from __future__ import annotations

from rpg_consts import *
from rpg_classes_skills import PlayerClassData, SkillData, PassiveSkillData
from rpg_items import Item, Equipment, Weapon

class CombatEntity(object):
    def __init__(self, name : str, passiveSkills : list[SkillData], activeSkills : list[SkillData]) -> None:
        self.name = name
        self.baseStats : dict[BaseStats, int] = {}
        self.flatStatMod : dict[Stats, float] = {}
        self.multStatMod : dict[Stats, float] = {}

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
        super().__init__(name, [], [])

        self.playerLevel : int = 1
        self.playerExp : int = 0

        self.freeStatPoints : int = 4
        self.statLevels : dict[BaseStats, int] = {baseStat : 0 for baseStat in BaseStats}

        self.classRanks : dict[PlayerClassNames, int] = {}
        self.classExp : dict[PlayerClassNames, int] = {}
        for classNameSet in [BasePlayerClassNames, AdvancedPlayerClassNames]:
            for className in classNameSet:
                self.classRanks[className] = 1
                self.classExp[className] = 0

        self.currentPlayerClass : PlayerClassNames = playerClass

        self.equipment : dict[EquipmentSlot, Equipment] = {}

        self._updateBaseStats()
        self._updateAvailableSkills()

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

        for skillData in PlayerClassData.getSkillsForRank(self.currentPlayerClass, self.classRanks[self.currentPlayerClass]):
            if skillData.isActiveSkill:
                self.availableActiveSkills.append(skillData)
            else:
                skillData.enablePassiveBonuses(self)
                self.availablePassiveSkills.append(skillData)

        for equip in self.equipment.values():
            for traitSkill in equip.currentTraitSkills:
                traitSkill.enablePassiveBonuses(self)
                self.availablePassiveSkills.append(traitSkill)


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

            if self.statLevels[increasedStat] >= self.playerLevel:
                continue

            self.statLevels[increasedStat] += 1
            result.append(increasedStat)
            self.freeStatPoints -= 1

        self._updateBaseStats()
        return result
    
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

        self._updateAvailableSkills()
        return oldEquip
    """
        As above, but does not equip a new item as a replacement.
    """
    def unequipItem(self, equipSlot : EquipmentSlot) -> Equipment | None:
        oldEquip : Equipment | None = self.equipment.get(equipSlot, None)
        if oldEquip is not None:
            oldStatMap = oldEquip.getStatMap()
            for stat in oldStatMap:
                self.flatStatMod[stat] -= oldStatMap[stat]
        
        if equipSlot == EquipmentSlot.WEAPON:
            self.basicAttackType = DEFAULT_ATTACK_TYPE
            self.basicAttackAttribute = DEFAULT_ATTACK_ATTRIBUTE

        self._updateAvailableSkills()
        return oldEquip