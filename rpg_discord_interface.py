from __future__ import annotations
import discord
from discord.ext import commands

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
        self.currentMenu : InterfaceMenu = NEW_GAME_MENU
        self.currentView : InterfaceView = InterfaceView(self, self.currentMenu.pages, [])

    async def messageTimeout(self, view):
        if view == self.currentView:
            print(f"{bot.get_user(self.userId)} message timeout")
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

        oldView = self.currentView
        self.currentView = InterfaceView(self, self.currentMenu.pages, oldView.currentPageStack)
        self.currentMessage = await channel.send(embed=self.currentEmbed, view=self.currentView)

        if clearOld is not None:
            await clearOld

    async def loadNewMenu(self, newMenu : InterfaceMenu):
        self.currentMenu = newMenu
        await self.currentView.loadPages(newMenu.pages)

class InterfaceView(discord.ui.View):
    def __init__(self, session : GameSession, availablePages : list[InterfacePage], currentPageStack : list[int]):
        super().__init__()
        self.session = session
        self.availablePages = availablePages
        self.currentPageStack = currentPageStack

        self.pageData : dict = {}
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
    await bot.tree.sync()
    print(f'Logged in as {bot.user}.')

@bot.hybrid_command()
async def new_character(ctx : commands.Context, character_name : str):
    userId = ctx.author.id
    if userId in GLOBAL_STATE.accountDataMap:
        await ctx.send("You already have a character [support for more characters coming soon]! Use the 'play' command instead.")
    else:
        gameSession = GameSession(userId, character_name)
        await ctx.send(f"Opening session for {ctx.author.display_name}...")
        await gameSession.recreateEmbed(ctx.channel)
@new_character.error
async def new_character_error(ctx, error):
    await ctx.send("Add a character name using 'new_character [name]'!")

@bot.hybrid_command()
async def play(ctx : commands.Context):
    userId = ctx.author.id
    if userId in GLOBAL_STATE.accountDataMap:
        gameSession = GLOBAL_STATE.accountDataMap[userId].session
        await ctx.send(f"Opening session for {ctx.author.display_name}...")
        await gameSession.recreateEmbed(ctx.channel)
    else:
        await ctx.send("You don't have a character yet! Use the 'new_character [character]' command first.")

@bot.hybrid_command()
async def sync(ctx : commands.Context):
    await ctx.bot.tree.sync(guild=ctx.guild)
    await ctx.send("Commands synced!")


secret_file = open("secret.txt", "r")
secret = secret_file.read()
secret_file.close()
bot.run(secret)