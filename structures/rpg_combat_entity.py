from __future__ import annotations
from typing import Callable

from gameData.rpg_item_data import makeBeginnerWeapon
from structures.rpg_combat_state import CombatController
from rpg_consts import *
from structures.rpg_classes_skills import PlayerClassData, SkillData, PassiveSkillData
from structures.rpg_items import Item, Equipment, Weapon

class CombatEntity(object):
    def __init__(self, name : str, level : int, aggroDecayFactor : float,
                 passiveSkills : list[SkillData], activeSkills : list[SkillData],
                 shortName : str = "", description = "", encounterMessage : str = "", defeatMessage : str = "") -> None:
        self.name = name
        self.shortName = shortName if len(shortName) > 0 else self.name
        self.level = level
        self.aggroDecayFactor = aggroDecayFactor
        self.baseStats : dict[BaseStats, int] = {}
        self.flatStatMod : dict[Stats, float] = {}
        self.multStatMod : dict[Stats, float] = {}
        self.description = description
        self.encounterMessage = encounterMessage
        self.defeatMessage = defeatMessage

        self.passiveBonusSkills : list[PassiveSkillData] = []

        self.availablePassiveSkills : list[SkillData] = passiveSkills
        self.availableActiveSkills : list[SkillData] = activeSkills

        self.basicAttackType : AttackType = DEFAULT_ATTACK_TYPE
        self.basicAttackAttribute : AttackAttribute = DEFAULT_ATTACK_ATTRIBUTE

    def __repr__(self) -> str:
        return f"<CombatEntity: {self.name}>"

    def getBaseStatString(self) -> str:
        return f"""HP: {self.baseStats[BaseStats.HP]}, MP: {self.baseStats[BaseStats.MP]}
ATK: {self.baseStats[BaseStats.ATK]}, DEF: {self.baseStats[BaseStats.DEF]}, MAG: {self.baseStats[BaseStats.MAG]}, RES: {self.baseStats[BaseStats.RES]}
ACC: {self.baseStats[BaseStats.ACC]}, AVO: {self.baseStats[BaseStats.AVO]}, SPD: {self.baseStats[BaseStats.SPD]}"""

    def getBaseStatValue(self, stat : BaseStats) -> int:
        return self.baseStats[stat]

    def getStatValueFloat(self, stat : Stats) -> float:
        base : float = 0
        if type(stat) is BaseStats:
            base = self.baseStats[stat]
        elif type(stat) is CombatStats:
            base = baseCombatStats[stat]
        else:
            assert(False)

        flatMod : float = self.flatStatMod.get(stat, 0)
        multMod : float = self.multStatMod.get(stat, 1)
        return (base + flatMod) * multMod

    def getStatValue(self, stat : Stats) -> int:
        return round(self.getStatValueFloat(stat))

class Player(CombatEntity):
    """Initializes the Player at level 1"""
    def __init__(self, name : str, playerClass : PlayerClassNames) -> None:
        super().__init__(name, 1, 0, [], [])

        self.playerExp : int = 0

        self.freeStatPoints : int = STAT_POINTS_PER_LEVEL
        self.statLevels : dict[BaseStats, int] = {baseStat : 0 for baseStat in BaseStats}

        self.classRanks : dict[PlayerClassNames, int] = {}
        self.classExp : dict[PlayerClassNames, int] = {}
        for classNameSet in [BasePlayerClassNames, AdvancedPlayerClassNames]:
            for className in classNameSet:
                self.classRanks[className] = 1
                self.classExp[className] = 0

        self.currentPlayerClass : PlayerClassNames = playerClass
        self.freeSkills : list[tuple[PlayerClassNames, int]] = []

        self.equipment : dict[EquipmentSlot, Equipment] = {}
        self.inventory : list[Equipment] = []
        self.wup : int = 0
        self.swup : int = 0

        self.milestones : set[Milestones] = set()

        self._updateBaseStats()
        self._updateAvailableSkills()

        self.weaponCache : dict[PlayerClassNames, Equipment] = {}
        for baseClass in BasePlayerClassNames:
            newWeapon = makeBeginnerWeapon(baseClass)
            self.inventory.append(newWeapon)
            if baseClass == self.currentPlayerClass:
                self.equipItem(newWeapon)

    def _updateBaseStats(self) -> None:
        for baseStat in BaseStats:
            base : int = baseStatValues_base[baseStat]
            level : int = self.statLevels[baseStat]
            increment : int = baseStatValues_perLevel[baseStat]
            self.baseStats[baseStat] = base + (level * increment)

    def _updateAvailableSkills(self) -> None:
        for passiveSkill in self.availablePassiveSkills:
            passiveSkill.disablePassiveBonuses(self)

        self.availableActiveSkills = []
        self.availablePassiveSkills = []

        allSkills = PlayerClassData.getSkillsForRank(self.currentPlayerClass, self.classRanks[self.currentPlayerClass])
        for freeSkillClass, freeSkillRank in self.freeSkills:
            freeSkill = PlayerClassData.getFreeSkillForRank(freeSkillClass, freeSkillRank)
            if freeSkill is not None:
                allSkills.append(freeSkill)
        for equip in self.equipment.values():
            allSkills += equip.currentTraitSkills

        for skillData in allSkills:
            if skillData.isActiveSkill:
                self.availableActiveSkills.append(skillData)
            else:
                skillData.enablePassiveBonuses(self)
                self.availablePassiveSkills.append(skillData)
    
    def getTotalStatString(self) -> str:
        statStrings = {}
        for stat in BaseStats:
            statStrings[stat] = f"**{stat.name}**: {self.getStatValue(stat)} ({self.statLevels[stat]} pts)"
        statString = f"{statStrings[BaseStats.HP]}  \\||  {statStrings[BaseStats.MP]}\n" + \
                     f"{statStrings[BaseStats.ATK]}  \\||  {statStrings[BaseStats.DEF]}  \\||  {statStrings[BaseStats.MAG]}  \\||  {statStrings[BaseStats.RES]}\n" + \
                     f"{statStrings[BaseStats.ACC]}  \\||  {statStrings[BaseStats.AVO]}  \\||  {statStrings[BaseStats.SPD]}"
        return statString

    """
        Increases the player's base stat levels once for each stat that appears in increasedStats, updating
        the base stat values accordingly.

        Stat levels cannot exceed the player's level, and stats will attempt to be increased in order
        until no more freeStatPoints remain.

        Returns a list containing stats once for each time their level was successfully increased.
    """
    def assignStatPoints(self, increasedStats : list[BaseStats]) -> list[BaseStats]:
        result : list[BaseStats] = []
        for increasedStat in increasedStats:
            if self.freeStatPoints <= 0:
                break

            if self.statLevels[increasedStat] >= self.level:
                continue

            self.statLevels[increasedStat] += 1
            result.append(increasedStat)
            self.freeStatPoints -= 1

        self._updateBaseStats()
        return result
    
    """
        Resets all stat points to 0.
    """
    def resetStatPoints(self):
        for stat in self.statLevels:
            self.freeStatPoints += self.statLevels[stat]
            self.statLevels[stat] = 0
        self._updateBaseStats()

    """
        Checks to see if the player's current class can equip a weapon.
    """
    def canEquipWeapon(self, newWeapon: Weapon) -> bool:
        permittedClasses = weaponTypeAttributeMap[newWeapon.weaponType].permittedClasses
        baseClasses = PlayerClassData.getBaseClasses(self.currentPlayerClass)
        return any([baseClass in permittedClasses for baseClass in baseClasses])
    
    """
        Puts on an item, replacing any item currently equipped in the same slot. Automatically updates
        stats accordingly, and returns an item if one was unequipped.
    """
    def equipItem(self, newEquip: Equipment) -> Equipment | None:
        equipSlot = newEquip.equipSlot
        oldEquip : Equipment | None = self.equipment.get(equipSlot, None)

        if oldEquip is not None:
            oldStatMap = oldEquip.getStatMap()
            for stat in oldStatMap:
                self.flatStatMod[stat] -= oldStatMap[stat]

        self.equipment[equipSlot] = newEquip
        newStatMap = newEquip.getStatMap()
        for stat in newStatMap:
            self.flatStatMod[stat] = self.flatStatMod.get(stat, 0) + newStatMap[stat]
        
        if equipSlot == EquipmentSlot.WEAPON:
            assert(isinstance(newEquip, Weapon))
            self.basicAttackType = weaponTypeAttributeMap[newEquip.weaponType].basicAttackType
            self.basicAttackAttribute = weaponTypeAttributeMap[newEquip.weaponType].basicAttackAttribute
            self.weaponCache[self.currentPlayerClass] = newEquip

        self._updateAvailableSkills()
        return oldEquip
    
    """
        As above, but does not equip a new item as a replacement.
    """
    def unequipItem(self, equipSlot : EquipmentSlot) -> Equipment | None:
        oldEquip : Equipment | None = self.equipment.pop(equipSlot, None)
        if oldEquip is not None:
            oldStatMap = oldEquip.getStatMap()
            for stat in oldStatMap:
                self.flatStatMod[stat] -= oldStatMap[stat]
        
        if equipSlot == EquipmentSlot.WEAPON:
            self.basicAttackType = DEFAULT_ATTACK_TYPE
            self.basicAttackAttribute = DEFAULT_ATTACK_ATTRIBUTE

        self._updateAvailableSkills()
        return oldEquip
    
    """
        Drops a piece of equipment, unequipping it if necessary.
    """
    def dropItem(self, equip : Equipment):
        if self.equipment.get(equip.equipSlot, None) == equip:
            self.unequipItem(equip.equipSlot)
        self.inventory.remove(equip)
    
    """
        Adds a class's free skill, as specified by the skill's class and rank.
        A player may have up to 4 active free skills for classes they meet the rank requirements for,
        and they may not choose a free skill if they already have that class's skills.
        Returns true if the free skill was successfully added.
    """
    def addFreeSkill(self, freeSkillClass : PlayerClassNames, freeSkillRank : int) -> bool:
        if len(self.freeSkills) >= MAX_FREE_SKILLS or (freeSkillClass, freeSkillRank) in self.freeSkills:
            return False
        
        currentSkillClasses = PlayerClassData.getAllClassDependencies(self.currentPlayerClass)
        if freeSkillClass in currentSkillClasses or self.classRanks[freeSkillClass] < freeSkillRank:
            return False
        
        freeSkill = PlayerClassData.getFreeSkillForRank(freeSkillClass, freeSkillRank)
        if freeSkill is None:
            return False
        
        self.freeSkills.append((freeSkillClass, freeSkillRank))
        self._updateAvailableSkills()
        return True
    
    """
        Removes free skills in the same format. Returns whether or not it was present before being removed.
    """
    def removeFreeSkill(self, freeSkillClass : PlayerClassNames, freeSkillRank : int) -> bool:
        if (freeSkillClass, freeSkillRank) in self.freeSkills:
            self.freeSkills.remove((freeSkillClass, freeSkillRank))
            self._updateAvailableSkills()
            return True
        return False
    
    """
        Checks to see if player meets the requirements for a class.
    """
    def classRequirementsMet(self, newClass : PlayerClassNames) -> bool:
        classData = PlayerClassData.PLAYER_CLASS_DATA_MAP[newClass]
        for requiredClass in classData.classRequirements:
            requiredRank = MAX_BASE_CLASS_RANK if isinstance(requiredClass, BasePlayerClassNames) else MAX_ADVANCED_CLASS_RANK
            if self.classRanks[requiredClass] < requiredRank:
                return False
        return True
    
    """
        Attempts to change to the given class. 
        Returns true if successful (meeting requirements). If so, unequips invalid
        free skills, and (attempts to) switch weapons if the current one cannot be equipped.
    """
    def changeClass(self, newClass : PlayerClassNames) -> bool:
        if not self.classRequirementsMet(newClass):
            return False
            
        self.currentPlayerClass = newClass
        removedFreeSkills = []
        for skillClass, skillRank in self.freeSkills:
            if skillClass in PlayerClassData.getAllClassDependencies(self.currentPlayerClass):
                removedFreeSkills.append((skillClass, skillRank))
        [self.removeFreeSkill(skillClass, skillRank) for (skillClass, skillRank) in removedFreeSkills]

        if EquipmentSlot.WEAPON in self.equipment:
            weapon = self.equipment[EquipmentSlot.WEAPON]
            assert isinstance(weapon, Weapon)
            if self.canEquipWeapon(weapon):
                self.weaponCache[self.currentPlayerClass] = weapon
            elif self.currentPlayerClass in self.weaponCache:
                self.equipItem(self.weaponCache[self.currentPlayerClass])
            else:
                self.unequipItem(EquipmentSlot.WEAPON)

        if EquipmentSlot.WEAPON not in self.equipment:
            for item in self.inventory:
                if isinstance(item, Weapon) and self.canEquipWeapon(item):
                    self.equipItem(item)
                    break

        self._updateAvailableSkills()
        return True
    
    def getExpToNextLevel(self) -> int | None:
        if self.level < MAX_PLAYER_LEVEL:
            return EXP_TO_NEXT_PLAYER_LEVEL[self.level - 1]
    
    def getExpToNextRank(self) -> int | None:
        classData = PlayerClassData.PLAYER_CLASS_DATA_MAP[self.currentPlayerClass]
        maxRank = MAX_BASE_CLASS_RANK if classData.isBaseClass else MAX_ADVANCED_CLASS_RANK
        if self.classRanks[self.currentPlayerClass] < maxRank:
            nextRankExpList = EXP_TO_NEXT_BASE_CLASS_RANK if classData.isBaseClass else EXP_TO_NEXT_ADVANCED_CLASS_RANK
            return nextRankExpList[self.classRanks[self.currentPlayerClass] - 1]
    
    """
        Internal rank up; returns True as long as not already at max rank (for current class)
    """
    def _rankUp(self) -> bool:
        classData = PlayerClassData.PLAYER_CLASS_DATA_MAP[self.currentPlayerClass]
        maxRank = MAX_BASE_CLASS_RANK if classData.isBaseClass else MAX_ADVANCED_CLASS_RANK
        expToNextRank = self.getExpToNextRank()
        if expToNextRank is not None:
            self.classExp[self.currentPlayerClass] -= expToNextRank

            self.classRanks[self.currentPlayerClass] += 1
            self._updateAvailableSkills()

            if self.classRanks[self.currentPlayerClass] >= maxRank:
                self.classExp[self.currentPlayerClass] = 0
            return True
        return False
    
    """
        Internal level up; returns True as long as not already at max level
    """
    def _levelUp(self) -> bool:
        expToNextLevel = self.getExpToNextLevel()
        if expToNextLevel is not None:
            self.playerExp -= expToNextLevel
            self.level += 1
            self.freeStatPoints += STAT_POINTS_PER_LEVEL

            if self.level >= MAX_PLAYER_LEVEL:
                self.playerExp = 0
            return True
        return False
    
    """
        Gains EXP for both current class and player level; performs any appropriate level ups.
        Returns a tuple indicating if the player leveled up, then if the class did.
    """
    def gainExp(self, expAmount : int) -> tuple[bool, bool]:
        levelUp = False
        rankUp = False

        if self.level < MAX_PLAYER_LEVEL:
            self.playerExp += expAmount
            expToNextLevel = self.getExpToNextLevel()
            while expToNextLevel is not None and self.playerExp >= expToNextLevel:
                levelUp = self._levelUp()
                expToNextLevel = self.getExpToNextLevel()

        classData = PlayerClassData.PLAYER_CLASS_DATA_MAP[self.currentPlayerClass]
        maxRank = MAX_BASE_CLASS_RANK if classData.isBaseClass else MAX_ADVANCED_CLASS_RANK
        classRank = self.classRanks[self.currentPlayerClass]
        if classRank < maxRank:
            self.classExp[self.currentPlayerClass] += expAmount
            nextRankExp = self.getExpToNextRank()
            while nextRankExp is not None and self.classExp[self.currentPlayerClass] >= nextRankExp:
                rankUp = self._rankUp()
                nextRankExp = self.getExpToNextRank()

        return (levelUp, rankUp)
    
    """
        Tries to put an item into inventory if there is space; returns true iff successful
    """
    def storeEquipItem(self, equip : Equipment) -> bool:
        if len(self.inventory) < MAX_INVENTORY:
            self.inventory.append(equip)
            return True
        return False
    

class Enemy(CombatEntity):
    def __init__(self, name : str, shortName : str, description : str, level : int, baseStats : dict[BaseStats, int],
                 bonusFlatStats : dict[Stats, float], bonusMultStats : dict[Stats, float], aggroDecayFactor : float,
                 passiveSkills : list[SkillData], activeSkills : list[SkillData],
                 encounterMessage : str, defeatMessage : str, ai : EnemyAI,
                 rewardFn : Callable[[CombatController, CombatEntity], EnemyReward]):
        super().__init__(name, level, aggroDecayFactor, passiveSkills, activeSkills,
                         shortName, description, encounterMessage, defeatMessage)
        self.baseStats = baseStats
        self.flatStatMod = bonusFlatStats
        self.multStatMod = bonusMultStats
        self.ai = ai
        self.rewardFn = rewardFn

    def getReward(self, combatController : CombatController, player : CombatEntity) -> EnemyReward:
        return self.rewardFn(combatController, player)
        
class EnemyAI(object):
    def __init__(self, data : dict, decisionFn : Callable[[CombatController, CombatEntity, dict], EnemyAIAction]):
        self.data = data
        self.decisionFn = decisionFn
    
    def chooseAction(self, combatController : CombatController, enemy : CombatEntity) -> EnemyAIAction:
        return self.decisionFn(combatController, enemy, self.data)
        
class EnemyAIAction(object):
    def __init__(self, action : CombatActions, skillIndex : int | None, targetIndices : list[int],
                 actionParameter : int | None, skillSelector : str | None):
        self.action = action
        self.skillIndex = skillIndex
        self.targetIndices = targetIndices
        self.actionParameter = actionParameter
        self.skillSelector = skillSelector

class EnemyReward(object):
    def __init__(self, exp : int, wup : int, swup : int, equip : Equipment | None):
        self.exp = exp
        self.wup = wup
        self.swup = swup
        self.equip = equip