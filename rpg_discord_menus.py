from __future__ import annotations
from typing import Callable, Coroutine
from typing import Callable, TYPE_CHECKING
import discord
import asyncio

from rpg_consts import *
from rpg_global_state import GLOBAL_STATE
from structures.rpg_combat_entity import Player
from structures.rpg_items import Equipment, Weapon

if TYPE_CHECKING:
    from rpg_discord_interface import GameSession, InterfaceView

class InterfacePage(object):
    def __init__(self, buttonName : str, buttonStyle : discord.ButtonStyle, subPages : list[InterfacePage],
                 contentFn : Callable[[GameSession, InterfaceView], discord.Embed] | None, enabledFn : Callable[[GameSession], bool],
                 callbackFn : Callable[[GameSession, InterfacePage, discord.Interaction], Coroutine],
                 buttonStyleFn : Callable[[GameSession, InterfaceView], discord.ButtonStyle] | None = None):
        self.buttonName = buttonName
        self.buttonStyle = buttonStyle
        self.contentFn = contentFn
        self.subPages = subPages
        self.enabledFn = enabledFn
        self.callbackFn = callbackFn
        self.buttonStyleFn = buttonStyleFn

        self.buttonDepth = 0
        if len(self.subPages) == 0:
            assert(self.contentFn is not None)
        self._adjustDepth()

    def _adjustDepth(self, parent : InterfacePage | None = None):
        if parent is not None:
            self.buttonDepth = parent.buttonDepth + 1
        [subPage._adjustDepth(self) for subPage in self.subPages]

    def getButton(self, session : GameSession, view : InterfaceView):
        buttonStyle = self.buttonStyle
        if self.buttonStyleFn is not None:
            buttonStyle = self.buttonStyleFn(session, view)
        return discord.ui.Button(style=buttonStyle, label=self.buttonName, custom_id=self.buttonName,
                                 row=4-self.buttonDepth)
    
    def isButtonEnabled(self, session : GameSession):
        return self.enabledFn(session)
    
    def getContent(self, session : GameSession, view : InterfaceView):
        if len(self.subPages) == 0:
            assert self.contentFn is not None
            return self.contentFn(session, view)
        else:
            childIndex = session.currentView.currentPageStack[self.buttonDepth + 1]
            return self.subPages[childIndex].getContent(session, view)
    
    def getCallback(self, session : GameSession):
        return (lambda interaction: self.callbackFn(session, self, interaction)
                    if interaction.user.id == session.userId else asyncio.sleep(0))
    
class InterfaceConfirmation(object):
    def __init__(self, prompt : str, confirmText : str, cancelText : str, dataKey : str):
        self.prompt = prompt
        self.confirmText = confirmText
        self.cancelText = cancelText
        self.dataKey = dataKey

    def getEmbed(self):
        return discord.Embed(title="CONFIRMATION", description="").add_field(name="", value=self.prompt)

    def getButtons(self, session : GameSession, view : InterfaceView):
        confirmButton = discord.ui.Button(label=self.confirmText, style=discord.ButtonStyle.red)
        confirmButton.callback = lambda interaction: self._callbackFn(interaction, session, view, True)
        cancelButton = discord.ui.Button(label=self.cancelText, style=discord.ButtonStyle.secondary)
        cancelButton.callback = lambda interaction: self._callbackFn(interaction, session, view, False)
        return [confirmButton, cancelButton]

    async def _callbackFn(self, interaction : discord.Interaction, session : GameSession, view : InterfaceView, didConfirm : bool):
        await interaction.response.defer()
        if interaction.user.id != session.userId:
            return
        await view.respondConfirm(didConfirm)

async def changePageCallback(session : GameSession, page : InterfacePage, interaction : discord.Interaction):
    await interaction.response.defer()
    await session.currentView.setPage(page)

async def scrollCallbackFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView, amount : int, bounds : int):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return asyncio.sleep(0)
    oldIdx = view.pageData.get('scrollIdx', 0)
    await view.updateData('scrollIdx', (oldIdx + amount) % (bounds + 1))

async def updateDataCallbackFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView, key : str, val):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return asyncio.sleep(0)
    await view.updateData(key, val)

class InterfaceMenu(object):
    def __init__(self, pages : list[InterfacePage]):
        self.pages = pages

#### New Character

def newCharacterContent(session : GameSession, view : InterfaceView):
    classSelector = discord.ui.Select(placeholder="Class", options=[
        discord.SelectOption(label="Warrior", value="WARRIOR", description="Strike opponents face-on!"),
        discord.SelectOption(label="Ranger", value="RANGER", description="Attack safely from afar!"),
        discord.SelectOption(label="Rogue", value="ROGUE", description="Dance around enemy attacks!"),
        discord.SelectOption(label="Mage", value="MAGE", description="Provide arcane support!")
    ])
    classSelector.callback = lambda interaction: interaction.response.defer() if interaction.user.id == session.userId else asyncio.sleep(0)
    view.add_item(classSelector)

    submitButton = discord.ui.Button(label="Confirm", style=discord.ButtonStyle.green, custom_id="confirm")
    submitButton.callback = lambda interaction: submitNewCharacter(interaction, session, classSelector)
    view.add_item(submitButton)

    description = f"Creating a new character: {session.newCharacterName}\n"
    description += "Choose a class below to start!"
    return discord.Embed(title="Welcome to Chatanquest!", description=description)
async def submitNewCharacter(interaction : discord.Interaction, session : GameSession, classSelector : discord.ui.Select):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return asyncio.sleep(0)
    try:
        chosenClass = BasePlayerClassNames[classSelector.values[0]]
        assert(session.newCharacterName is not None)
        GLOBAL_STATE.registerNewCharacter(interaction.user.id, session.newCharacterName, chosenClass, session)
        await session.loadNewMenu(MAIN_MENU)
    except IndexError:
        if session.currentMessage:
            await session.currentMessage.edit(content="(Remember to select a class!)")
NEW_CHARACTER_PAGE = InterfacePage("hello", discord.ButtonStyle.secondary, [],
                                   newCharacterContent,
                                   lambda session: False,
                                   lambda session, page, interaction: asyncio.sleep(0))
NEW_GAME_MENU = InterfaceMenu([NEW_CHARACTER_PAGE])


#### Character Pages

def characterDetailContent(session : GameSession, view : InterfaceView):
    player = GLOBAL_STATE.accountDataMap[session.userId].currentCharacter
    currentClass = player.currentPlayerClass
    embed = discord.Embed(title="Character Info", description=f"{player.name}: Level {player.level}  \\||  " +
                          f"{currentClass.name[0] + currentClass.name[1:].lower()} Rank {player.classRanks[currentClass]}")
    
    statStrings = {}
    for stat in BaseStats:
        statStrings[stat] = f"{stat.name}: {player.getStatValue(stat)} ({player.statLevels[stat]} pts)"
    statString = f"{statStrings[BaseStats.HP]}  \\||  {statStrings[BaseStats.MP]}\n" + \
                 f"{statStrings[BaseStats.ATK]}  \\||  {statStrings[BaseStats.DEF]}  \\||  {statStrings[BaseStats.MAG]}  \\||  {statStrings[BaseStats.RES]}\n" + \
                 f"{statStrings[BaseStats.ACC]}  \\||  {statStrings[BaseStats.AVO]}  \\||  {statStrings[BaseStats.SPD]}"
    embed.add_field(name="Stats:", value=statString, inline=False)
    
    levelExpString = f"{player.playerExp}/{player.getExpToNextLevel()}" if player.getExpToNextLevel() else "(MAX)"
    rankExpString = f"{player.classExp[currentClass]}/{player.getExpToNextRank()}" if player.getExpToNextRank() else "(MAX)"
    embed.add_field(name="EXP:", value=f"To next Level: {levelExpString}\nTo next Rank: {rankExpString}")
    
    equipString = "\n".join(["- " + equip.getShortDescription() for equip in player.equipment.values()])
    embed.add_field(name="Equipped:", value=equipString)

    embed.add_field(name="Material:",
                    value=f"WUP: {player.wup}\nSWUP: {player.swup}")
    return embed
CHARACTER_DETAIL_SUBPAGE = InterfacePage("Summary", discord.ButtonStyle.secondary, [],
                                      characterDetailContent,
                                      lambda session: True,
                                      changePageCallback)


def characterStatsContent(session : GameSession, view : InterfaceView):
    player = GLOBAL_STATE.accountDataMap[session.userId].currentCharacter
    canAdd = player.freeStatPoints > 0
    embed = discord.Embed(title="Stats", description=f"Available Stat points: {player.freeStatPoints}")

    for stat in BaseStats:
        embed.add_field(name=stat.name,
                        value=f"{player.getBaseStatValue(stat)} Base, {player.getStatValue(stat)} Total ({player.statLevels[stat]} pts)")

        statButton = discord.ui.Button(label=f"+{stat.name}", style=discord.ButtonStyle.primary, custom_id=f"{stat.name}",
                                    disabled=not canAdd or player.statLevels[stat] >= player.level)
        statButton.callback = (lambda _stat: lambda interaction: statIncreaseButton(interaction, session, player, _stat, False))(stat)
        view.add_item(statButton)
    resetButton = discord.ui.Button(label=f"Reset Stats", style=discord.ButtonStyle.danger, custom_id=f"reset", disabled=False)
    resetButton.callback = lambda interaction: statIncreaseButton(interaction, session, player, BaseStats.HP, True)
    view.add_item(resetButton)

    return embed
async def statIncreaseButton(interaction : discord.Interaction, session : GameSession, player : Player, stat : BaseStats, reset : bool):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return asyncio.sleep(0)
    if reset:
        player.resetStatPoints()
    else:
        player.assignStatPoints([stat])
    await session.currentView.refresh()
def statPointStyle(session : GameSession, view : InterfaceView):
    player = GLOBAL_STATE.accountDataMap[session.userId].currentCharacter
    if player.freeStatPoints > 0:
        return discord.ButtonStyle.green
    else:
        return discord.ButtonStyle.secondary
CHARACTER_STATS_SUBPAGE = InterfacePage("Stats", discord.ButtonStyle.secondary, [],
                                        characterStatsContent, lambda session: True, changePageCallback, statPointStyle)


def characterClassesContent(session : GameSession, view : InterfaceView):
    player = GLOBAL_STATE.accountDataMap[session.userId].currentCharacter
    currentClass = player.currentPlayerClass
    rankExpString = f"EXP to next rank: {player.classExp[currentClass]}/{player.getExpToNextRank()}" if player.getExpToNextRank() else "MAX"
    embed = discord.Embed(title="Classes",
                          description=f"Current Class: {currentClass.name[0] + currentClass.name[1:].lower()} Rank {player.classRanks[currentClass]} " +
                          f"({rankExpString})")

    baseClassStrings = [f"{baseClass.name[0] + baseClass.name[1:].lower()}: Rank {player.classRanks[baseClass]}/{MAX_BASE_CLASS_RANK}"
                        for baseClass in BasePlayerClassNames]
    embed.add_field(name="Base Classes:", value='\n'.join(baseClassStrings))

    availableAdvancedClasses = [advancedClass for advancedClass in AdvancedPlayerClassNames if player.classRequirementsMet(advancedClass)]
    advancedClassString = "(Level up Base Classes to unlock these!)"
    if len(availableAdvancedClasses) > 0:
        advancedClassStrings = [f"{advancedClass.name[0] + advancedClass.name[1:].lower()}: Rank {player.classRanks[advancedClass]}/{MAX_ADVANCED_CLASS_RANK}"
                                for advancedClass in availableAdvancedClasses]
        advancedClassString = '\n'.join(advancedClassStrings)
    embed.add_field(name="Advanced Classes:", value=advancedClassString)

    # TODO: may need scrolling options
    for classGroup in (BasePlayerClassNames, availableAdvancedClasses):
        for availableClass in classGroup:
            classButton = discord.ui.Button(label=f"{availableClass.name[0] + availableClass.name[1:].lower()}",
                                            style=discord.ButtonStyle.primary if classGroup is BasePlayerClassNames else discord.ButtonStyle.green,
                                            custom_id=f"{availableClass.name}", disabled=(availableClass == currentClass))
            classButton.callback = (lambda _class: lambda interaction: changeClassButton(interaction, session, player, _class))(availableClass)
            view.add_item(classButton)

    return embed
async def changeClassButton(interaction : discord.Interaction, session : GameSession, player : Player, newClass : PlayerClassNames):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return asyncio.sleep(0)
    player.changeClass(newClass)
    await session.currentView.refresh()
CHARACTER_CLASSES_SUBPAGE = InterfacePage("Classes", discord.ButtonStyle.secondary, [],
                                          characterClassesContent, lambda session: True, changePageCallback)

CHARACTER_PAGE = InterfacePage("Character", discord.ButtonStyle.secondary,
                               [CHARACTER_DETAIL_SUBPAGE, CHARACTER_STATS_SUBPAGE, CHARACTER_CLASSES_SUBPAGE],
                               None, lambda session: True, changePageCallback)
# TODO: free skill selection


#### Equipment

def equipMainContentFn(session : GameSession, view : InterfaceView):
    player = GLOBAL_STATE.accountDataMap[session.userId].currentCharacter
    embed = discord.Embed(title="Equipment", description="Click a number to see the associated item's details")

    focusItemIdx = view.pageData.get('focusItemIdx', None)

    if 'dropItem' in view.pageData and view.pageData['dropItem']:
        focusItem : Equipment = player.inventory[focusItemIdx]
        player.dropItem(focusItem)

        view.pageData.pop('dropItem')
        view.pageData['focusItemIdx'] = None
        focusItemIdx = None

    if focusItemIdx is None:
        if 'scrollIdx' not in view.pageData:
            view.pageData['scrollIdx'] = 0
        window_size = 5

        scrollWindowMin = view.pageData['scrollIdx'] * window_size
        scrollWindowMax = scrollWindowMin + window_size
        equipStrings = []
        for i in range(len(player.inventory)):
            item = player.inventory[i]
            equipString = f"**[{i+1}]** {player.inventory[i].getShortDescription()}"
            if item in player.equipment.values():
                equipString += " **[Equipped]**"
            equipStrings.append(equipString)

            if scrollWindowMin <= i and i < scrollWindowMax:
                itemButton = discord.ui.Button(label=f"{i+1}", style=discord.ButtonStyle.blurple, custom_id=item.name)
                itemButton.callback = (lambda j: lambda interaction: updateDataCallbackFn(interaction, session, view, 'focusItemIdx', j))(i)
                view.add_item(itemButton)

        embed.add_field(name="", value='\n'.join(equipStrings))
        if len(player.inventory) > window_size:
            backButton = discord.ui.Button(emoji="⬅️", style=discord.ButtonStyle.green, row=2)
            backButton.callback = lambda interaction: scrollCallbackFn(interaction, session, view, -1, len(player.inventory) // window_size)
            forwardButton = discord.ui.Button(emoji="➡️", style=discord.ButtonStyle.green, row=2)
            forwardButton.callback = lambda interaction: scrollCallbackFn(interaction, session, view, 1, len(player.inventory) // window_size)
            view.add_item(backButton)
            view.add_item(forwardButton)
    else:
        focusItem = player.inventory[focusItemIdx]
        currentlyEquipped = (focusItem in player.equipment.values())
        canEquip = player.canEquipWeapon(focusItem) if isinstance(focusItem, Weapon) else True

        equippedString = "(Currently Equipped)" if currentlyEquipped else ""
        embed.add_field(name=equippedString, value=focusItem.getDescription())
        equipButton = discord.ui.Button(label="Equip", style=discord.ButtonStyle.blurple, disabled=(currentlyEquipped or not canEquip))
        equipButton.callback = lambda interaction: equipCallbackFn(interaction, session, view, player, focusItem)
        view.add_item(equipButton)

        dropButton = discord.ui.Button(label="Drop", style=discord.ButtonStyle.red)
        dropButton.callback = lambda interaction: dropEquipCallbackFn(interaction, session, view, player, focusItem)
        view.add_item(dropButton)

        returnButton = discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary, custom_id="Back", row=2)
        returnButton.callback = lambda interaction: updateDataCallbackFn(interaction, session, view, 'focusItemIdx', None)
        view.add_item(returnButton)
    return embed
async def equipCallbackFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView, player : Player, item : Equipment):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return asyncio.sleep(0)
    player.equipItem(item)
    await view.refresh()
async def dropEquipCallbackFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView, player : Player, item : Equipment):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return asyncio.sleep(0)
    await view.requestConfirm(InterfaceConfirmation(
        f"Are you sure you want to drop {item.name}? You cannot get it back.", "Drop Item", "Cancel", "dropItem"))
EQUIPMENT_PAGE = InterfacePage("Equipment", discord.ButtonStyle.secondary, [],
                               equipMainContentFn, lambda session: True, changePageCallback)

#### Testing    

testPage1 = InterfacePage("1", discord.ButtonStyle.secondary,[],
                          lambda session, _: discord.Embed(title="One", description="first page").add_field(
                              name="hello", value=f"currently on {GLOBAL_STATE.accountDataMap[session.userId].currentCharacter.name}"),
                          lambda session: True, changePageCallback)
testPage2 = InterfacePage("2", discord.ButtonStyle.blurple, [],
                          lambda session, _: discord.Embed(title="Two", description="second page").add_field(name="goodbye", value="oh"),
                          lambda session: True, changePageCallback)
testPage3 = InterfacePage("3", discord.ButtonStyle.blurple, [],
                          lambda session, _: discord.Embed(title="Three", description="third page").add_field(name="maybe", value="huh"),
                          lambda session: True, changePageCallback)
testPage4 = InterfacePage("2/3", discord.ButtonStyle.secondary, [testPage2, testPage3],
                          None, lambda session: True, changePageCallback)

MAIN_MENU = InterfaceMenu([CHARACTER_PAGE, EQUIPMENT_PAGE, testPage4])