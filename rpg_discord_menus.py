from __future__ import annotations
from datetime import datetime
import os
import random
from typing import Any, Callable, Coroutine
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
from structures.rpg_items import Equipment, EquipmentTrait, Weapon, getAdaptOptionsForEquip
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
                                 row=4-self.buttonDepth, disabled=not self.isButtonEnabled(session))
    
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

class RequestView(discord.ui.View):
    def __init__(self, userId : int, buttons : list[discord.ui.Button]):
        super().__init__(timeout=60)
        self.userId = userId
        self.buttons = buttons

        self.message : discord.Message | None = None
        
        for button in self.buttons:
            self.add_item(button)

    async def on_timeout(self):
        self.clear_items()
        if self.message is not None:
            await self.message.edit(view=self)

    async def checkedCallback(self, interaction : discord.Interaction, callback : Callable[[discord.Interaction], Coroutine]):
        await interaction.response.defer()
        if interaction.user.id != self.userId:
            return await asyncio.sleep(0)
        return await callback(interaction)
    
    async def close(self):
        self.clear_items()
        self.stop()

class PartyInfo(object):
    def __init__(self, creatorSession : GameSession, dungeonData : DungeonData):
        self.creatorSession = creatorSession
        self.allSessions : list[GameSession] = [creatorSession]
        self.dungeonData = dungeonData
        self.maxPartySize = dungeonData.maxPartySize

    """ Returns True if the session was successfully added """
    def joinParty(self, newSession : GameSession) -> bool:
        if newSession in self.allSessions:
            return False
        if len(self.allSessions) < self.maxPartySize:
            newSession.currentParty = self
            self.allSessions.append(newSession)
            return True
        return False
    
    """ Returns True if the party is now empty """
    def leaveParty(self, session : GameSession) -> bool:
        if session not in self.allSessions:
            return len(self.allSessions) == 0
        self.allSessions.remove(session)
        session.currentParty = None
        if len(self.allSessions) == 0:
            return True
        elif self.creatorSession == session:
            self.creatorSession = self.allSessions[0]
        return False
    
    def getSessionPlayerMap(self) -> dict[GameSession, Player]:
        result : dict[GameSession, Player] = {}
        for session in self.allSessions:
            player = session.getPlayer()
            assert (player is not None)
            result[session] = player
        return result
    
async def changePageCallback(session : GameSession, page : InterfacePage, interaction : discord.Interaction):
    await interaction.response.defer()
    await session.currentView.setPage(page)

async def scrollCallbackFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView, amount : int, bounds : int,
                           scrollIdxKey : str | None = None):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)
    if scrollIdxKey is None:
        scrollIdxKey = SCROLL_IDX
    oldIdx = view.pageData.get(scrollIdxKey, 0)
    await view.updateData(scrollIdxKey, (oldIdx + amount) % (bounds + 1))

async def updateDataCallbackFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView, key : str, val):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)
    await view.updateData(key, val)

async def updateDataMapCallbackFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView,
                                  mapKey : str, key : str, val):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)
    mapVal = view.pageData.get(mapKey, {})
    mapVal[key] = val
    await view.updateData(mapKey, mapVal)

async def sendPartyInvite(hostSession : GameSession, targetSession : GameSession):
    player = hostSession.getPlayer()
    party = hostSession.currentParty
    assert(party is not None and party.creatorSession == hostSession and player is not None)

    acceptButton = discord.ui.Button(label="Join Party", style=discord.ButtonStyle.green)
    requestView = RequestView(targetSession.userId, [acceptButton])

    acceptButton.callback = (lambda _ts, _rv: lambda interaction: partyInviteAcceptFn(
        interaction, hostSession, targetSession, party, requestView))(targetSession, requestView)
    
    assert(hostSession.currentMessage is not None)
    requestView.message = await hostSession.currentMessage.channel.send(
        f"{targetSession.savedMention}, you have been invited to a party for {party.dungeonData.dungeonName} by {player.name}! " +
        "(This invitation will expire in a minute.)",
        view=requestView)
    
class InterfaceMenu(object):
    def __init__(self, pages : list[InterfacePage]):
        self.pages = pages

SCROLL_IDX = 'scrollIdx'
TRAIT_SCROLL_IDX = 'traitScrollIdx'
ACTION_CHOICE = 'actionChoice'
ACTION_CHOICE_DATA = 'actionChoiceData'
DETAIL_FOCUS = 'detailFocus'
DUNGEON_SUBPAGE = 'dungeonSubpage'
PARTY_UPDATE = 'partyUpdate'

#### New Character

def newCharacterContent(session : GameSession, view : InterfaceView):
    showReminder = view.pageData.get("showReminder", False)

    classSelector = discord.ui.Select(placeholder="Class", options=[
        discord.SelectOption(label=f"{bc.name[0]}{bc.name[1:].lower()}", value=bc.name, description=CLASS_DESCRIPTION[bc])
        for bc in BasePlayerClassNames
    ])
    classSelector.callback = lambda interaction: interaction.response.defer() if interaction.user.id == session.userId else asyncio.sleep(0)
    view.add_item(classSelector)

    submitButton = discord.ui.Button(label="Confirm", style=discord.ButtonStyle.green, custom_id="confirm")
    submitButton.callback = lambda interaction: submitNewCharacter(interaction, session, classSelector)
    view.add_item(submitButton)

    embed = discord.Embed(title="Welcome to Chatanquest!", description=f"Creating a new character: {session.newCharacterName}\n")
    description = "This is a simple RPG where you can clear dungeons with friends. The classic " + \
        "'beat enemies to get items to beat stronger enemies' kind of thing.\n" + \
        "Choose a class below to start!"
    embed.add_field(name="", value=description, inline=False)
    
    if showReminder:
        embed.add_field(name="", value="(Remember to select a class!)", inline=False)

    return embed
async def submitNewCharacter(interaction : discord.Interaction, session : GameSession, classSelector : discord.ui.Select):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)
    try:
        chosenClass = BasePlayerClassNames[classSelector.values[0]]
        assert(session.newCharacterName is not None)
        GLOBAL_STATE.registerNewCharacter(interaction.user.id, session.newCharacterName, chosenClass, session)
        await session.loadNewMenu(MAIN_MENU)
    except IndexError:
        session.currentView.pageData['showReminder'] = True
        await session.currentView.refresh()
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

    embed.add_field(name="Stats:", value=player.getTotalStatString(), inline=False)
    
    levelExpString = f"{player.playerExp}/{player.getExpToNextLevel()}" if player.getExpToNextLevel() else "(MAX)"
    rankExpString = f"{player.classExp[currentClass]}/{player.getExpToNextRank()}" if player.getExpToNextRank() else "(MAX)"
    embed.add_field(name="EXP:", value=f"Player Level: {levelExpString}\nClass Rank: {rankExpString}")
    
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
                        value=f"**{player.getStatValue(stat)}** ({player.getBaseStatValue(stat)} Base; {player.statLevels[stat]} pts)")

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
        return await asyncio.sleep(0)
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
    rankExpString = f"Class Rank EXP: {player.classExp[currentClass]}/{player.getExpToNextRank()}" if player.getExpToNextRank() else "MAX"
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

    embed.add_field(name=enumName(currentClass), value=CLASS_DESCRIPTION[currentClass], inline=False)

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
        return await asyncio.sleep(0)
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
        targetArray.append(getSkillDescription(skill, True))

    activeSkillString = "*None Yet*" if len(activeSkillStrings) == 0 else '\n\n'.join(activeSkillStrings)
    passiveSkillString = "*None Yet*" if len(passiveSkillStrings) == 0 else '\n\n'.join(passiveSkillStrings)
    embed.add_field(name="__Active Skills:__", value=activeSkillString)
    embed.add_field(name="__Passive Skills:__", value=passiveSkillString)

    return embed
def getSkillDescription(skill : SkillData, includeFreeSkillTag : bool) -> str:
    skillString = f"**{skill.skillName}** ({skill.playerClass.name[0] + skill.playerClass.name[1:].lower()} Rank {skill.rank})\n"
    skillString += f"{skill.description}"
    if skill.isActiveSkill:
        skillString += f"\nMP Cost: {skill.mpCost} \\|| Speed: {getSkillSpeed(skill)}"
        if skill.isFreeSkill and includeFreeSkillTag:
            skillString += " \\|| **Free Skill**"
    elif skill.isFreeSkill and includeFreeSkillTag:
        skillString += "\n**Free Skill**"
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

def characterFreeSkillsContent(session : GameSession, view : InterfaceView):
    player = GLOBAL_STATE.accountDataMap[session.userId].currentCharacter
    embed = discord.Embed(title="Free Skills",
                          description=f"You can equip up to 4 Free Skills from classes (other than your current class) that you've ranked up.\n" +
                                "Use the arrows to locate the skill you'd like to equip/unequip.")
    
    equippedFreeSkills : list[SkillData] = []
    equippedFreeSkillStrings : list[str]  = []
    activeFreeSkillStrings : list[str]  = []
    availableFreeSkills : list[SkillData]  = []
    availableFreeSkillStrings : list[str]  = []
    currentSkillClasses = PlayerClassData.getAllClassDependencies(player.currentPlayerClass)
    
    for playerClass in player.classRanks:
        for skill in PlayerClassData.getFreeSkillsForRank(playerClass, player.classRanks[playerClass]):
            if (playerClass, skill.rank) in player.freeSkills:
                equippedFreeSkills.append(skill)
                equippedFreeSkillStrings.append(getSkillDescription(skill, False))
            else:
                availableFreeSkills.append(skill)
                if skill.playerClass in currentSkillClasses:
                    activeFreeSkillStrings.append(getSkillDescription(skill, False))
                else:
                    availableFreeSkillStrings.append(getSkillDescription(skill, False))

    equippedSkillString = "*None Yet*" if len(equippedFreeSkillStrings) == 0 else '\n'.join(equippedFreeSkillStrings)
    activeSkillString = "*None Yet*" if len(activeFreeSkillStrings) == 0 else '\n'.join(activeFreeSkillStrings)
    availableSkillString = "*None Yet*" if len(availableFreeSkillStrings) == 0 else '\n'.join(availableFreeSkillStrings)
    embed.add_field(name=f"__Equipped Free Skills ({len(equippedFreeSkills)}/{MAX_FREE_SKILLS}):__",
                    value=equippedSkillString, inline=False)
    embed.add_field(name="__Current Class Free Skills:__", value=activeSkillString, inline=False)
    embed.add_field(name="__Unlocked Free Skills:__", value=availableSkillString, inline=False)

    if SCROLL_IDX not in view.pageData:
        view.pageData[SCROLL_IDX] = 0
    window_size = 5

    currentScroll = view.pageData[SCROLL_IDX]
    equippedSkillOffset = len(equippedFreeSkills)
    if equippedSkillOffset > 0:
        if currentScroll == 0:
            for skill in equippedFreeSkills:
                skillButton = discord.ui.Button(label=f"-{skill.skillName}", style=discord.ButtonStyle.secondary)
                skillButton.callback = (lambda _skill:(lambda interaction:
                                                       toggleFreeSkillButton(interaction, session, player, _skill, False)))(skill)
                view.add_item(skillButton)

    atFreeSkillCapacity = len(player.freeSkills) >= MAX_FREE_SKILLS
    scrollWindowMin = view.pageData[SCROLL_IDX] * window_size - equippedSkillOffset
    scrollWindowMax = scrollWindowMin + window_size
    for i in range(scrollWindowMin, scrollWindowMax):
        if i >= 0 and i < len(availableFreeSkills):
            skill = availableFreeSkills[i]
            skillButton = discord.ui.Button(label=f"+{skill.skillName}", style=discord.ButtonStyle.blurple, disabled=atFreeSkillCapacity)
            if skill.playerClass in currentSkillClasses:
                skillButton.disabled = True
            skillButton.callback = (lambda _skill:(lambda interaction:
                                                    toggleFreeSkillButton(interaction, session, player, _skill, True)))(skill)
            view.add_item(skillButton)

    totalSkills = len(availableFreeSkills) + len(equippedFreeSkills)
    if totalSkills > window_size:
        backButton = discord.ui.Button(emoji="⬅️", style=discord.ButtonStyle.green, row=2)
        backButton.callback = lambda interaction: scrollCallbackFn(interaction, session, view, -1,
                                                                   (totalSkills-1) // window_size)
        forwardButton = discord.ui.Button(emoji="➡️", style=discord.ButtonStyle.green, row=2)
        forwardButton.callback = lambda interaction: scrollCallbackFn(interaction, session, view, 1,
                                                                      (totalSkills-1) // window_size)
        view.add_item(backButton)
        view.add_item(forwardButton)

    return embed
async def toggleFreeSkillButton(interaction : discord.Interaction, session : GameSession, player : Player,
                                skill : SkillData, equip : bool):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)
    if equip:
        player.addFreeSkill(skill.playerClass, skill.rank)
    else:
        player.removeFreeSkill(skill.playerClass, skill.rank)
    await session.currentView.refresh()
def checkFreeSkillAvailable(session : GameSession):
    player = GLOBAL_STATE.accountDataMap[session.userId].currentCharacter
    for playerClass in player.classRanks:
        if len(PlayerClassData.getFreeSkillsForRank(playerClass, player.classRanks[playerClass])) > 0:
            return True
    return False
CHARACTER_FREE_SKILLS_SUBPAGE = InterfacePage("Free Skills", discord.ButtonStyle.secondary, [],
                                               characterFreeSkillsContent,  checkFreeSkillAvailable, changePageCallback)

CHARACTER_SKILLS_SUBPAGE = InterfacePage("Skills", discord.ButtonStyle.secondary,
                                         [CHARACTER_CLASS_SKILLS_SUBPAGE, CHARACTER_FREE_SKILLS_SUBPAGE],
                                         None, lambda session: True, changePageCallback)

CHARACTER_PAGE = InterfacePage("Character", discord.ButtonStyle.secondary,
                               [CHARACTER_DETAIL_SUBPAGE, CHARACTER_STATS_SUBPAGE, CHARACTER_CLASSES_SUBPAGE, CHARACTER_SKILLS_SUBPAGE],
                               None, lambda session: True, changePageCallback)


#### Equipment

def equipMainContentFn(session : GameSession, view : InterfaceView):
    player = GLOBAL_STATE.accountDataMap[session.userId].currentCharacter
    embed = discord.Embed(title=f"Equipment ({len(player.inventory)}/{MAX_INVENTORY})",
                          description="Click a number to see the associated item's details")

    focusItemIdx = view.pageData.get('focusItemIdx', None)
    itemList = player.inventory
    inPending = False
    if focusItemIdx is not None and len(session.pendingItems) > 0:
        if focusItemIdx < len(session.pendingItems):
            itemList = session.pendingItems

            inPending = True
        else:
            focusItemIdx -= len(session.pendingItems)

    tradeItem = view.pageData.get('tradeItem', False)
    dropItem = view.pageData.get('dropItem', False)
    if tradeItem or dropItem:
        if inPending:
           focusItem = session.pendingItems.pop(focusItemIdx)
        else:
            focusItem = itemList[focusItemIdx]
            player.dropItem(focusItem)

        if dropItem:
            salePrice = focusItem.getSalePrice()
            player.wup += salePrice[0]
            player.swup += salePrice[1]
            view.pageData.pop('dropItem')
        else:
            view.pageData.pop('tradeItem')
        view.pageData['focusItemIdx'] = None
        focusItemIdx = None

    if focusItemIdx is None:
        if SCROLL_IDX not in view.pageData:
            view.pageData[SCROLL_IDX] = 0
        window_size = 5

        scrollWindowMin = view.pageData[SCROLL_IDX] * window_size
        scrollWindowMax = scrollWindowMin + window_size
        pendingStrings = []
        equipStrings = []
        for i in range(len(session.pendingItems)):
            item = session.pendingItems[i]
            pendingString = f"**[\\*{i+1}]** {session.pendingItems[i].getShortDescription()}"
            pendingStrings.append(pendingString)
            if scrollWindowMin <= i and i < scrollWindowMax:
                itemButton = discord.ui.Button(label=f"*{i+1}", style=discord.ButtonStyle.green, custom_id=item.name)
                itemButton.callback = (lambda j: lambda interaction: updateDataCallbackFn(interaction, session, view, 'focusItemIdx', j))(i)
                view.add_item(itemButton)

        idxOffset = len(session.pendingItems)
        for i in range(len(player.inventory)):
            item = player.inventory[i]
            equipString = f"**[{i+1}]** {player.inventory[i].getShortDescription()}"
            if item in player.equipment.values():
                equipString += " **[Equipped]**"
            equipStrings.append(equipString)
            if scrollWindowMin <= i + idxOffset and i + idxOffset < scrollWindowMax:
                itemButton = discord.ui.Button(label=f"{i+1}", style=discord.ButtonStyle.blurple, custom_id=item.name)
                if item in player.equipment.values():
                    itemButton.style = discord.ButtonStyle.green
                itemButton.callback = (lambda j: lambda interaction: updateDataCallbackFn(interaction, session, view, 'focusItemIdx', j))(i + idxOffset)
                view.add_item(itemButton)

        embed.add_field(name="", value='\n'.join(equipStrings), inline=False)
        if len(pendingStrings) > 0:
            embed.add_field(name="Pending Drops", value='\n'.join(pendingStrings), inline=False)
        if len(player.inventory)+idxOffset > window_size:
            backButton = discord.ui.Button(emoji="⬅️", style=discord.ButtonStyle.green, row=2)
            backButton.callback = lambda interaction: scrollCallbackFn(interaction, session, view, -1,
                                                                       (len(player.inventory)+idxOffset-1) // window_size)
            forwardButton = discord.ui.Button(emoji="➡️", style=discord.ButtonStyle.green, row=2)
            forwardButton.callback = lambda interaction: scrollCallbackFn(interaction, session, view, 1,
                                                                          (len(player.inventory)+idxOffset-1)  // window_size)
            view.add_item(backButton)
            view.add_item(forwardButton)
    else:
        focusItem : Equipment = itemList[focusItemIdx]
        adaptMenu = view.pageData.get('adaptMenu', False)
        giveMenu = view.pageData.get('giveMenu', False)

        if not adaptMenu and not giveMenu:
            currentlyEquipped = not inPending and (focusItem in player.equipment.values())
            canEquip = player.canEquipWeapon(focusItem) if isinstance(focusItem, Weapon) else True

            equippedString = " (Currently Equipped)" if currentlyEquipped else ""
            if inPending:
                equippedString = " (Pending Drop)"

            if not currentlyEquipped:
                compareItem = player.equipment.get(focusItem.equipSlot, None)
                if compareItem is not None:
                    embed.add_field(name=f"*Currently Equipped {enumName(focusItem.equipSlot)}:*",
                                    value=f"*{compareItem.getDescription()}*", inline=False)
            embed.add_field(name=f"Selected Item{equippedString}:", value=focusItem.getDescription(), inline=False)

            if inPending:
                keepButton = discord.ui.Button(label="Keep", style=discord.ButtonStyle.green, disabled=len(player.inventory)>=MAX_INVENTORY)
                keepButton.callback = lambda interaction: keepCallbackFn(interaction, session, view, player, focusItem)
                view.add_item(keepButton)
            else:
                rankIncreasePrice = focusItem.getRankIncreaseCost()
                rarityIncreasePrice = focusItem.getRarityIncreaseCost()
                salePrice = focusItem.getSalePrice()

                if not currentlyEquipped:
                    equipButton = discord.ui.Button(label="Equip", style=discord.ButtonStyle.blurple, disabled=not canEquip)
                    equipButton.callback = lambda interaction: equipCallbackFn(interaction, session, view, player, focusItem)
                    view.add_item(equipButton)
                else:
                    unequipButton = discord.ui.Button(label="Unequip", style=discord.ButtonStyle.gray, disabled=False)
                    unequipButton.callback = lambda interaction: unequipCallbackFn(interaction, session, view, player, focusItem)
                    view.add_item(unequipButton)

                if rankIncreasePrice is not None:
                    costString = f"Cost: {rankIncreasePrice[0]} WUP"
                    if rankIncreasePrice[1] > 0:
                        costString += f", {rankIncreasePrice[1]} SWUP"
                    embed.add_field(name="Rank Increase Available", value=f"{costString}\nYou have: {player.wup} WUP, {player.swup} SWUP")

                    canAfford = player.wup >= rankIncreasePrice[0] and player.swup >= rankIncreasePrice[1]
                    rankUpButton = discord.ui.Button(label="Increase Rank", style=discord.ButtonStyle.green, disabled=not canAfford)
                    rankUpButton.callback = lambda interaction: rankUpCallbackFn(interaction, session, view, player, focusItem)
                    view.add_item(rankUpButton)
                if rarityIncreasePrice is not None:
                    costString = f"Cost: {rarityIncreasePrice[0]} WUP"
                    if rarityIncreasePrice[1] > 0:
                        costString += f", {rarityIncreasePrice[1]} SWUP"
                    embed.add_field(name="Rarity Increase Available", value=f"{costString}\nYou have: {player.wup} WUP, {player.swup} SWUP")

                    canAfford = player.wup >= rarityIncreasePrice[0] and player.swup >= rarityIncreasePrice[1]
                    rarityUpButton = discord.ui.Button(label="Increase Rarity", style=discord.ButtonStyle.green, disabled=not canAfford)
                    rarityUpButton.callback = lambda interaction: rarityUpCallbackFn(interaction, session, view, player, focusItem)
                    view.add_item(rarityUpButton)

                saleString = f"{salePrice[0]} WUP"
                if salePrice[1] > 0:
                    saleString += f", {salePrice[1]} SWUP"
                embed.add_field(name="Sale Value", value=saleString)

                if focusItem.isAdaptable():
                    embed.add_field(name="Adaptation Available", value=f"Adaptations Applied: {focusItem.timesTraitsAdapted}")
                    adaptButton = discord.ui.Button(label="Adaptation", style=discord.ButtonStyle.blurple)
                    adaptButton.callback = lambda interaction: updateDataCallbackFn(interaction, session, view, 'adaptMenu', True)
                    view.add_item(adaptButton)

            if session.currentParty is not None:
                dropButton = discord.ui.Button(label="Give To Ally", style=discord.ButtonStyle.blurple)
                dropButton.callback = lambda interaction: updateDataCallbackFn(interaction, session, view, 'giveMenu', True)
                view.add_item(dropButton)

            dropButton = discord.ui.Button(label="Sell", style=discord.ButtonStyle.red)
            dropButton.callback = lambda interaction: dropEquipCallbackFn(interaction, session, view, player, focusItem)
            view.add_item(dropButton)

            returnButton = discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary, custom_id="Back", row=2)
            returnButton.callback = lambda interaction: updateDataCallbackFn(interaction, session, view, 'focusItemIdx', None)
            view.add_item(returnButton)
        elif adaptMenu:
            embed.add_field(name=f"Equipment Adaptation: {focusItem.name}",
                            value="Adaptation allows you to change the traits on an item. " + \
                                "Beware, it becomes more expensive every time it's performed on the same item.",
                            inline=False)
            
            errorMessage = view.pageData.get('')

            selectedTrait : EquipmentTrait | None = view.pageData.get('selectedTrait', None)
            if selectedTrait is None:
                if TRAIT_SCROLL_IDX not in view.pageData:
                    view.pageData[TRAIT_SCROLL_IDX] = 0
                window_size = 5

                scrollWindowMin = view.pageData[TRAIT_SCROLL_IDX] * window_size
                scrollWindowMax = scrollWindowMin + window_size
                traitOptionStrings = []
                traitOptions = getAdaptOptionsForEquip(focusItem)
                for i in range(len(traitOptions)):
                    trait = traitOptions[i]
                    adaptPrice = focusItem.getTraitAdaptSwupCost(trait)
                    assert adaptPrice is not None
                    traitOptionStrings.append(f"**[{i+1}]** {trait.summary} - *{adaptPrice} SWUP*")

                    if scrollWindowMin <= i and i < scrollWindowMax:
                        canAfford = player.swup >= adaptPrice
                        traitButton = discord.ui.Button(label=f"{i+1}", style=discord.ButtonStyle.blurple,
                                                        disabled=trait in focusItem.traits or not canAfford)
                        traitButton.callback = (lambda _t: lambda interaction:
                                                updateDataCallbackFn(interaction, session, view, 'selectedTrait', _t))(trait)
                        view.add_item(traitButton)

                traitOptionHalfIdx = len(traitOptionStrings) // 2
                embed.add_field(name="Select New Trait:", value='\n'.join(traitOptionStrings[:traitOptionHalfIdx]))
                embed.add_field(name="\n", value='\n'.join(traitOptionStrings[traitOptionHalfIdx:]))
                if len(traitOptions) > window_size:
                    backButton = discord.ui.Button(emoji="⬅️", style=discord.ButtonStyle.green, row=2)
                    backButton.callback = lambda interaction: scrollCallbackFn(interaction, session, view, -1,
                                                                            (len(traitOptions)-1) // window_size, TRAIT_SCROLL_IDX)
                    forwardButton = discord.ui.Button(emoji="➡️", style=discord.ButtonStyle.green, row=2)
                    forwardButton.callback = lambda interaction: scrollCallbackFn(interaction, session, view, 1,
                                                                                (len(traitOptions)-1)  // window_size, TRAIT_SCROLL_IDX)
                    view.add_item(backButton)
                    view.add_item(forwardButton)

                returnButton = discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary, custom_id="Back", row=2)
                returnButton.callback = lambda interaction: updateDataCallbackFn(interaction, session, view, 'adaptMenu', False)
                view.add_item(returnButton)
            else:
                selectedSlot = view.pageData.get('selectedSlot', None)
                if len(focusItem.traits) == 1:
                    selectedSlot = 0
                
                if selectedSlot is None:
                    embed.add_field(name="Choose Trait to Replace",
                                    value=f"**Selected New Trait:** {selectedTrait.summary}", inline=False)
                    traitStrings = []
                    for i in range(len(focusItem.traits)):
                        trait = focusItem.traits[i]
                        traitStrings.append(f"**[{i+1}]** {trait.summary}")

                        traitButton = discord.ui.Button(label=f"{i+1}", style=discord.ButtonStyle.blurple)
                        traitButton.callback = (lambda j: lambda interaction:
                                                updateDataCallbackFn(interaction, session, view, 'selectedSlot', j))(i)
                        view.add_item(traitButton)
                    embed.add_field(name="**Current Item Traits:**",
                                    value='\n'.join(traitStrings), inline=False)

                    returnButton = discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary, custom_id="Back", row=2)
                    returnButton.callback = lambda interaction: updateDataCallbackFn(interaction, session, view, 'selectedTrait', None)
                    view.add_item(returnButton)
                else:
                    embed.add_field(name="Confirmation",
                                    value=f"**Replacing:** {focusItem.traits[selectedSlot].summary}\n" + \
                                            f"**With:** {selectedTrait.summary}\n" + \
                                            f"**Cost: {focusItem.getTraitAdaptSwupCost(selectedTrait)} SWUP**")
                    embed.add_field(name="Reminder:", value="Adapting this item further in the future will have an increased cost. " + \
                                        "Once you replace the old trait, it may be difficult and/or expensive to get it back.")
                    
                    confirmButton = discord.ui.Button(label="Confirm Adaptation", style=discord.ButtonStyle.green)
                    confirmButton.callback = lambda interaction: adaptCallbackFn(interaction, session, view, player,
                                                                                 focusItem, selectedTrait, selectedSlot)
                    view.add_item(confirmButton)

                    returnButton = discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary, custom_id="Back", row=2)
                    returnButton.callback = lambda interaction: adaptBackFn(interaction, session, view)
                    view.add_item(returnButton)
        elif giveMenu:
            embed.add_field(name=f"Give To Party Member: {focusItem.name}",
                            value="Choose a party member to give this item to.\n" + \
                                "Note that the item will be sent immediately upon selecting a party member, but they can always just give it back to you (right...?).",
                            inline=False)
            
            errorMessage = view.pageData.get('sendItemError', '')
            if len(errorMessage) > 0:
                embed.add_field(name="Error:", value=errorMessage)
            
            assert session.currentParty is not None
            for partySession in session.currentParty.allSessions:
                partyPlayer = partySession.getPlayer()
                if partyPlayer is None or partyPlayer == player:
                    continue
                sendButton = discord.ui.Button(label=f"{partyPlayer.name}", style=discord.ButtonStyle.green)
                sendButton.callback = (lambda _tp, _ts: lambda interaction: sendItemCallbackFn(
                    interaction, session, view, player, focusItem, _tp, _ts))(partyPlayer, partySession)
                view.add_item(sendButton)

            returnButton = discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary, custom_id="Back", row=2)
            returnButton.callback = lambda interaction: updateDataCallbackFn(interaction, session, view, 'giveMenu', False)
            view.add_item(returnButton)

    return embed
async def equipCallbackFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView, player : Player, item : Equipment):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)
    player.equipItem(item)
    await view.refresh()
async def unequipCallbackFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView, player : Player, item : Equipment):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)
    player.unequipItem(item.equipSlot)
    await view.refresh()
async def rankUpCallbackFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView, player : Player, item : Equipment):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)
    player.increaseItemRank(item)
    await view.refresh()
async def rarityUpCallbackFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView, player : Player, item : Equipment):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)
    player.increaseItemRarity(item)
    await view.refresh()
async def adaptCallbackFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView, player : Player,
                          item : Equipment, newTrait : EquipmentTrait, replaceTraitIdx : int):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)
    player.adaptItem(item, replaceTraitIdx, newTrait)
    view.pageData['adaptMenu'] = False
    view.pageData['selectedTrait'] = None
    view.pageData['selectedSlot'] = None
    await view.refresh()
async def sendItemCallbackFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView,
                             player : Player, item : Equipment, target : Player, targetSession : GameSession):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)
    if not target.storeEquipItem(item):
        view.pageData['sendItemError'] = f"{target.name}'s inventory is full! Have them drop or send something away before trying again."
    else:
        if session.currentMessage is not None:
            await session.currentMessage.channel.send(
                f"{targetSession.savedMention}, you have received **{item.name}** from {player.name}!")
        
        view.pageData['giveMenu'] = False
        view.pageData['sendItemError'] = ''
        view.pageData['tradeItem'] = True
    await view.refresh()
async def adaptBackFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)
    view.pageData['selectedTrait'] = None
    view.pageData['selectedSlot'] = None
    await view.refresh()
async def dropEquipCallbackFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView, player : Player, item : Equipment):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)
    salePrice = item.getSalePrice()
    saleString = f"{salePrice[0]} WUP"
    if salePrice[1] > 0:
        saleString += f" and {salePrice[1]} SWUP"
    await view.requestConfirm(InterfaceConfirmation(
        f"Are you sure you want to sell {item.name}? You will receive {saleString}, but you cannot get the item back.", "Sell Item", "Cancel", "dropItem"))
async def keepCallbackFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView, player : Player, item : Equipment):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)
    player.storeEquipItem(item)
    session.pendingItems.remove(item)
    view.pageData['focusItemIdx'] = None
    await view.refresh()
def equipStyle(session : GameSession, view : InterfaceView):
    if len(session.pendingItems) > 0:
        return discord.ButtonStyle.green
    else:
        return discord.ButtonStyle.secondary
EQUIPMENT_PAGE = InterfacePage("Equipment", discord.ButtonStyle.secondary, [],
                               equipMainContentFn, lambda session: True, changePageCallback, equipStyle)


#### Dungeon Selection

def dungeonListContentFn(session : GameSession, view : InterfaceView):
    player = GLOBAL_STATE.accountDataMap[session.userId].currentCharacter
    embed = discord.Embed(title="Dungeons", description="Select a dungeon to enter/view details")

    focusDungeon : DungeonData | None = view.pageData.get('focusDungeon', None)
    if session.currentParty is not None:
        focusDungeon = session.currentParty.dungeonData
    dungeonSubpage : str = view.pageData.get(DUNGEON_SUBPAGE, '')

    if focusDungeon is None:
        view.pageData[DUNGEON_SUBPAGE] = ''
        if SCROLL_IDX not in view.pageData:
            view.pageData[SCROLL_IDX] = 0
        window_size = 5

        scrollWindowMin = view.pageData[SCROLL_IDX] * window_size
        scrollWindowMax = scrollWindowMin + window_size
        dungeonStrings = []
        availableDungeons = [dungeon for dungeon in DungeonData.registeredDungeons if dungeon.meetsRequirements(player)]
        for i in range(scrollWindowMin, scrollWindowMax):
            if i >= len(availableDungeons):
                break
            dungeon = availableDungeons[i]
            clearSymbol = "⭐" if dungeon.clearFlag in player.milestones else ""
            dungeonString = f"**{dungeon.dungeonName}**{clearSymbol}\n"
            shortDescription = dungeon.description.split('\n')[0]
            dungeonString += f"*{shortDescription}*\n"
            dungeonString += f"Rec. Level: {dungeon.recLevel} \\|| Max Party Size: {dungeon.maxPartySize}"
            dungeonStrings.append(dungeonString)

            dungeonButton = discord.ui.Button(label=f"{dungeon.shortDungeonName}", style=discord.ButtonStyle.blurple)
            dungeonButton.callback = (lambda _dungeon: lambda interaction: updateDataCallbackFn(interaction, session, view, 'focusDungeon', _dungeon))(dungeon)
            view.add_item(dungeonButton)

        embed.add_field(name="", value='\n\n'.join(dungeonStrings))
        if len(availableDungeons) > window_size:
            backButton = discord.ui.Button(emoji="⬅️", style=discord.ButtonStyle.green, row=2)
            backButton.callback = lambda interaction: scrollCallbackFn(interaction, session, view, -1,
                                                                       (len(availableDungeons)-1) // window_size)
            forwardButton = discord.ui.Button(emoji="➡️", style=discord.ButtonStyle.green, row=2)
            forwardButton.callback = lambda interaction: scrollCallbackFn(interaction, session, view, 1,
                                                                          (len(availableDungeons)-1) // window_size)
            view.add_item(backButton)
            view.add_item(forwardButton)
    else:
        dungeonString = f"*{focusDungeon.description}*\n"
        dungeonString += f"Recommended Level: {focusDungeon.recLevel} \\|| Max Party Size: {focusDungeon.maxPartySize}\n"
        dungeonString += f"{len(focusDungeon.dungeonRooms)} Rooms \\|| Restore {focusDungeon.hpBetweenRooms*100:.1f}% HP/{focusDungeon.mpBetweenRooms*100:.1f}% MP between rooms"
        if focusDungeon.allowRetryFights:
            dungeonString += " \\|| Can retry fights"
        dungeonString += f"\nExpected Rewards: {focusDungeon.rewardDescription}"
        embed.add_field(name=f"Selected Dungeon: {focusDungeon.dungeonName}", value=dungeonString, inline=False)

        partyUpdate = view.pageData.get(PARTY_UPDATE, '')
        if len(partyUpdate) > 0:
            embed.add_field(name="Party Updated", value=partyUpdate, inline=False)

        enterButton = discord.ui.Button(label="Enter (Solo)", style=discord.ButtonStyle.green, row=2)
        enterButton.callback = lambda interaction: enterDungeonFn(interaction, session, focusDungeon)
        view.add_item(enterButton)

        # Party handling
        inviteToPartyButton = discord.ui.Button(label="Invite Players", style=discord.ButtonStyle.blurple, row=3, disabled=True)
        inviteToPartyButton.callback = lambda interaction: updateDataCallbackFn(interaction, session, view, DUNGEON_SUBPAGE, 'invite')
        view.add_item(inviteToPartyButton)

        if session.currentParty is None:
            makePartyButton = discord.ui.Button(label="Make Party", style=discord.ButtonStyle.blurple, row=2)
            makePartyButton.callback = lambda interaction: makePartyFn(interaction, session, view, focusDungeon)
            if focusDungeon.maxPartySize <= 1:
                makePartyButton.disabled = True
            view.add_item(makePartyButton)
        else:
            leavePartyButton = discord.ui.Button(label="Leave Party", style=discord.ButtonStyle.red, row=2)
            leavePartyButton.callback = lambda interaction: leavePartyFn(interaction, session, view)
            view.add_item(leavePartyButton)

            if session.currentParty.creatorSession == session:
                enterButton.label = "Enter (Party)"
                if len(session.currentParty.allSessions) < focusDungeon.maxPartySize:
                    inviteToPartyButton.disabled = False
            else:
                enterButton.label = "Waiting for Leader"
                enterButton.disabled = True


        formationButton = discord.ui.Button(label="Formation", style=discord.ButtonStyle.blurple, row=3,
                                            disabled=player.level <= 1)
        formationButton.callback = lambda interaction: updateDataCallbackFn(interaction, session, view, DUNGEON_SUBPAGE, 'formation')
        view.add_item(formationButton)

        # Subpages
        if dungeonSubpage == 'formation':
            formationButton.disabled = True

            startingPositionStrings = []
            for partySession in session.getPartySessions():
                partyPlayer = partySession.getPlayer()
                assert partyPlayer is not None
                penaltyString = " (initiative penalty)" if partySession.defaultFormationDistance != DEFAULT_STARTING_DISTANCE else ""
                startingPositionStrings.append(f"**{partyPlayer.name}**: {partySession.defaultFormationDistance}{penaltyString}")
            startingPositionString = '\n'.join(startingPositionStrings)

            embed.add_field(name="Starting Positions",
                            value=f"You can change the distance at which you start from enemies (default is {DEFAULT_STARTING_DISTANCE}), " +
                            "but doing so will often cause you to lose initiative. Coordinate with teammates to find a balance!\n\n" +
                            f"__Starting Distances:__\n{startingPositionString}", inline=False)
            
            for dist in [1, 2, 3]:
                distButton = discord.ui.Button(label=f"Start Dist. {dist}", style=discord.ButtonStyle.blurple,
                                               disabled=session.defaultFormationDistance==dist)
                distButton.callback = (lambda _i: (lambda interaction: updateFormationFn(interaction, session, view, player, _i)))(dist)
                view.add_item(distButton)

        if dungeonSubpage == 'invite':
            inviteToPartyButton.disabled = True
            assert(session.currentParty is not None)

            embed.add_field(name='Invite Players',
                            value="You can use the dropdown below to add available players to your party, or you can " +
                            "use the 'invite [user]' command to invite a player by their discord username. Everyone in " +
                            "the party will enter the dungeon when you press Enter (Party).", inline=False)
            
            foundPlayers : list[Player] = []
            sessionList : list[GameSession] = []
            if session.currentMessage is not None:
                messageGuild = session.currentMessage.guild
                if messageGuild is not None:
                    messageMemberIds = [member.id for member in messageGuild.members]
                    registeredMemberIds = [memberId for memberId in messageMemberIds if GLOBAL_STATE.idRegistered(memberId)]
                    for memberId in registeredMemberIds:
                        memberSession = GLOBAL_STATE.accountDataMap[memberId].session
                        if memberSession in session.currentParty.allSessions:
                            continue
                        sessionPlayer = memberSession.getPlayer()
                        if sessionPlayer is not None and focusDungeon.meetsRequirements(sessionPlayer) and memberSession.safeToSwitch():
                            foundPlayers.append(sessionPlayer)
                            sessionList.append(memberSession)
            inviteOptions = [
                discord.SelectOption(label=foundPlayer.name, value=str(idx),
                                     description=f"Level {foundPlayer.level} {foundPlayer.currentPlayerClass.name[0]+foundPlayer.currentPlayerClass.name[1:].lower()}")
                for idx, foundPlayer in enumerate(foundPlayers)
            ]
            view.pageData['inviteOptions'] = sessionList

            partySpace = focusDungeon.maxPartySize - len(session.currentParty.allSessions)
            placeholderText = "Select Players"
            canSelectMore = partySpace >= 1
            if len(inviteOptions) == 0:
                inviteOptions = [discord.SelectOption(label="-", value="None")]
                placeholderText = "No other eligible players available"
                canSelectMore = False

            inviteSelector = discord.ui.Select(placeholder=placeholderText, options=inviteOptions,
                                               max_values=min(1, partySpace), disabled=not canSelectMore)
            inviteSelector.callback = lambda interaction: interaction.response.defer() if interaction.user.id == session.userId else asyncio.sleep(0)
            view.add_item(inviteSelector)

            inviteSendButton = discord.ui.Button(label="Send Invite(s)", style=discord.ButtonStyle.green, disabled=not canSelectMore)
            inviteSendButton.callback = lambda interaction: partyInviteFn(interaction, session, view, inviteSelector)
            view.add_item(inviteSendButton)

        returnButton = discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary, custom_id="Back", row=2,
                                         disabled=session.currentParty is not None)
        returnButton.callback = lambda interaction: updateDataCallbackFn(interaction, session, view, 'focusDungeon', None)
        view.add_item(returnButton)

    return embed
async def updateFormationFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView, player : Player, newDist : int):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)
    session.defaultFormationDistance = newDist
    if session.currentDungeon is not None:
        session.currentDungeon.startingPlayerTeamDistances[player] = newDist
    await view.refresh()
async def enterDungeonFn(interaction : discord.Interaction, session : GameSession, dungeon : DungeonData):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)
    await session.enterDungeon(dungeon)
async def makePartyFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView, dungeon : DungeonData):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)
    assert(session.currentParty is None)
    session.currentParty = PartyInfo(session, dungeon)
    view.pageData[PARTY_UPDATE] = "Created a new party! Use the Invite Players option or 'invite [user]' command to add players."
    await view.refresh()
async def partyInviteFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView,
                        inviteSelector : discord.ui.Select):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)

    inviteOptions = view.pageData['inviteOptions']
    targetSessions : list[GameSession] = [inviteOptions[int(val)] for val in inviteSelector.values]

    view.pageData[PARTY_UPDATE] = "Sending party invites!"

    for targetSession in targetSessions:
        await sendPartyInvite(session, targetSession)

    await view.refresh()
async def partyInviteAcceptFn(interaction : discord.Interaction, hostSession : GameSession, joiningSession : GameSession,
                        party : PartyInfo, inviteView : RequestView):
    if interaction.user.id != joiningSession.userId:
        await interaction.response.defer()
        return await asyncio.sleep(0)
    await inviteView.close()
    await interaction.response.edit_message(view=inviteView)

    joiningPlayer = joiningSession.getPlayer()
    assert(joiningPlayer is not None)
    
    hostParty = hostSession.currentParty
    failureMessage = ""
    if hostParty is None or hostParty != party:
        failureMessage = "The leader of the party you were invited to has changed."
    elif hostSession.currentDungeon is not None:
        failureMessage = "The party has already entered the dungeon."
    elif len(party.allSessions) >= party.dungeonData.maxPartySize:
        failureMessage = "The party is already full."

    if len(failureMessage) > 0:
        if joiningSession.currentMessage is not None:
            await joiningSession.currentMessage.channel.send(f"{joiningPlayer.name} could not join: {failureMessage}")
    else:
        assert(hostParty is not None)
        if hostParty.joinParty(joiningSession):
            hostSession.currentView.pageData[PARTY_UPDATE] = hostSession.currentView.pageData.get(PARTY_UPDATE, "") + \
                f"\n{joiningPlayer.name} joined the party!"
            await hostSession.currentView.refresh()
            if joiningSession.isActive:
                await joiningSession.currentView.refresh()
async def leavePartyFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)
    party = session.currentParty
    assert(party is not None)

    wasPreviousLeader = party.creatorSession == session
    partyDisbanded = party.leaveParty(session)
    extraUpdateString = ""
    if partyDisbanded:
        extraUpdateString = " The party is empty and has been disbanded."
    else:
        newLeaderPlayer = party.creatorSession.getPlayer()
        if wasPreviousLeader:
            assert(newLeaderPlayer is not None)
            extraUpdateString = f" {newLeaderPlayer.name} is now the party leader."
            party.creatorSession.currentView.pageData[PARTY_UPDATE] = "Control over the party has been passed to you."
        player = session.getPlayer()
        assert(player is not None)
        party.creatorSession.currentView.pageData[PARTY_UPDATE] += f"\n{player.name} left the party."
        if party.creatorSession.isActive:
            await party.creatorSession.currentView.refresh()
    view.pageData[PARTY_UPDATE] = f"You left the party.{extraUpdateString}"
    view.pageData[DUNGEON_SUBPAGE] = ''

    await view.refresh()
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

def _abridgeCombatLog(logString : str):
    if len(logString) >= DISPLAY_LOG_THRESHOLD:
        logString = '\n'.join(logString[4 - DISPLAY_LOG_THRESHOLD:].split('\n')[1:])
        logString = "(...)" + logString[4 - DISPLAY_LOG_THRESHOLD:]
    return logString
async def expandLogFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView, logger : MessageCollector):
    if interaction.user.id != session.userId:
        await interaction.response.defer()
        return await asyncio.sleep(0)
    logString = session.unseenCombatLog

    mentionString = session.savedMention
    await interaction.response.send_message(f"{mentionString} Log since last turn:\n{logString}", ephemeral=True)
    await view.refresh()

def combatMainContentFn(session : GameSession, view : InterfaceView):
    assert(session.currentDungeon is not None)
    assert(session.currentDungeon.currentCombatInterface is not None)
    combatInterface = session.currentDungeon.currentCombatInterface

    player = GLOBAL_STATE.accountDataMap[session.userId].currentCharacter
    playerTurnString = f" - *{combatInterface.activePlayer.name}'s Turn*" if combatInterface.activePlayer is not None else ""
    if combatInterface.activePlayer == player:
        playerTurnString = " - *Your Turn!*"
    embed = discord.Embed(title=f"Combat{playerTurnString}", description="")
    instructionTitle = ""
    instructionContent = ""

    combatLog : str = _abridgeCombatLog(session.unseenCombatLog)
    if len(session.unseenCombatLog) > DISPLAY_LOG_THRESHOLD:
        logger = session.currentDungeon.loggers[player]
        logCatchupButton = discord.ui.Button(label="Expand Log", style=discord.ButtonStyle.blurple, row=4)
        logCatchupButton.callback = lambda interaction: expandLogFn(interaction, session, view, logger)
        view.add_item(logCatchupButton)

    embed.add_field(name="__Player Team__", value=combatInterface.getPlayerTeamSummary(player))
    embed.add_field(name="__Opponent Team__", value=combatInterface.getEnemyTeamSummary(player))

    embed.add_field(name="__Combat Log__", value=combatLog, inline=False)

    if isPlayerTurn(session):
        combatHandler = combatInterface.handlerMap[player]
        assert(isinstance(combatHandler, DiscordCombatInputHandler))

        actionChoice : str = view.pageData.get(ACTION_CHOICE, None)
        actionChoiceData : dict = view.pageData.get(ACTION_CHOICE_DATA, {})
        if actionChoice == CombatActions.ATTACK:
            instructionTitle = "Attack"
            instructionContent = "Select a target."

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
                instructionTitle = "Skill"
                instructionContent = "Select a skill to use:\n"
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
                instructionContent += '\n'.join(skillDescriptions)
            elif isinstance(chosenSkill, ActiveSkillDataSelector):
                instructionTitle = "Skill"
                instructionContent = f"Options for {chosenSkill.skillName}:\n{chosenSkill.optionDescription}"
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

                instructionTitle = f"{chosenSkill.skillName}"
                if expectedTargets == 0:
                    instructionContent = f"No targets needed."
                else:
                    amount = "any number of" if expectedTargets == None else f"{expectedTargets}"
                    instructionContent = f"Select {amount} target(s)."
                    if len(selectedTargets) > 0:
                        instructionContent += f" Current targets: {', '.join([st.shortName for st in selectedTargets])}"

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
            instructionTitle, instructionContent = repositionHandler(
                True, session, view, combatInterface, player, combatHandler, embed, actionChoiceData)
        elif actionChoice == CombatActions.RETREAT:
            instructionTitle, instructionContent = repositionHandler(
                False, session, view, combatInterface, player, combatHandler, embed, actionChoiceData)
        else:
            instructionTitle = "Select an action."
            instructionContent = f"*Your current Basic Attack Range is {combatInterface.getRange(player)}.*"

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

            targets = combatInterface.getOpponents(player, True)
            if len(targets) == 1:
                target = targets[0]
                buttonMap[CombatActions.ATTACK].style = discord.ButtonStyle.green
                buttonMap[CombatActions.ATTACK].callback = (lambda _targ: lambda interaction:
                                                            submitActionCallbackFn(interaction, session, view, combatHandler,
                                                                                   CombatActions.ATTACK, [_targ]))(target)
            [view.add_item(buttonMap[option]) for option in CombatActions]

        if actionChoice is not None:
            returnButton = discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary, custom_id="Back", row=2)
            if len(actionChoiceData) == 0:
                returnButton.callback = lambda interaction: updateDataCallbackFn(interaction, session, view, ACTION_CHOICE, None)
            else:
                returnButton.callback = lambda interaction: updateDataCallbackFn(interaction, session, view, ACTION_CHOICE_DATA, {})
            view.add_item(returnButton)
    if len(instructionTitle + instructionContent) > 0:
        embed.add_field(name=f"__*{instructionTitle}*__", value=instructionContent)
    return embed
def repositionHandler(isApproach : bool, session : GameSession, view : InterfaceView, combatInterface : CombatInterface,
                      player : Player, combatHandler : DiscordCombatInputHandler, embed : discord.Embed, actionChoiceData : dict):
    actionName = 'Approach' if isApproach else 'Retreat'
    changeString = 'Decrease' if isApproach else 'Increase'
    targetKey = 'approachTargets' if isApproach else 'retreatTargets'
    combatAction = CombatActions.APPROACH if isApproach else CombatActions.RETREAT
    amount = -1 if isApproach else 1
    opponents = combatInterface.getOpponents(player, True)

    targetConfirm : bool = actionChoiceData.get('targetConfirm', False)
    selectedTargets : set[CombatEntity] = actionChoiceData.get(targetKey, set())

    if not targetConfirm and len(opponents) == 1:
        targetConfirm = True
        selectedTargets = set([opponents[0]])
    
    instructionTitle = f"{actionName}"
    instructionContent = ""
    if len(selectedTargets) > 0:
        instructionContent = f"{changeString} distance from {', '.join([st.shortName for st in selectedTargets])}."
    else:
        instructionContent = "Select targets, then amount to move by."

    if not targetConfirm:
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
    return (instructionTitle, instructionContent)
async def submitActionCallbackFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView,
                                 handler : DiscordCombatInputHandler, action : CombatActions, targets : list[CombatEntity],
                                 amount : int = 0, skillData : SkillData | None = None):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)
    session.unseenCombatLog = ""
    view.pageData['sentLog'] = False

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

def partyDetailContent(session : GameSession, view : InterfaceView, playerTeam : bool):
    assert(session.currentDungeon is not None)
    assert(session.currentDungeon.currentCombatInterface is not None)
    combatInterface = session.currentDungeon.currentCombatInterface
    player = GLOBAL_STATE.accountDataMap[session.userId].currentCharacter

    targetTeam = combatInterface.getTeammates(player, False) if playerTeam else combatInterface.getOpponents(player, False)
    livingTeam = set(combatInterface.getTeammates(player, True) if playerTeam else combatInterface.getOpponents(player, True))
    defaultTarget = player if playerTeam else targetTeam[0]
    defaultTargetConfirmed = playerTeam
    
    focusEntity : CombatEntity = view.pageData.get(DETAIL_FOCUS, defaultTarget)

    targetButtons = []
    for target in targetTeam:
        buttonStyle = discord.ButtonStyle.secondary
        if target in livingTeam:
            buttonStyle = discord.ButtonStyle.blurple
            if not defaultTargetConfirmed:
                defaultTarget = target
                defaultTargetConfirmed = True

        targetButton = discord.ui.Button(label=target.shortName, style=buttonStyle, disabled=target==focusEntity)
        targetButton.callback = (lambda _trg: lambda interaction: updateDataCallbackFn(interaction, session, view, DETAIL_FOCUS, _trg))(target)

        if target == player:
            targetButtons.insert(0, targetButton)
        else:
            targetButtons.append(targetButton)
    [view.add_item(button) for button in targetButtons]

    classString = ""
    if isinstance(focusEntity, Player):
        classString = f" {enumName(focusEntity.currentPlayerClass)}"
    embed = discord.Embed(title=f"**{focusEntity.name}**: Level {focusEntity.level}{classString}", description=focusEntity.description)
    statusString = combatInterface.getEntityStatus(player, focusEntity)
    embed.add_field(name="Combat Status:", value=statusString, inline=False)

    buffString = combatInterface.getEntityBuffs(focusEntity)
    if len(buffString) > 0:
        embed.add_field(name="Ongoing Effects:", value=buffString, inline=False)
    
    return embed
COMBAT_PARTY_PAGE = InterfacePage("Party", discord.ButtonStyle.secondary, [],
                                 lambda session, view: partyDetailContent(session, view, True),
                                 lambda session: True, changePageCallback)
COMBAT_ENEMY_PAGE = InterfacePage("Enemies", discord.ButtonStyle.secondary, [],
                                 lambda session, view: partyDetailContent(session, view, False),
                                 lambda session: True, changePageCallback)

def dungeonEscapeFn(session : GameSession, view : InterfaceView):
    assert(session.currentDungeon is not None)

    embed = discord.Embed(title=f"Are you sure you want to leave?", description="Escaping will end this dungeon run; you will need to start from the beginning if you return.")

    confirmButton = discord.ui.Button(label="Leave Dungeon", style=discord.ButtonStyle.red)
    confirmButton.callback = lambda interaction: exitDungeonFn(interaction, session)
    view.add_item(confirmButton)

    return embed
async def exitDungeonFn(interaction : discord.Interaction, session : GameSession):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)
    await session.exitDungeon()
DUNGEON_LEAVE_PAGE = InterfacePage("Escape", discord.ButtonStyle.red, [],
                                   dungeonEscapeFn, lambda session: True, changePageCallback)

COMBAT_MENU = InterfaceMenu([COMBAT_MAIN_PAGE, COMBAT_PARTY_PAGE, COMBAT_ENEMY_PAGE, DUNGEON_LEAVE_PAGE])


def roomReadyFn(session : GameSession, view : InterfaceView):
    assert(session.currentDungeon is not None)
    player = GLOBAL_STATE.accountDataMap[session.userId].currentCharacter

    embed = discord.Embed(title=f"Prepare for Next Room",
                          description="You can change your stats, free skills, equipment, and positioning between rooms.\n" +
                          "Press \"I'm Ready\" when you're prepared.")
    if session.dungeonFailed:
        embed.title = "Party Defeated..."
        embed.description = "This dungeon allows you to retry fights; you can change your stats, free skills, equipment," + \
            " and positioning before trying again.\nPress \"Retry\" when you're prepared."

    dungeonHandler = session.currentDungeon.playerTeamHandlers[player]
    logger = session.currentDungeon.loggers[player]
    assert isinstance(dungeonHandler, DiscordDungeonInputHandler)
    if dungeonHandler.isReady:
        embed.description = "Waiting for teammates..."
    else:
        embed.add_field(name="__Combat Log__", value=_abridgeCombatLog(session.unseenCombatLog), inline=False)
        sentLog = view.pageData.get('sentLog', False)
        assert isinstance(logger, DiscordMessageCollector)
        if len(session.unseenCombatLog) > DISPLAY_LOG_THRESHOLD:
            logCatchupButton = discord.ui.Button(label="Expand Log", style=discord.ButtonStyle.blurple, row=3)
            logCatchupButton.callback = lambda interaction: expandLogFn(interaction, session, view, logger)
            view.add_item(logCatchupButton)

        logButton = discord.ui.Button(label="Get Full Fight Log", style=discord.ButtonStyle.blurple, disabled=sentLog, row=3)
        logButton.callback = lambda interaction: sendCombatLogFn(interaction, session, view, logger)
        view.add_item(logButton)

    disableReady = dungeonHandler.isReady
    if len(session.pendingItems) > 0:
        prevDesc = embed.description if embed.description is not None else ""
        embed.description = prevDesc + "\n*(Some equipment dropped that would take you past your inventory limit;" + \
            " handle these in the Equipment page before readying up.)*"
        disableReady = True
    confirmButton = discord.ui.Button(label="I'm Ready", style=discord.ButtonStyle.green, disabled=disableReady)
    if session.dungeonFailed:
        confirmButton.label="Retry"
    confirmButton.callback = lambda interaction: markReadyFn(interaction, session, dungeonHandler, logger)
    view.add_item(confirmButton)

    return embed
async def markReadyFn(interaction : discord.Interaction, session : GameSession, dungeonHandler : DiscordDungeonInputHandler,
                      logger : MessageCollector):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)
    logger.clearMessages()
    dungeonHandler.markReady()
    await session.currentView.refresh()
def pressedReady(session : GameSession):
    assert(session.currentDungeon is not None)
    player = GLOBAL_STATE.accountDataMap[session.userId].currentCharacter
    dungeonHandler = session.currentDungeon.playerTeamHandlers[player]
    assert isinstance(dungeonHandler, DiscordDungeonInputHandler)
    return dungeonHandler.isReady
BETWEEN_ROOM_READY_PAGE = InterfacePage("Ready", discord.ButtonStyle.green, [],
                                        roomReadyFn, lambda session: not pressedReady(session),
                                        changePageCallback)
BETWEEN_ROOM_LEAVE_PAGE = InterfacePage("Escape", discord.ButtonStyle.red, [],
                                        dungeonEscapeFn, lambda session: not pressedReady(session),
                                        changePageCallback)

BETWEEN_ROOM_STATS_SKILLS_PAGE = InterfacePage("Stats/Skills", discord.ButtonStyle.secondary,
                                               [CHARACTER_STATS_SUBPAGE, CHARACTER_SKILLS_SUBPAGE],
                                               None, lambda session: True, changePageCallback, statPointStyle)

def roomFormationFn(session : GameSession, view : InterfaceView):
    assert(session.currentDungeon is not None)
    player = GLOBAL_STATE.accountDataMap[session.userId].currentCharacter

    embed = discord.Embed(title=f"Starting Positions",
                          description=f"You can change the distance at which you start from enemies (default is {DEFAULT_STARTING_DISTANCE}), " +
                          "but doing so will often cause you to lose initiative. Coordinate with teammates to find a balance!")
    
    startingPositionStrings = []
    for partySession in session.getPartySessions():
        partyPlayer = partySession.getPlayer()
        assert partyPlayer is not None
        penaltyString = " (initiative penalty)" if partySession.defaultFormationDistance != DEFAULT_STARTING_DISTANCE else ""
        startingPositionStrings.append(f"**{partyPlayer.name}**: {partySession.defaultFormationDistance}{penaltyString}")
    startingPositionString = '\n'.join(startingPositionStrings)

    embed.add_field(name="__Starting Distances:__", value=startingPositionString)
    
    for dist in [1, 2, 3]:
        distButton = discord.ui.Button(label=f"Start Dist. {dist}", style=discord.ButtonStyle.blurple,
                                        disabled=session.defaultFormationDistance==dist)
        distButton.callback = (lambda _i: (lambda interaction: updateFormationFn(interaction, session, view, player, _i)))(dist)
        view.add_item(distButton)

    return embed
def playerLevelOneCheck(session : GameSession):
    player = GLOBAL_STATE.accountDataMap[session.userId].currentCharacter
    return player.level > 1
BETWEEN_ROOM_FORMATION_PAGE = InterfacePage("Formation", discord.ButtonStyle.secondary, [],
                                            roomFormationFn, playerLevelOneCheck, changePageCallback)


BETWEEN_ROOM_MENU = InterfaceMenu([BETWEEN_ROOM_READY_PAGE, BETWEEN_ROOM_STATS_SKILLS_PAGE,
                                   EQUIPMENT_PAGE, BETWEEN_ROOM_FORMATION_PAGE, BETWEEN_ROOM_LEAVE_PAGE])



def dungeonCompleteFn(session : GameSession, view : InterfaceView):
    assert(session.currentDungeon is not None)
    player = GLOBAL_STATE.accountDataMap[session.userId].currentCharacter
    embed = discord.Embed(title="", description="")
    
    if session.dungeonFailed:
        embed.title = "Dungeon Failed..."
    else:
        embed.title = "Dungeon Cleared!"
    embed.add_field(name="__Combat Log__", value=_abridgeCombatLog(session.unseenCombatLog), inline=False)
    if len(session.unseenCombatLog) > DISPLAY_LOG_THRESHOLD:
        logger = session.currentDungeon.loggers[player]
        logCatchupButton = discord.ui.Button(label="Expand Log", style=discord.ButtonStyle.blurple, row=4)
        logCatchupButton.callback = lambda interaction: expandLogFn(interaction, session, view, logger)
        view.add_item(logCatchupButton)

    confirmButton = discord.ui.Button(label="Exit Dungeon", style=discord.ButtonStyle.green)
    confirmButton.callback = lambda interaction: exitDungeonFn(interaction, session)
    view.add_item(confirmButton)

    sentLog = view.pageData.get('sentLog', False)
    logger = session.currentDungeon.loggers[player]
    assert isinstance(logger, DiscordMessageCollector)
    logButton = discord.ui.Button(label="Get Full Fight Log", style=discord.ButtonStyle.blurple, disabled=sentLog)
    logButton.callback = lambda interaction: sendCombatLogFn(interaction, session, view, logger)
    view.add_item(logButton)

    return embed
async def sendCombatLogFn(interaction : discord.Interaction, session : GameSession, view : InterfaceView, logger : DiscordMessageCollector):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)
    filterSettings = list(GLOBAL_STATE.accountDataMap[session.userId].enabledLogFilters)
    messages = logger.sendAllMessages(filterSettings, False)
    messageString = messages.getMessagesString(filterSettings, False)

    assert(session.currentMessage is not None)

    combatLogFile = f"{COMBAT_LOG_FILE_PREFIX}{session.userId}_{int(datetime.now().timestamp())}.txt"
    with open(combatLogFile, "w") as tmp:
        tmp.write(messageString)

    channel = session.currentMessage.channel
    mentionString = session.savedMention
    await channel.send(mentionString, file=discord.File(combatLogFile))

    os.remove(combatLogFile)
    view.pageData['sentLog'] = True
    await view.refresh()
DUNGEON_COMPLETE_PAGE = InterfacePage("Exit", discord.ButtonStyle.green, [],
                                      dungeonCompleteFn, lambda session: True,
                                      changePageCallback)
DUNGEON_COMPLETE_MENU = InterfaceMenu([DUNGEON_COMPLETE_PAGE])


#### Options
def optionsMainContent(session : GameSession, view : InterfaceView):
    embed = discord.Embed(title="Game Options",
                          description="This command gives a few settings you can change that affect all of your characters " + \
                            "(or it will, when I think of some).")
    embed.add_field(name="General Information",
                    value="idk what to put here yet, but if anything breaks reach out to Serp")
    return embed
OPTIONS_MAIN_PAGE = InterfacePage("Info", discord.ButtonStyle.secondary, [],
                                  optionsMainContent, lambda session: True, changePageCallback)

def optionsLogContent(session : GameSession, view : InterfaceView):
    embed = discord.Embed(title="Logging Settings",
                          description="Enable or disable certain parts of the Combat Log.")
    embed.add_field(name="",
                    value="Use the buttons to configure the types of lines that will be printed to your Combat Log in dungeons.")
    
    enabledFilters = GLOBAL_STATE.accountDataMap[session.userId].enabledLogFilters
    for messageType in TOGGLE_LOG_FILTER_DEFAULTS:
        filterOn = messageType in enabledFilters
        filterButton = discord.ui.Button()
        if filterOn:
            filterButton.label = f"'{enumName(messageType)}' is ON"
            filterButton.style = discord.ButtonStyle.green
        else:
            filterButton.label = f"'{enumName(messageType)}' is OFF"
            filterButton.style = discord.ButtonStyle.gray
        filterButton.callback = (lambda _fil: lambda interaction:
                                 toggleFilterFn(interaction, session, enabledFilters, _fil))(messageType)
        view.add_item(filterButton)
    
    return embed
async def toggleFilterFn(interaction : discord.Interaction, session : GameSession,
                         enabledFilterSet : set[MessageType], newFilter : MessageType):
    await interaction.response.defer()
    if interaction.user.id != session.userId:
        return await asyncio.sleep(0)
    if newFilter in enabledFilterSet:
        enabledFilterSet.remove(newFilter)
    else:
        enabledFilterSet.add(newFilter)
    await session.currentView.refresh()
OPTIONS_LOG_PAGE = InterfacePage("Combat Log Filters", discord.ButtonStyle.secondary, [],
                                  optionsLogContent, lambda session: True, changePageCallback)

OPTIONS_MENU = InterfaceMenu([OPTIONS_MAIN_PAGE, OPTIONS_LOG_PAGE])


#### Dungeon/Combat Interaction

class DiscordDungeonInputHandler(DungeonInputHandler):
    def __init__(self, player : Player, session : GameSession):
        super().__init__(player, DiscordCombatInputHandler)
        self.session = session
        self.readyFlag = asyncio.Event()
        self.disabled = False
        self.isReady = False

    def makeCombatInputController(self):
        return DiscordCombatInputHandler(self.player, self.session)
    
    def markReady(self):
        self.isReady = True
        self.readyFlag.set()
    
    def onPlayerLeaveDungeon(self):
        self.disabled = True
        self.readyFlag.set()
    
    def onDungeonComplete(self):
        if not self.disabled:
            asyncio.create_task(self.session.loadNewMenu(DUNGEON_COMPLETE_MENU))

    def onDungeonFail(self):
        self.session.dungeonFailed = True
        asyncio.create_task(self.session.loadNewMenu(DUNGEON_COMPLETE_MENU))
    
    """
        Promps the player to retry after a failed fight.
        Returns whether or not the retry is accepted.
    """
    async def waitDungeonRetryResponse(self, dungeonController : DungeonController):
        self.session.dungeonFailed = True
        await self.waitReady(dungeonController)
        return not self.disabled # disabled set to true if leaving dungeon
    
    """
        Waits for the player to be ready for the dungeon rooms.
        Allows free skills, equips, and formation positions to be changed.
    """
    async def waitReady(self, dungeonController : DungeonController):
        if self.disabled:
            return True

        self.isReady = False
        self.readyFlag.clear()
        await self.session.loadNewMenu(BETWEEN_ROOM_MENU)

        await self.readyFlag.wait()
        await self.session.currentView.refresh()

        if not self.disabled:
            asyncio.create_task(self.session.waitForCombatStart())
        return True
    
    """
        Picks up a new equip; if inventory is full, gives the player the option to
        drop something from their inventory. (Should give a confirmation prompt as well; maybe add a way to lock items later?)
    """
    async def getEquip(self, dungeonController : DungeonController, newEquip : Equipment):
        hadSpace = self.player.storeEquipItem(newEquip)
        if not hadSpace:
            self.session.pendingItems.append(newEquip)


class DiscordCombatInputHandler(CombatInputHandler):
    def __init__(self, player : Player, session : GameSession):
        super().__init__(player)
        self.session = session
        self.controller : CombatController | None = None
        self.actionFlag = asyncio.Event()
        self.disabled = False

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
    
    def onPlayerLeaveDungeon(self) -> None:
        self.disabled = True
        self.actionFlag.set()

    async def takeTurn(self, combatController : CombatController) -> None:
        if self.disabled:
            return
        
        if not self.session.dungeonLoaded.is_set():
            await self.session.dungeonLoaded.wait()

        self.session.currentView.pageData[ACTION_CHOICE] = None
        self.session.currentView.pageData[ACTION_CHOICE_DATA] = {}
        self.controller = combatController

        if self.session.currentParty is None:
            await self.session.currentView.refresh()
        else:
            await asyncio.gather(*[session.currentView.refresh() for session in self.session.currentParty.allSessions])

        self.actionFlag.clear()
        await self.actionFlag.wait()

        if not self.disabled:
            await self.session.currentView.refresh()
    
class DiscordMessageCollector(MessageCollector):
    def __init__(self, session : GameSession):
        super().__init__()
        self.session = session
        self.pendingMessages = {}
        
        self.defaultFilters = GLOBAL_STATE.accountDataMap[session.userId].enabledLogFilters

    def sendAllMessages(self, filters : list[MessageType] | None, includeTypes : bool) -> LogMessageCollection:
        if filters is None:
            filters = list(self.defaultFilters)

        result = super().sendAllMessages(filters, includeTypes)
        resultString = result.getMessagesString(filters, includeTypes)
        # self._updateViewLog(resultString)
        return result
    
    def sendNewestMessages(self, filters : list[MessageType] | None, includeTypes : bool) -> LogMessageCollection:
        if filters is None:
            filters = list(self.defaultFilters)

        result = super().sendNewestMessages(filters, includeTypes)
        resultString = result.getMessagesString(filters, includeTypes)
        if len(resultString) > 0:
            self._updateViewLog(resultString)
        return result
    
    def _updateViewLog(self, newLog : str):
        self.session.unseenCombatLog += '\n' + newLog if self.session.unseenCombatLog else newLog
