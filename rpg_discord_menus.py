from __future__ import annotations
import random
from typing import Callable, Coroutine
from typing import Callable, TYPE_CHECKING
import discord
import asyncio

from rpg_consts import *
from rpg_global_state import GLOBAL_STATE
from structures.rpg_classes_skills import ActiveSkillDataSelector, PlayerClassData, SkillData
from structures.rpg_combat_entity import CombatEntity, Player
from structures.rpg_combat_interface import CombatInputHandler, CombatInterface
from structures.rpg_combat_state import CombatController
from structures.rpg_dungeons import DungeonController, DungeonData, DungeonInputHandler
from structures.rpg_items import Equipment, Weapon
import gameData.rpg_dungeon_data
from structures.rpg_messages import LogMessageCollection, MessageCollector

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
    oldIdx = view.pageData.get(SCROLL_IDX, 0)
    await view.updateData(SCROLL_IDX, (oldIdx + amount) % (bounds + 1))

async def updateDataCallbackFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView, key : str, val):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return asyncio.sleep(0)
    await view.updateData(key, val)

async def updateDataMapCallbackFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView,
                                  mapKey : str, key : str, val):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return asyncio.sleep(0)
    mapVal = view.pageData.get(mapKey, {})
    mapVal[key] = val
    await view.updateData(mapKey, mapVal)

class InterfaceMenu(object):
    def __init__(self, pages : list[InterfacePage]):
        self.pages = pages

SCROLL_IDX = 'scrollIdx'
ACTION_CHOICE = 'actionChoice'
ACTION_CHOICE_DATA = 'actionChoiceData'

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


def characterClassSkillsContent(session : GameSession, view : InterfaceView):
    player = GLOBAL_STATE.accountDataMap[session.userId].currentCharacter
    currentClass = player.currentPlayerClass
    embed = discord.Embed(title="Class Skills",
                          description=f"{currentClass.name[0] + currentClass.name[1:].lower()} Rank {player.classRanks[currentClass]}")
    
    activeSkillStrings = []
    passiveSkillStrings = []
    for skill in PlayerClassData.getSkillsForRank(currentClass, player.classRanks[currentClass]):
        targetArray = activeSkillStrings if skill.isActiveSkill else passiveSkillStrings
        targetArray.append(getSkillDescription(skill))

    activeSkillString = "*None Yet*" if len(activeSkillStrings) == 0 else '\n\n'.join(activeSkillStrings)
    passiveSkillString = "*None Yet*" if len(passiveSkillStrings) == 0 else '\n\n'.join(passiveSkillStrings)
    embed.add_field(name="__Active Skills:__", value=activeSkillString)
    embed.add_field(name="__Passive Skills:__", value=passiveSkillString)

    return embed
def getSkillDescription(skill : SkillData) -> str:
    skillString = f"**{skill.skillName}** ({skill.playerClass.name[0] + skill.playerClass.name[1:].lower()} Rank {skill.rank})\n"
    skillString += f"{skill.description}"
    if skill.isActiveSkill:
        skillString += f"\nMP Cost: {skill.mpCost} \\|| {getSkillSpeed(skill)}"
        if skill.isFreeSkill:
            skillString += " \\|| **Free Skill**"
    return skillString
def getSkillSpeed(skill : SkillData) -> str:
    skillSpeed = skill.actionTime
    if skillSpeed is None:
        return "None"
    speedString = "Slow"
    if skillSpeed <= DEFAULT_ATTACK_TIMER_USAGE:
        speedString = "Normal"
    if skillSpeed <= MAX_ACTION_TIMER / 2:
        speedString = "Fast"
    if skillSpeed <= MAX_ACTION_TIMER / 5:
        speedString = "Very Fast"
    if skillSpeed <= 0:
        speedString = "Instant"
    return speedString 
CHARACTER_CLASS_SKILLS_SUBPAGE = InterfacePage("Class Skills", discord.ButtonStyle.secondary, [],
                                               characterClassSkillsContent,  lambda session: True, changePageCallback)


# TODO: free skill display/selection as another subpage
CHARACTER_SKILLS_SUBPAGE = InterfacePage("Skills", discord.ButtonStyle.secondary, [CHARACTER_CLASS_SKILLS_SUBPAGE],
                                         None, lambda session: True, changePageCallback)

CHARACTER_PAGE = InterfacePage("Character", discord.ButtonStyle.secondary,
                               [CHARACTER_DETAIL_SUBPAGE, CHARACTER_STATS_SUBPAGE, CHARACTER_CLASSES_SUBPAGE, CHARACTER_SKILLS_SUBPAGE],
                               None, lambda session: True, changePageCallback)


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
        if SCROLL_IDX not in view.pageData:
            view.pageData[SCROLL_IDX] = 0
        window_size = 5

        scrollWindowMin = view.pageData[SCROLL_IDX] * window_size
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


#### Dungeon Selection

def dungeonListContentFn(session : GameSession, view : InterfaceView):
    player = GLOBAL_STATE.accountDataMap[session.userId].currentCharacter
    embed = discord.Embed(title="Dungeons", description="Select a dungeon to enter/view details")

    focusDungeon : DungeonData | None = view.pageData.get('focusDungeon', None)

    if focusDungeon is None:
        if SCROLL_IDX not in view.pageData:
            view.pageData[SCROLL_IDX] = 0
        window_size = 5

        scrollWindowMin = view.pageData[SCROLL_IDX] * window_size
        scrollWindowMax = scrollWindowMin + window_size
        dungeonStrings = []
        availableDungeons = [dungeon for dungeon in DungeonData.registeredDungeons
                            if len(dungeon.milestoneRequirements.intersection(player.milestones)) == len(dungeon.milestoneRequirements)]
        for i in range(scrollWindowMin, scrollWindowMax):
            if i >= len(availableDungeons):
                break
            dungeon = availableDungeons[i]
            dungeonString = f"**{dungeon.dungeonName}**\n"
            dungeonString += f"*{dungeon.description}*\n"
            dungeonString += f"Rec. Level: {dungeon.recLevel} \\|| Max Party Size: {dungeon.maxPartySize}"
            dungeonStrings.append(dungeonString)

            dungeonButton = discord.ui.Button(label=f"{dungeon.shortDungeonName}", style=discord.ButtonStyle.blurple)
            dungeonButton.callback = (lambda j: lambda interaction: updateDataCallbackFn(interaction, session, view, 'focusDungeon', dungeon))(i)
            view.add_item(dungeonButton)

        embed.add_field(name="", value='\n\n'.join(dungeonStrings))
        if len(player.inventory) > window_size:
            backButton = discord.ui.Button(emoji="⬅️", style=discord.ButtonStyle.green, row=2)
            backButton.callback = lambda interaction: scrollCallbackFn(interaction, session, view, -1, len(availableDungeons) // window_size)
            forwardButton = discord.ui.Button(emoji="➡️", style=discord.ButtonStyle.green, row=2)
            forwardButton.callback = lambda interaction: scrollCallbackFn(interaction, session, view, 1, len(availableDungeons) // window_size)
            view.add_item(backButton)
            view.add_item(forwardButton)
    else:
        dungeonString = f"*{focusDungeon.description}*\n"
        dungeonString += f"Recommended Level: {focusDungeon.recLevel} \\|| Max Party Size: {focusDungeon.maxPartySize}\n"
        dungeonString += f"{len(focusDungeon.dungeonRooms)} Rooms \\|| Restore {focusDungeon.hpBetweenRooms*100:.1f}% HP/{focusDungeon.mpBetweenRooms*100:.1f}% MP between rooms"
        if focusDungeon.allowRetryFights:
            dungeonString += " \\|| Can retry fights"
        dungeonString += f"\nRewards: {focusDungeon.rewardDescription}"
        embed.add_field(name=f"Selected Dungeon: {focusDungeon.dungeonName}", value=dungeonString)

        enterButton = discord.ui.Button(label="Enter (Solo)", style=discord.ButtonStyle.green)
        enterButton.callback = lambda interaction: enterDungeonFn(interaction, session, focusDungeon)
        view.add_item(enterButton)

        # dropButton = discord.ui.Button(label="Drop", style=discord.ButtonStyle.red)
        # dropButton.callback = lambda interaction: dropEquipCallbackFn(interaction, session, view, player, focusItem)
        # view.add_item(dropButton)

        returnButton = discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary, custom_id="Back", row=2)
        returnButton.callback = lambda interaction: updateDataCallbackFn(interaction, session, view, 'focusDungeon', None)
        view.add_item(returnButton)

    return embed
async def enterDungeonFn(interaction : discord.Interaction, session : GameSession, dungeon : DungeonData):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return asyncio.sleep(0)
    await session.enterDungeon(dungeon)
DUNGEON_PAGE = InterfacePage("Dungeons", discord.ButtonStyle.secondary, [],
                             dungeonListContentFn, lambda session: True, changePageCallback)


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

MAIN_MENU = InterfaceMenu([CHARACTER_PAGE, EQUIPMENT_PAGE, DUNGEON_PAGE])

#### Dungeon Combat

def combatMainContentFn(session : GameSession, view : InterfaceView):
    assert(session.currentDungeon is not None)
    assert(session.currentDungeon.currentCombatInterface is not None)
    combatInterface = session.currentDungeon.currentCombatInterface

    player = GLOBAL_STATE.accountDataMap[session.userId].currentCharacter
    playerTurnString = f" - *{combatInterface.activePlayer}'s Turn*" if combatInterface.activePlayer is not None else ""
    if combatInterface.activePlayer == player:
        playerTurnString = " - *Your Turn!*"
    embed = discord.Embed(title=f"Combat{playerTurnString}", description="")

    combatLog : str = session.unseenCombatLog

    embed.add_field(name="__Player Team__", value=combatInterface.getPlayerTeamSummary(player))
    embed.add_field(name="__Opponent Team__", value=combatInterface.getEnemyTeamSummary(player))

    embed.add_field(name="__Combat Log__", value=combatLog, inline=False)

    if isPlayerTurn(session):
        combatHandler = combatInterface.handlerMap[player]
        assert(isinstance(combatHandler, DiscordCombatInputHandler))

        actionChoice : str = view.pageData.get(ACTION_CHOICE, None)
        actionChoiceData : dict = view.pageData.get(ACTION_CHOICE_DATA, {})
        if actionChoice == CombatActions.ATTACK:
            embed.description = "**Attack**: Select a target."

            targets = combatInterface.getOpponents(player, True)
            for target in targets:
                targetButton = discord.ui.Button(label=target.shortName, style=discord.ButtonStyle.green)
                targetButton.callback = (lambda _targ: lambda interaction:
                                         submitActionCallbackFn(interaction, session, view, combatHandler,
                                                                CombatActions.ATTACK, [_targ]))(target)
                view.add_item(targetButton)
        elif actionChoice == CombatActions.SKILL:
            chosenSkill : SkillData | None = actionChoiceData.get('chosenSkill', None)
            if chosenSkill is None:
                embed.description = f"**Skill**: Select a skill to use:\n"
                skillDescriptions = []
                for skill in player.availableActiveSkills:
                    skillDescriptions.append(f"__{skill.skillName}__ ({combatInterface.getSkillManaCost(player, skill)} MP): {skill.description}")

                    skillButton = discord.ui.Button(label=skill.skillName, style=discord.ButtonStyle.blurple)
                    skillButton.callback = (lambda _sk: lambda interaction:
                                            updateDataMapCallbackFn(interaction, session, view, ACTION_CHOICE_DATA, 'chosenSkill', _sk))(skill)
                    skillButton.disabled = not combatInterface.canPayForSkill(player, skill)

                    if combatInterface.isActiveToggle(player, skill):
                        skillButton = discord.ui.Button(label="Disable " + skill.skillName, style=discord.ButtonStyle.green)
                        skillButton.callback = (lambda _sk: lambda interaction:
                                                submitActionCallbackFn(interaction, session, view, combatHandler,
                                                                        CombatActions.SKILL, [], 0, _sk))(skill)

                    view.add_item(skillButton)
                embed.description += '\n'.join(skillDescriptions)
            elif isinstance(chosenSkill, ActiveSkillDataSelector):
                embed.description = f"**Skill**: Options for {chosenSkill.skillName}:\n{chosenSkill.optionDescription}"
                for option in chosenSkill.options:
                    optionName = option[0] + option[1:].lower()
                    optionSkill = chosenSkill.selectSkill(option)
                    optionButton = discord.ui.Button(label=optionName, style=discord.ButtonStyle.blurple)
                    optionButton.callback = (lambda _os: lambda interaction:
                                            updateDataMapCallbackFn(interaction, session, view, ACTION_CHOICE_DATA, 'chosenSkill', _os))(optionSkill)
                    optionButton.disabled = not combatInterface.canPayForSkill(player, optionSkill)
                    view.add_item(optionButton)
            else:
                selectedTargets : set[CombatEntity] = actionChoiceData.get('skillTargets', set())
                expectedTargets = chosenSkill.expectedTargets

                if expectedTargets == 0:
                    embed.description = f"**{chosenSkill.skillName}**: No targets needed."
                else:
                    amount = "any number of" if expectedTargets == None else f"{expectedTargets}"
                    embed.description = f"**{chosenSkill.skillName}**: Select {amount} target(s)."
                    if len(selectedTargets) > 0:
                        embed.description += f" Current targets: {', '.join([st.shortName for st in selectedTargets])}"

                    targetTeam = combatInterface.getOpponents(player, True) if chosenSkill.targetOpponents else combatInterface.getTeammates(player, True)
                    for target in targetTeam:
                        targetButton = discord.ui.Button(label=target.shortName)
                        if target in selectedTargets:
                            targetButton.style = discord.ButtonStyle.secondary
                            updatedTargets = selectedTargets.difference([target])
                            targetButton.callback = (lambda _ut: lambda interaction:
                                                    updateDataMapCallbackFn(interaction, session, view, ACTION_CHOICE_DATA, 'skillTargets', _ut))(updatedTargets)
                        else:
                            targetButton.style = discord.ButtonStyle.blurple
                            updatedTargets = selectedTargets.union([target])
                            targetButton.callback = (lambda _ut: lambda interaction:
                                                    updateDataMapCallbackFn(interaction, session, view, ACTION_CHOICE_DATA, 'skillTargets', _ut))(updatedTargets)
                            if expectedTargets is not None:
                                targetButton.disabled = len(selectedTargets) >= expectedTargets
                        view.add_item(targetButton)

                confirmButton = discord.ui.Button(label=f"Confirm Targets", style=discord.ButtonStyle.green)
                confirmButton.callback = lambda interaction: submitActionCallbackFn(interaction, session, view, combatHandler,
                                                                    CombatActions.SKILL, list(selectedTargets), 0, chosenSkill)
                if expectedTargets is not None:
                    confirmButton.disabled = len(selectedTargets) != expectedTargets
                else:
                    confirmButton.disabled = len(selectedTargets) == 0
                view.add_item(confirmButton)
        elif actionChoice == CombatActions.APPROACH:
            repositionHandler(True, session, view, combatInterface, player, combatHandler, embed, actionChoiceData)
        elif actionChoice == CombatActions.RETREAT:
            repositionHandler(False, session, view, combatInterface, player, combatHandler, embed, actionChoiceData)
        else:
            embed.description = "Select an action."

            buttonMap : dict[CombatActions, discord.ui.Button] = {}
            for option in CombatActions:
                buttonMap[option] = discord.ui.Button(label=option.name[0] + option.name[1:].lower(), style=discord.ButtonStyle.blurple)
                if option != CombatActions.DEFEND:
                    buttonMap[option].callback = (lambda _opt: lambda interaction:
                                                updateDataCallbackFn(interaction, session, view, ACTION_CHOICE, _opt))(option)
                
            buttonMap[CombatActions.DEFEND].style = discord.ButtonStyle.green
            buttonMap[CombatActions.DEFEND].callback = lambda interaction: submitActionCallbackFn(interaction, session, view, combatHandler,
                                                                                                  CombatActions.DEFEND, [])

            if len(player.availableActiveSkills) == 0:
                buttonMap[CombatActions.SKILL].disabled = True
            if not combatInterface.advancePossible(player):
                buttonMap[CombatActions.APPROACH].disabled = True
            if not combatInterface.retreatPossible(player):
                buttonMap[CombatActions.RETREAT].disabled = True
            [view.add_item(buttonMap[option]) for option in CombatActions]

        if actionChoice is not None:
            returnButton = discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary, custom_id="Back", row=2)
            if len(actionChoiceData) == 0:
                returnButton.callback = lambda interaction: updateDataCallbackFn(interaction, session, view, ACTION_CHOICE, None)
            else:
                returnButton.callback = lambda interaction: updateDataCallbackFn(interaction, session, view, ACTION_CHOICE_DATA, {})
            view.add_item(returnButton)
    return embed
def repositionHandler(isApproach : bool, session : GameSession, view : InterfaceView, combatInterface : CombatInterface,
                      player : Player, combatHandler : DiscordCombatInputHandler, embed : discord.Embed, actionChoiceData : dict):
    actionName = 'Approach' if isApproach else 'Retreat'
    changeString = 'Decrease' if isApproach else 'Increase'
    targetKey = 'approachTargets' if isApproach else 'retreatTargets'
    combatAction = CombatActions.APPROACH if isApproach else CombatActions.RETREAT
    amount = -1 if isApproach else 1

    selectedTargets : set[CombatEntity] = actionChoiceData.get(targetKey, set())
    if len(selectedTargets) > 0:
        embed.description = f"**{actionName}**: {changeString} distance from {', '.join([st.shortName for st in selectedTargets])}."
    else:
        embed.description = f"**{actionName}**: Select targets, then amount to move by."

    if not actionChoiceData.get('targetConfirm', False):
        targets = combatInterface.getOpponents(player, True)
        for target in targets:
            targetButton = discord.ui.Button(label=target.shortName)
            if target in selectedTargets:
                targetButton.style = discord.ButtonStyle.secondary
                updatedTargets = selectedTargets.difference([target])
                targetButton.callback = (lambda _ut: lambda interaction:
                                         updateDataMapCallbackFn(interaction, session, view, ACTION_CHOICE_DATA, targetKey, _ut))(updatedTargets)
            else:
                targetButton.style = discord.ButtonStyle.blurple
                updatedTargets = selectedTargets.union([target])
                targetButton.callback = (lambda _ut: lambda interaction:
                                         updateDataMapCallbackFn(interaction, session, view, ACTION_CHOICE_DATA, targetKey, _ut))(updatedTargets)
                targetButton.disabled = not combatInterface.validateReposition(player, list(selectedTargets) + [target], amount)
            view.add_item(targetButton)
        confirmButton = discord.ui.Button(label="Confirm Targets", style=discord.ButtonStyle.green, row=2, disabled=len(selectedTargets)==0)
        confirmButton.callback = lambda interaction: updateDataMapCallbackFn(interaction, session, view, ACTION_CHOICE_DATA, 'targetConfirm', True)
        view.add_item(confirmButton)
    else:
        oneButton = discord.ui.Button(label=f"{actionName} by 1", style=discord.ButtonStyle.green)
        oneButton.callback = lambda interaction: submitActionCallbackFn(interaction, session, view, combatHandler,
                                                        combatAction, list(selectedTargets), 1)
        view.add_item(oneButton)

        twoButton = discord.ui.Button(label=f"{actionName} by 2", style=discord.ButtonStyle.green)
        twoButton.callback = lambda interaction: submitActionCallbackFn(interaction, session, view, combatHandler,
                                                        combatAction, list(selectedTargets), 2)
        twoButton.disabled = not combatInterface.validateReposition(player, list(selectedTargets), amount * 2)
        view.add_item(twoButton)
async def submitActionCallbackFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView,
                                 handler : DiscordCombatInputHandler, action : CombatActions, targets : list[CombatEntity],
                                 amount : int = 0, skillData : SkillData | None = None):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return asyncio.sleep(0)
    session.unseenCombatLog = ""

    if action == CombatActions.ATTACK:
        handler.selectAttack(targets[0])
    elif action == CombatActions.SKILL:
        assert(skillData is not None)
        handler.selectSkill(targets, skillData)
    elif action == CombatActions.APPROACH:
        handler.selectAdvance(targets, amount)
    elif action == CombatActions.RETREAT:
        handler.selectRetreat(targets, amount)
    elif action == CombatActions.DEFEND:
        handler.selectDefend()

    view.pageData[ACTION_CHOICE] = None
    view.pageData[ACTION_CHOICE_DATA] = {}
def isPlayerTurn(session : GameSession) -> bool:
    if session.currentDungeon is None or session.currentDungeon.currentCombatInterface is None:
        return False
    player = session.getPlayer()
    if player is None:
        return False
    return session.currentDungeon.currentCombatInterface.activePlayer == player
COMBAT_MAIN_PAGE = InterfacePage("Actions", discord.ButtonStyle.secondary, [],
                                 combatMainContentFn, lambda session: True, changePageCallback,
                                 lambda session, _: discord.ButtonStyle.green if isPlayerTurn(session) else discord.ButtonStyle.secondary)

COMBAT_MENU = InterfaceMenu([COMBAT_MAIN_PAGE])


#### Dungeon/Combat Interaction

class DiscordDungeonInputHandler(DungeonInputHandler):
    def __init__(self, player : Player, session : GameSession):
        super().__init__(player, DiscordCombatInputHandler)
        self.session = session

    def makeCombatInputController(self):
        return DiscordCombatInputHandler(self.player, self.session)

    """
        Waits for the player to be ready for the dungeon rooms.
        Allows free skills, equips, and formation positions to be changed.
    """
    async def waitReady(self, dungeonController : DungeonController):
        # TODO
        # add a "waiting for allies" message before returning
        return True
    
    """
        Allows the player to choose between a set of text options.
        Returns the index of the selection.
    """
    async def makeChoice(self, dungeonController : DungeonController, options : list[str]):
        # TODO: offer choice of options
        return 0
    
    """
        Picks up a new equip; if inventory is full, gives the player the option to
        drop something from their inventory. (Should give a confirmation prompt as well; maybe add a way to lock items later?)
    """
    async def getEquip(self, dungeonController : DungeonController, newEquip : Equipment):
        hadSpace = self.player.storeEquipItem(newEquip)
        if not hadSpace:
            # TODO
            pass


class DiscordCombatInputHandler(CombatInputHandler):
    def __init__(self, player : Player, session : GameSession):
        super().__init__(player)
        self.session = session
        self.controller : CombatController | None = None
        self.actionFlag = asyncio.Event()

    def selectAttack(self, target : CombatEntity) -> bool:
        assert(self.controller is not None)
        self.doAttack(self.controller, target, None, None, True, [])
        self.actionFlag.set()
        return True
    
    def selectSkill(self, targets : list[CombatEntity], skillData : SkillData) -> bool:
        assert(self.controller is not None)
        result = self.doSkill(self.controller, targets, skillData)
        if result.success == ActionSuccessState.SUCCESS:
            self.actionFlag.set()
            return True
        return False
        
    def selectAdvance(self, targets : list[CombatEntity], amount : int) -> bool:
        assert(self.controller is not None)
        if self.doReposition(self.controller, targets, -amount):
            self.actionFlag.set()
            return True
        return False
        
    def selectRetreat(self, targets : list[CombatEntity], amount : int) -> bool:
        assert(self.controller is not None)
        if self.doReposition(self.controller, targets, amount):
            self.actionFlag.set()
            return True
        return False
        
    def selectDefend(self) -> bool:
        assert(self.controller is not None)
        self.doDefend(self.controller)
        self.actionFlag.set()
        return True

    async def takeTurn(self, combatController : CombatController) -> None:
        if not self.session.dungeonLoaded.is_set():
            await self.session.dungeonLoaded.wait()

        self.session.currentView.pageData[ACTION_CHOICE] = None
        self.session.currentView.pageData[ACTION_CHOICE_DATA] = {}
        self.controller = combatController

        await self.session.currentView.refresh()
        self.actionFlag.clear()
        await self.actionFlag.wait()
        await self.session.currentView.refresh()
    
class DiscordMessageCollector(MessageCollector):
    def __init__(self, session : GameSession):
        super().__init__()
        self.session = session
        self.pendingMessages = {}

    def sendAllMessages(self, filters : list[MessageType] | None, includeTypes : bool) -> LogMessageCollection:
        result = super().sendAllMessages(filters, includeTypes)
        resultString = result.getMessagesString(filters, includeTypes)
        self._updateViewLog(resultString)
        return result
    
    def sendNewestMessages(self, filters : list[MessageType] | None, includeTypes : bool) -> LogMessageCollection:
        result = super().sendNewestMessages(filters, includeTypes)
        resultString = result.getMessagesString(filters, includeTypes)
        self._updateViewLog(resultString)
        return result
    
    def _updateViewLog(self, newLog : str):
        self.session.unseenCombatLog += '\n' + newLog if self.session.unseenCombatLog else newLog

