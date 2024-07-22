from __future__ import annotations
from typing import Any
import dill as pickle
import traceback
import discord
from discord.ext import commands, tasks

from rpg_consts import *
from rpg_discord_menus import *
from structures.rpg_combat_entity import Player

Channel = discord.TextChannel | discord.StageChannel | discord.VoiceChannel | discord.Thread | \
    discord.DMChannel | discord.GroupChannel | discord.PartialMessageable

MY_ID = 92437761147023360

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
        self.currentParty : PartyInfo | None = None
        self.pendingItems : list[Equipment] = []

    """ Returns values to be pickled """
    def __getstate__(self):
        return (self.userId, self.savedMention, self.defaultFormationDistance)
    
    """ Restore state from unpickled values """
    def __setstate__(self, state):
        self.userId, self.savedMention, self.defaultFormationDistance = state
        GameSession.restoreUnpickledState(self)
        
    @staticmethod
    def restoreUnpickledState(session : GameSession):
        session.newCharacterName = ""
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
        session.currentParty = None
        session.pendingItems = []
        
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

    async def updateEmbed(self, channel : Channel | None = None):
        if self.isActive:
            if self.currentMessage is None:
                print("warning: message to update not found")
                return
            self.currentMessage = await self.currentMessage.edit(embed=self.currentEmbed, view=self.currentView)
        else:
            if channel is None:
                if self.currentMessage is None:
                    print("warning: message to update not found")
                    return
                channel = self.currentMessage.channel
            await self.recreateEmbed(channel)

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
        player = self.getPlayer()
        assert(player is not None)
        sessionPlayerMap : dict[GameSession, Player] = {self: player} if self.currentParty is None else self.currentParty.getSessionPlayerMap()

        inputHandlerMap : dict[Player, DungeonInputHandler] = {
            sessionPlayerMap[session]: DiscordDungeonInputHandler(sessionPlayerMap[session], session) for session in sessionPlayerMap}
        startingDistanceMap : dict[CombatEntity, int] = {
            sessionPlayerMap[session]: session.defaultFormationDistance for session in sessionPlayerMap}
        loggerMap : dict[Player, MessageCollector] = {
            sessionPlayerMap[session]: DiscordMessageCollector(session) for session in sessionPlayerMap}

        newDungeon = DungeonController(dungeonData, inputHandlerMap, startingDistanceMap, loggerMap)
        if self.currentParty is not None:
            for session in self.currentParty.allSessions:
                session.currentDungeon = newDungeon
        else:
            self.currentDungeon = newDungeon

        assert(self.currentDungeon is not None)
        asyncio.create_task(self.currentDungeon.runDungeon(False))
        [await session.waitForCombatStart() for session in sessionPlayerMap]

    async def waitForCombatStart(self):
        assert(self.currentDungeon is not None)

        self.unseenCombatLog = ""
        self.dungeonLoaded.clear()
        await self.currentDungeon.combatReadyFlag.wait()
        # TODO: also load other party sessions, including loading flags (is this needed?)
        await self.loadNewMenu(COMBAT_MENU)
        self.dungeonFailed = False
        self.dungeonLoaded.set()

    async def exitDungeon(self):
        player = self.getPlayer()
        assert(player is not None)
        if self.currentDungeon is None:
            return

        self.currentDungeon.removePlayer(player)
        if self.currentParty is not None:
            self.currentParty.leaveParty(self)

        self.currentDungeon = None
        await self.loadNewMenu(MAIN_MENU)
        self.dungeonFailed = False

    async def loadNewMenu(self, newMenu : InterfaceMenu, channel : Channel | None = None):
        self.currentMenu = newMenu
        await self.currentView.loadPages(newMenu.pages, None, channel)

    def safeToSwitch(self):
        return self.currentDungeon is None and self.currentParty is None
    
    def getPartySessions(self):
        if self.currentParty is None:
            return [self]
        else:
            return self.currentParty.allSessions

class InterfaceView(discord.ui.View):
    def __init__(self, session : GameSession, availablePages : list[InterfacePage],
                 currentPageStack : list[int], pageData : dict):
        super().__init__()
        self.session = session
        self.availablePages = availablePages
        self.currentPageStack = currentPageStack
        self.pageData : dict = pageData

        self.indexMap : dict[InterfacePage, int] = {}
        self.rowMap : dict[int, int] = {}
        self.currentConfirmation : InterfaceConfirmation | None = None

        self.refreshButtons()
        self.session.currentEmbed = self.availablePages[currentPageStack[0]].getContent(self.session, self)

    def refreshButtons(self):
        self.indexMap = {}
        self.clear_items()
        if self.currentConfirmation is None:
            self.rowMap = {}
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
            
            if button.row is not None:
                if self.rowMap.get(button.row, 0) >= 5:
                    button.row = None
                else:
                    self.rowMap[button.row] = self.rowMap.get(button.row, 0) + 1

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

    async def loadPages(self, newPages : list[InterfacePage], pageStack : list[int] | None = None, channel : Channel | None = None):
        self.availablePages = newPages

        self.currentPageStack = [0]
        if pageStack is not None:
            self.currentPageStack = pageStack
        self.pageData = {}
        self.refreshButtons()
        self.session.currentEmbed = self.availablePages[0].getContent(self.session, self)
        await self.session.updateEmbed(channel)

    async def requestConfirm(self, confirmDialogue : InterfaceConfirmation):
        self.currentConfirmation = confirmDialogue
        await self.refresh()

    async def respondConfirm(self, didConfirm : bool):
        assert(self.currentConfirmation is not None)
        if didConfirm:
            self.pageData[self.currentConfirmation.dataKey] = True
        self.currentConfirmation = None
        await self.refresh()

class CharacterDeletionPrompt(object):
    def __init__(self, channel : Channel, userId : int, character : Player):
        self.channel = channel
        self.userId = userId
        self.character = character

        self.session = GLOBAL_STATE.accountDataMap[userId].session
        self.state = 0
        self.embed = discord.Embed(title=f"DELETING CHARACTER: {character.name}")
        self.view = discord.ui.View()
        self.message : discord.Message | None = None

    async def _confirmCallback(self, interaction : discord.Interaction):
        await interaction.response.defer()
        if interaction.user.id != self.userId:
            return
        self.state += 1
        await self.updateMessage()

    async def _cancelCallback(self, interaction : discord.Interaction):
        await interaction.response.defer()
        if interaction.user.id != self.userId:
            return
        self.view.clear_items()
        self.view.stop()
        self.embed.clear_fields()
        self.embed.title="Deletion Cancelled!"
        if self.message is not None:
            await self.message.edit(embed=self.embed, view=self.view)

    async def updateMessage(self):
        self.embed.clear_fields()
        self.view.clear_items()

        if self.state == 0:
            charDescription = f"Level {self.character.level} {enumName(self.character.currentPlayerClass)}"
            self.embed.add_field(name=f"Are you sure you want to delete {self.character.name}?",
                                 value=f"They are currently a **{charDescription}**. There is no way to restore a deleted character, and all of their items will be lost as well.")

            confirmButton = discord.ui.Button(label="Delete Character", style=discord.ButtonStyle.red)
            confirmButton.callback = self._confirmCallback
            cancelButton = discord.ui.Button(label="Do Not Delete", style=discord.ButtonStyle.blurple)
            cancelButton.callback = self._cancelCallback
            self.view.add_item(confirmButton).add_item(cancelButton)

            self.message = await self.channel.send(self.session.savedMention, embed=self.embed, view=self.view)

        elif self.state == 1:
            self.embed.add_field(name=f"Are you REALLY sure you want to delete {self.character.name}??",
                                 value=f"Remember that you can create up to {MAX_USER_CHARACTERS} characters currently, and that each character can change class at any time outside of a dungeon.")

            confirmButton = discord.ui.Button(label="Yes, Delete Character", style=discord.ButtonStyle.red)
            confirmButton.callback = self._confirmCallback
            cancelButton = discord.ui.Button(label="No, whoops", style=discord.ButtonStyle.blurple)
            cancelButton.callback = self._cancelCallback
            self.view.add_item(confirmButton).add_item(cancelButton)

            assert self.message is not None
            await self.message.edit(embed=self.embed, view=self.view)

        elif self.state == 2:
            self.embed.add_field(name=f"Are you *REALLY REALLY REALLY* sure you want to delete {self.character.name}?????",
                                 value=f"**This is your last warning.**")

            confirmButton = discord.ui.Button(label="YES!!!!!", style=discord.ButtonStyle.red)
            confirmButton.callback = self._confirmCallback
            cancelButtonTextOptions = ["no", "not anymore", "my b", "whoops", "cancel", "oh no", "not really", "uhhh", "hmm"]
            cancelButtons = [discord.ui.Button(label=random.choice(cancelButtonTextOptions),
                                               style=discord.ButtonStyle.blurple) for i in range(14)]
            for cancelButton in cancelButtons:
                cancelButton.callback = self._cancelCallback

            allButtons = cancelButtons + [confirmButton]
            random.shuffle(allButtons)
            for button in allButtons:
                self.view.add_item(button)

            assert self.message is not None
            await self.message.edit(embed=self.embed, view=self.view)
        
        else:
            GLOBAL_STATE.deleteCharacter(self.userId, self.character)

            self.embed.add_field(name="It is done.", value="")
            self.view.stop()
            assert self.message is not None
            await self.message.edit(embed=self.embed, view=self.view)




intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='ch.', intents=intents) # TODO: change if beta

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}.')
    GLOBAL_STATE.loadState()
    await bot.change_presence(status=discord.Status.online,
                              activity=discord.Game("Chatanquest using /play (or ch.play)"))
    saveLoop.start()

@tasks.loop(seconds = BACKUP_INTERVAL_SECONDS)
async def saveLoop():
    if GLOBAL_STATE.loaded:
        if GLOBAL_STATE.firstSave:
            _doSave()
        else:
            GLOBAL_STATE.firstSave = True

def _doSave():
    try:
        GLOBAL_STATE.saveState()
    except TypeError:
        print(traceback.format_exc())
        print("failed to save")
    except pickle.PicklingError:
        print(traceback.format_exc())
        print("failed to save")

async def respondNotLoaded(ctx : commands.Context):
    await ctx.send(f"Sorry, still setting up; please wait a moment and try again.")

@bot.hybrid_command(brief="Create a new character",
                    description=f"Creates a new character. Currently, you can create up to {MAX_USER_CHARACTERS} characters.")
async def new_character(ctx : commands.Context, character_name : str):
    if GLOBAL_STATE.loaded:
        userId = ctx.author.id
        validated = True
        if GLOBAL_STATE.idRegistered(userId):
            charList = GLOBAL_STATE.accountDataMap[userId].allCharacters
            if len(charList) > MAX_USER_CHARACTERS:
                await ctx.send(f"You cannot make more than {MAX_USER_CHARACTERS} characters at the moment. " + \
                            "Use the 'play' or 'select_character' commands instead.", ephemeral=True)
                validated = False
            elif character_name.lower() in [char.name.lower() for char in charList]:
                await ctx.send(f"You already have a character with this name.", ephemeral=True)
                validated = False
        if validated and len(character_name) > MAX_NAME_LENGTH:
            await ctx.send(f"Please use a name that's less that {MAX_NAME_LENGTH} characters.", ephemeral=True)
            validated = False

        if validated:
            if GLOBAL_STATE.idRegistered(userId):
                gameSession = GLOBAL_STATE.accountDataMap[userId].session
                gameSession.newCharacterName = character_name
                await ctx.send(f"Creating new character for {ctx.author.display_name}...")
                await gameSession.recreateEmbed(ctx.channel)
                await gameSession.loadNewMenu(NEW_GAME_MENU, ctx.channel)
            else:
                gameSession = GameSession(userId, character_name)
                await ctx.send(f"Opening session for {ctx.author.display_name}...")
                gameSession.savedMention = ctx.author.mention
                await gameSession.recreateEmbed(ctx.channel)
    else:
        await respondNotLoaded(ctx)
@new_character.error
async def new_character_error(ctx, error : Exception):
    await ctx.send("Add a character name using 'new_character [name]'!", ephemeral=True)

@bot.hybrid_command(brief="Change active character",
                    description=f"Selects your active character, either by index or name. Unavailable while in a party or dungeon.")
async def select_character(ctx : commands.Context, target_character : str):
    if GLOBAL_STATE.loaded:
        userId = ctx.author.id
        accountData = GLOBAL_STATE.accountDataMap.get(userId, None)
        if accountData is None:
            await ctx.send("You don't have a character yet! Use the 'new_character [name]' command first.", ephemeral=True)
        elif not accountData.session.safeToSwitch():
            await ctx.send("You can't switch characters while in a party or dungeon! Leave first, then try again.", ephemeral=True)
        else:
            charList = accountData.allCharacters
            chosenCharacter = None
            if target_character.isdigit():
                chosenCharacter = charList[int(target_character) - 1]
            else:
                for character in charList:
                    if character.name.lower() == target_character.lower():
                        chosenCharacter = character

            if chosenCharacter is None:
                raise KeyError
            elif chosenCharacter != accountData.currentCharacter:
                accountData.currentCharacter = chosenCharacter
                await ctx.send(f"Selected {chosenCharacter.name} as your current character.")
            else:
                await ctx.send(f"{chosenCharacter.name} is already your current character!", ephemeral=True)
    else:
        await respondNotLoaded(ctx)
@select_character.error
async def select_character_error(ctx, error : Exception):
    userId = ctx.author.id
    if not GLOBAL_STATE.idRegistered(userId):
        await ctx.send("You don't have a character yet! Use the 'new_character [name]' command first.", ephemeral=True)
    else:
        charList = GLOBAL_STATE.accountDataMap[userId].allCharacters
        response = "You can use 'select_character [character_name]' or 'select_character [index]'.\n"
        response += "__Your characters:__\n"
        response += '\n'.join(f"[{i+1}] {char.name}, Level {char.level}" for i, char in enumerate(charList))
        await ctx.send(response, ephemeral=True)

@bot.hybrid_command(brief="Opens the game",
                    description=f"Opens a new session with for the game, assuming you've already made a character.")
async def play(ctx : commands.Context):
    if GLOBAL_STATE.loaded:
        userId = ctx.author.id
        if GLOBAL_STATE.idRegistered(userId):
            gameSession = GLOBAL_STATE.accountDataMap[userId].session
            await ctx.send(f"Opening session for {ctx.author.display_name}...")
            gameSession.savedMention = ctx.author.mention
            await gameSession.recreateEmbed(ctx.channel)
        else:
            await ctx.send("You don't have a character yet! Use the 'new_character [name]' command first.", ephemeral=True)
    else:
        await respondNotLoaded(ctx)

@bot.hybrid_command(brief="Closes the game",
                    description=f"Disables any open sessions you have.")
async def close(ctx : commands.Context):
    if GLOBAL_STATE.loaded:
        userId = ctx.author.id
        if GLOBAL_STATE.idRegistered(userId):
            gameSession = GLOBAL_STATE.accountDataMap[userId].session
            if gameSession.isActive:
                await ctx.send(f"Closing session for {ctx.author.display_name}...")
                gameSession.currentView.stop()
                await gameSession.messageTimeout(gameSession.currentView)
            else:
                await ctx.send(f"No active session found for {ctx.author.display_name}.")
        else:
            await ctx.send("You don't have a character yet! Use the 'new_character [name]' command first.", ephemeral=True)
    else:
        await respondNotLoaded(ctx)

@bot.hybrid_command(brief="Invite user to party",
                    description=f"When you've created a party, you can invite people with this instead of the drop-down menu.")
async def invite(ctx : commands.Context, member: discord.Member):
    if GLOBAL_STATE.loaded:
        userId = ctx.author.id
        if not GLOBAL_STATE.idRegistered(userId):
            await ctx.send("You don't have a character yet! Use the 'new_character [name]' command first.", ephemeral=True)
        else:
            gameSession = GLOBAL_STATE.accountDataMap[userId].session
            if gameSession.currentParty is None:
                await ctx.send("You don't have a party! Use 'play' to select a dungeon and create one first.", ephemeral=True)
            elif gameSession.currentParty.creatorSession != gameSession:
                await ctx.send("Only the party creator can invite people.")
            elif gameSession.currentDungeon is not None:
                await ctx.send("You can't invite people while in the middle of a dungeon!", ephemeral=True)
            elif len(gameSession.currentParty.allSessions) >= gameSession.currentParty.dungeonData.maxPartySize:
                await ctx.send("The party is already full.", ephemeral=True)

            else:
                invitedData = GLOBAL_STATE.accountDataMap.get(member.id, None)
                if invitedData is None or not GLOBAL_STATE.idRegistered(member.id):
                    await ctx.send("The user you invited hasn't made any characters!", ephemeral=True)
                elif not invitedData.session.safeToSwitch():
                    await ctx.send("The user you invited is already in a party or dungeon.", ephemeral=True)
                elif invitedData.session in gameSession.currentParty.allSessions:
                    await ctx.send("The user you invited is already in the party!", ephemeral=True)
                else:
                    invitedPlayer = invitedData.session.getPlayer()
                    if invitedPlayer is None or not gameSession.currentParty.dungeonData.meetsRequirements(invitedPlayer):
                        await ctx.send("The character you invited does not meet the requirements for this dungeon.", ephemeral=True)
                    else:
                        await ctx.send("Sent an invite!", ephemeral=True)
                        await sendPartyInvite(gameSession, invitedData.session)
    else:
        await respondNotLoaded(ctx)
@invite.error
async def invite_error(ctx, error : Exception):
    await ctx.send("Include someone to invite to a party using 'invite [user]'!", ephemeral=True)

@bot.hybrid_command(brief="Adjust options",
                    description=f"Provides some options that apply to all characters on your account.")
async def options(ctx : commands.Context):
    if GLOBAL_STATE.loaded:
        userId = ctx.author.id
        if GLOBAL_STATE.idRegistered(userId):
            await ctx.send(f"Opening options for {ctx.author.display_name}...")
            optionSession = GameSession(userId)
            optionSession.savedMention = ctx.author.mention
            await optionSession.loadNewMenu(OPTIONS_MENU, ctx.channel)
        else:
            await ctx.send("You don't have a character yet! Use the 'new_character [name]' command first.", ephemeral=True)
    else:
        await respondNotLoaded(ctx)

@bot.hybrid_command(brief="[OWNER] Sync bot state",
                    description=f"[Bot Owner Only] Hopefully updates slash commands.")
async def sync(ctx : commands.Context):
    if ctx.author.id == MY_ID:
        # if ctx.guild is not None:
            await bot.wait_until_ready()
            # bot.tree.clear_commands(guild=ctx.guild)
            # await bot.tree.sync(guild=ctx.guild)
            # bot.tree.copy_global_to(guild=ctx.guild)
            # await bot.tree.sync(guild=ctx.guild)
            await bot.tree.sync()
            await ctx.send("Commands synced!")

@bot.hybrid_command(brief="Emergency session reset",
                    description=f"Attempts to reset your session to the main menu. Useful if something breaks in a dungeon.")
async def panic(ctx : commands.Context, confirmation : str | None = None):
    if GLOBAL_STATE.loaded:
        if confirmation is not None and confirmation.lower() == "saveme":
            userId = ctx.author.id
            if GLOBAL_STATE.idRegistered(userId):
                gameSession = GLOBAL_STATE.accountDataMap[userId].session
                await gameSession.exitDungeon()
                await ctx.send(f"Resetting your session (hopefully this worked...)")
            else:
                await ctx.send("You don't have a character yet (which means you're probably not stuck)! Use the 'new_character [name]' command first.")
        else:
            await ctx.send("This command will attempt to reset you to the main menu if you get stuck in a dungeon, kicking you out. " +
                           "Note that using the 'play' command to start a new session can solve some smaller issues.\n" +
                            "To confirm this reset, use '/panic saveme'.")
    else:
        await respondNotLoaded(ctx)

@bot.hybrid_command(brief="Delete character",
                    description=f"Deletes one of your characters forever (for real).")
async def delete_character(ctx : commands.Context, target_character : str):
    if GLOBAL_STATE.loaded:
        userId = ctx.author.id
        accountData = GLOBAL_STATE.accountDataMap.get(userId, None)
        if accountData is None:
            await ctx.send("You don't have a character yet (why are you trying to delete one?)! Use the 'new_character [name]' command first.", ephemeral=True)
        elif not accountData.session.safeToSwitch():
            await ctx.send("You can't delete characters while in a party or dungeon! Leave first, then try again. (You can use the 'panic' command if you're stuck.)", ephemeral=True)
        else:
            charList = accountData.allCharacters
            chosenCharacter = None
            if target_character.isdigit():
                chosenCharacter = charList[int(target_character) - 1]
            else:
                for character in charList:
                    if character.name.lower() == target_character.lower():
                        chosenCharacter = character

            if chosenCharacter is None:
                raise KeyError
            else:
                await ctx.send(f"Opening deletion prompt for {chosenCharacter.name}...")
                await CharacterDeletionPrompt(ctx.channel, userId, chosenCharacter).updateMessage()
    else:
        await respondNotLoaded(ctx)
@delete_character.error
async def delete_character_error(ctx, error : Exception):
    userId = ctx.author.id
    if not GLOBAL_STATE.idRegistered(userId):
        await ctx.send("You don't have a character yet (why are you trying to delete one?)! Use the 'new_character [name]' command first.", ephemeral=True)
    else:
        charList = GLOBAL_STATE.accountDataMap[userId].allCharacters
        response = "You can use 'delete_character [character_name]' or 'delete_character [index]'.\n"
        response += "__Your characters:__\n"
        response += '\n'.join(f"[{i+1}] {char.name}, Level {char.level}" for i, char in enumerate(charList))
        await ctx.send(response, ephemeral=True)

@bot.command(brief="[OWNER] Save bot state",
                    description=f"[BOT OWNER ONLY] Force-saves the bot state. This should automatically happen periodically without calling this command.")
async def save(ctx : commands.Context):
    if ctx.author.id == MY_ID:
        _doSave()
        await ctx.send("saved state")
    else:
        await ctx.send("This is a dev-only command; progress should be periodically saved automatically.")


secret_file = open("secret.txt", "r")
secret = secret_file.read()
secret_file.close()
bot.run(secret)