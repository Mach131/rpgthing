from __future__ import annotations
import dill as pickle
import traceback
import discord
from discord.ext import commands, tasks

from rpg_consts import *
from rpg_discord_menus import *
from structures.rpg_combat_entity import Player

Channel = discord.TextChannel | discord.StageChannel | discord.VoiceChannel | discord.Thread | \
    discord.DMChannel | discord.GroupChannel | discord.PartialMessageable


class GameSession(object):
    def __init__(self, userId : int, newCharacterName : str | None = None):
        self.userId : int = userId
        self.newCharacterName = newCharacterName

        self.isActive : bool = False
        self.currentEmbed : discord.Embed = discord.Embed()
        self.currentMessage : discord.Message | None = None
        self.savedMention : str = ""
        self.currentMenu : InterfaceMenu = NEW_GAME_MENU
        self.currentView : InterfaceView = InterfaceView(self, self.currentMenu.pages, [], {})

        self.currentDungeon : DungeonController | None = None
        self.dungeonLoaded : asyncio.Event = asyncio.Event()
        self.unseenCombatLog : str = ""
        self.defaultFormationDistance : int = DEFAULT_STARTING_DISTANCE
        self.dungeonFailed : bool = False

    """ Returns values to be pickled """
    def __getstate__(self):
        return (self.userId, self.newCharacterName, self.savedMention, self.defaultFormationDistance)
    
    """ Restore state from unpickled values """
    def __setstate__(self, state):
        self.userId, self.newCharacterName, self.savedMention, self.defaultFormationDistance = state
        GameSession.restoreUnpickledState(self)
        
    @staticmethod
    def restoreUnpickledState(session : GameSession):
        session.isActive = False
        session.currentEmbed = discord.Embed()
        session.currentMessage = None
        session.currentView = InterfaceView(session, NEW_GAME_MENU.pages, [], {})
        session.currentMenu = MAIN_MENU
        session.currentView.availablePages = session.currentMenu.pages
        session.currentDungeon = None
        session.dungeonLoaded = asyncio.Event()
        session.unseenCombatLog = ""
        session.dungeonFailed = False
        
    def onLoadReset(self):
        # Originally had support for re-loading dungeons here, but too hard to figure out pickling at the moment
        
        # if self.currentDungeon is not None:
        #     # TODO: only the first person in a party this is called for needs to do this
        #     asyncio.create_task(self.currentDungeon.runDungeon(True))
        #     if not self.currentDungeon.loadCheckWaiting():
        #         asyncio.create_task(self.waitForCombatStart())
        pass

    async def messageTimeout(self, view):
        if view == self.currentView:
            print(f"{self.userId} message timeout")
            self.isActive = False
            if self.currentMessage is not None:
                await self.currentMessage.edit(view=None)

    async def updateEmbed(self):
        assert(self.currentMessage is not None)
        if self.isActive:
            self.currentMessage = await self.currentMessage.edit(embed=self.currentEmbed, view=self.currentView)
        else:
            await self.recreateEmbed(self.currentMessage.channel)

    async def recreateEmbed(self, channel : Channel):
        self.isActive = True
        self.currentView.stop()
        clearOld = None
        if self.currentMessage is not None:
            clearOld = self.currentMessage.edit(view=None)

        mentionString = self.savedMention
        oldView = self.currentView
        self.currentView = InterfaceView(self, self.currentMenu.pages, oldView.currentPageStack, oldView.pageData)
        self.currentMessage = await channel.send(mentionString, embed=self.currentEmbed, view=self.currentView)
        
        if clearOld is not None:
            await clearOld

    def getPlayer(self) -> Player | None:
        accountData = GLOBAL_STATE.accountDataMap.get(self.userId, None)
        if accountData is not None:
            return accountData.currentCharacter

    async def enterDungeon(self, dungeonData : DungeonData):
        # TODO: the party leader calling this should set the same dungeonController for teammates, including making handlers & stuff
        # TODO: formations -> starting distances
        player = self.getPlayer()
        assert(player is not None)

        self.currentDungeon = DungeonController(dungeonData, {player: DiscordDungeonInputHandler(player, self)},
                                                {player: self.defaultFormationDistance},
                                                {player: DiscordMessageCollector(self)})
        
        asyncio.create_task(self.currentDungeon.runDungeon(False))
        await self.waitForCombatStart()

    async def waitForCombatStart(self):
        assert(self.currentDungeon is not None)

        self.unseenCombatLog = ""
        self.dungeonLoaded.clear()
        await self.currentDungeon.combatReadyFlag.wait()
        # TODO: also load other party sessions, including loading flags
        await self.loadNewMenu(COMBAT_MENU)
        self.dungeonFailed = False
        self.dungeonLoaded.set()

    async def exitDungeon(self):
        player = self.getPlayer()
        assert(player is not None)
        if self.currentDungeon is None:
            return

        self.currentDungeon.removePlayer(player)

        self.currentDungeon = None
        await self.loadNewMenu(MAIN_MENU)
        self.dungeonFailed = False

    async def loadNewMenu(self, newMenu : InterfaceMenu):
        self.currentMenu = newMenu
        await self.currentView.loadPages(newMenu.pages)

class InterfaceView(discord.ui.View):
    def __init__(self, session : GameSession, availablePages : list[InterfacePage],
                 currentPageStack : list[int], pageData : dict):
        super().__init__()
        self.session = session
        self.availablePages = availablePages
        self.currentPageStack = currentPageStack
        self.pageData : dict = pageData

        self.indexMap : dict[InterfacePage, int] = {}
        self.currentConfirmation : InterfaceConfirmation | None = None

        self.refreshButtons()
        self.session.currentEmbed = self.availablePages[currentPageStack[0]].getContent(self.session, self)

    def refreshButtons(self):
        self.indexMap = {}
        self.clear_items()
        if self.currentConfirmation is None:
            self._addButtons(self.availablePages, 0)
        else:
            for button in self.currentConfirmation.getButtons(self.session, self):
                self.add_item(button)

    def _addButtons(self, pageList : list[InterfacePage], depth : int):
        self._extendCurrentPageStack(depth)

        for idx, page in enumerate(pageList):
            self.indexMap[page] = idx
            button = page.getButton(self.session, self)
            button.callback = page.getCallback(self.session)
            if idx == self.currentPageStack[depth]:
                button.disabled = True
            self.add_item(button)

        subPages = pageList[self.currentPageStack[depth]].subPages
        if len(subPages) > 0:
            self._addButtons(subPages, depth+1)

    def _extendCurrentPageStack(self, depth):
        while len(self.currentPageStack) < depth + 1:
            self.currentPageStack.append(0)

    async def on_timeout(self):
        self.clear_items()
        await self.session.messageTimeout(self)

    async def setPage(self, page : InterfacePage):
        depth = page.buttonDepth
        self.currentPageStack = self.currentPageStack[:depth+1]
        self._extendCurrentPageStack(depth)

        self.currentPageStack[depth] = self.indexMap[page]
        self.pageData = {}

        self.refreshButtons()
        self.session.currentEmbed = page.getContent(self.session, self)
        await self.session.updateEmbed()

    async def refresh(self):
        self.refreshButtons()
        if self.currentConfirmation is None:
            self.session.currentEmbed = self.availablePages[self.currentPageStack[0]].getContent(self.session, self)
        else:
            self.session.currentEmbed = self.currentConfirmation.getEmbed()
        await self.session.updateEmbed()

    async def updateData(self, key, value):
        self.pageData[key] = value
        await self.refresh()

    async def loadPages(self, newPages : list[InterfacePage], pageStack : list[int] | None = None):
        self.availablePages = newPages

        self.currentPageStack = [0]
        if pageStack is not None:
            self.currentPageStack = pageStack
        self.pageData = {}
        self.refreshButtons()
        self.session.currentEmbed = self.availablePages[0].getContent(self.session, self)
        await self.session.updateEmbed()

    async def requestConfirm(self, confirmDialogue : InterfaceConfirmation):
        self.currentConfirmation = confirmDialogue
        await self.refresh()

    async def respondConfirm(self, didConfirm : bool):
        assert(self.currentConfirmation is not None)
        if didConfirm:
            self.pageData[self.currentConfirmation.dataKey] = True
        self.currentConfirmation = None
        await self.refresh()


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='ch.', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}.')
    GLOBAL_STATE.loadState()
    saveLoop.start()

@tasks.loop(seconds = BACKUP_INTERVAL_SECONDS)
async def saveLoop():
    if GLOBAL_STATE.loaded:
        if GLOBAL_STATE.firstSave:
            try:
                GLOBAL_STATE.saveState()
            except TypeError:
                print(traceback.format_exc())
                print("failed to save")
            except pickle.PicklingError:
                print(traceback.format_exc())
                print("failed to save")
        else:
            GLOBAL_STATE.firstSave = True

async def respondNotLoaded(ctx : commands.Context):
    await ctx.send(f"Sorry, still setting up; please wait a moment and try again.")

@bot.hybrid_command()
async def new_character(ctx : commands.Context, character_name : str):
    if GLOBAL_STATE.loaded:
        userId = ctx.author.id
        if userId in GLOBAL_STATE.accountDataMap:
            await ctx.send("You already have a character [support for more characters coming soon]! Use the 'play' command instead.")
        else:
            gameSession = GameSession(userId, character_name)
            await ctx.send(f"Opening session for {ctx.author.display_name}...")
            gameSession.savedMention = ctx.author.mention
            await gameSession.recreateEmbed(ctx.channel)
    else:
        await respondNotLoaded(ctx)
@new_character.error
async def new_character_error(ctx, error : Exception):
    await ctx.send("Add a character name using 'new_character [name]'!")

@bot.hybrid_command()
async def play(ctx : commands.Context):
    if GLOBAL_STATE.loaded:
        userId = ctx.author.id
        if userId in GLOBAL_STATE.accountDataMap:
            gameSession = GLOBAL_STATE.accountDataMap[userId].session
            await ctx.send(f"Opening session for {ctx.author.display_name}...")
            gameSession.savedMention = ctx.author.mention
            await gameSession.recreateEmbed(ctx.channel)
        else:
            await ctx.send("You don't have a character yet! Use the 'new_character [character]' command first.")
    else:
        await respondNotLoaded(ctx)

@bot.hybrid_command()
async def sync(ctx : commands.Context):
    await ctx.bot.tree.sync(guild=ctx.guild)
    await ctx.send("Commands synced!")


secret_file = open("secret.txt", "r")
secret = secret_file.read()
secret_file.close()
bot.run(secret)