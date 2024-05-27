from __future__ import annotations
from typing import Callable, TypeAlias, Protocol
from functools import reduce

from rpg_consts import *
from rpg_combat_entity import *
from rpg_combat_state import *

### Classes

class PlayerClassData(object):
    def __init__(self, className : PlayerClassNames, classRequirements : list[PlayerClassNames]) -> None:
        self.className : PlayerClassNames = className
        self.isBaseClass : bool = len(classRequirements) == 0
        self.classRequirements : list[PlayerClassNames] = classRequirements

        self.rankSkills : dict[int, SkillData] = {}

    """ Provides a list of all of this class's skills, up to the given rank. """
    def getSkillsForRank(self, rank : int) -> list[SkillData]:
        results : list[SkillData] = []

        maxRank : int = MAX_BASE_CLASS_RANK if self.isBaseClass else MAX_ADVANCED_CLASS_RANK
        for i in range(1, min(maxRank, rank) + 1):
            if i in self.rankSkills:
                results.append(self.rankSkills[i])

        return results

classDataList = [
    PlayerClassData(BasePlayerClassNames.WARRIOR, []),
    PlayerClassData(BasePlayerClassNames.RANGER, []),
    PlayerClassData(BasePlayerClassNames.ROGUE, []),
    PlayerClassData(BasePlayerClassNames.MAGE, []),
    PlayerClassData(AdvancedPlayerClassNames.MERCENARY, [BasePlayerClassNames.WARRIOR]),
    PlayerClassData(AdvancedPlayerClassNames.KNIGHT, [BasePlayerClassNames.WARRIOR]),
    PlayerClassData(AdvancedPlayerClassNames.SNIPER, [BasePlayerClassNames.RANGER]),
    PlayerClassData(AdvancedPlayerClassNames.HUNTER, [BasePlayerClassNames.RANGER]),
    PlayerClassData(AdvancedPlayerClassNames.ASSASSIN, [BasePlayerClassNames.ROGUE]),
    PlayerClassData(AdvancedPlayerClassNames.ACROBAT, [BasePlayerClassNames.ROGUE]),
    PlayerClassData(AdvancedPlayerClassNames.WIZARD, [BasePlayerClassNames.MAGE]),
    PlayerClassData(AdvancedPlayerClassNames.SAINT, [BasePlayerClassNames.MAGE])
]
PLAYER_CLASS_DATA_MAP : dict[PlayerClassNames, PlayerClassData] = {classData.className: classData for classData in classDataList}


### Skills

class SkillData(object):
    def __init__(self, skillName : str, playerClass : PlayerClassNames, rank : int,
            isActiveSkill : bool, isFreeSkill : bool, description : str,
            mpCost : int | None, actionTime : float | None, causesAttack : bool, skillEffects : list[SkillEffect]) -> None:
        self.skillName : str = skillName
        self.playerClass : PlayerClassNames = playerClass
        self.rank : int = rank
        self.isActiveSkill : bool = isActiveSkill
        self.isFreeSkill : bool = isFreeSkill
        self.description : str = description
        self.mpCost : int | None = mpCost if isActiveSkill else None
        self.actionTime : float | None = actionTime if isActiveSkill else None
        self.causesAttack : bool = causesAttack
        self.skillEffects : list[SkillEffect] = skillEffects[:]

        self.registerSkill(PLAYER_CLASS_DATA_MAP)

    """ Associates this skill with the appropriate ClassData; expected to be called on startup """
    def registerSkill(self, playerClassDataMap : dict[PlayerClassNames, PlayerClassData]) -> None:
        assert(playerClassDataMap[self.playerClass].rankSkills.get(self.rank, None) is None)
        playerClassDataMap[self.playerClass].rankSkills[self.rank] = self

    def enablePassiveBonuses(self, entity : CombatEntity) -> None:
        pass

    def disablePassiveBonuses(self, entity : CombatEntity) -> None:
        pass

    def getAllEffectFunctions(self) -> list[EffectFunction]:
        return reduce(lambda a, b: a+b, list(map(lambda skillEffect : skillEffect.effectFunctions, self.skillEffects)))

class PassiveSkillData(SkillData):
    def __init__(self, skillName : str, playerClass : PlayerClassNames, rank : int, isFreeSkill : bool, description : str, 
            flatStatBonuses : dict[Stats, float], multStatBonuses : dict[Stats, float], skillEffects : list[SkillEffect]):
        super().__init__(skillName, playerClass, rank, False, isFreeSkill, description, None, None, False, skillEffects)

        self.flatStatBonuses = flatStatBonuses.copy()
        self.multStatBonuses = multStatBonuses.copy()

    def enablePassiveBonuses(self, entity : CombatEntity) -> None:
        if self in entity.passiveBonusSkills:
            return

        for stat in self.flatStatBonuses:
            entity.flatStatMod[stat] = entity.flatStatMod.get(stat, 0) + self.flatStatBonuses[stat]
        for stat in self.multStatBonuses:
            entity.multStatMod[stat] = entity.multStatMod.get(stat, 1) * self.multStatBonuses[stat]

        entity.passiveBonusSkills.append(self)

    def disablePassiveBonuses(self, entity : CombatEntity) -> None:
        if self not in entity.passiveBonusSkills:
            return

        for stat in self.flatStatBonuses:
            entity.flatStatMod[stat] -= self.flatStatBonuses[stat]
        for stat in self.multStatBonuses:
            entity.multStatMod[stat] /= self.multStatBonuses[stat]

        entity.passiveBonusSkills.remove(self)

class AttackSkillData(SkillData):
    def __init__(self, skillName : str, playerClass : PlayerClassNames, rank : int, isFreeSkill : bool, mpCost : int, description : str,
            isPhysical : bool, attackStatMultiplier : float, actionTime : float, skillEffects : list[SkillEffect]):
        super().__init__(skillName, playerClass, rank, True, isFreeSkill, description, mpCost, actionTime, True, skillEffects)

        self.isPhysical = isPhysical
        self.attackStatMultiplier = attackStatMultiplier

        attackingStat = BaseStats.ATK if isPhysical else BaseStats.MAG
        basicAttackSkillEffects = SkillEffect([
            EFBeforeNextAttack({}, {attackingStat : attackStatMultiplier}, None, None)
            # EFAfterNextAttack(lambda _1, _2, _3, _4, result: result.setActionTime(actionTime))
        ], 0)
        self.skillEffects.append(basicAttackSkillEffects)


class SkillEffect(object):
    def __init__(self, effectFunctions : list[EffectFunction], effectDuration : int | None):
        self.effectFunctions : list[EffectFunction] = effectFunctions[:]
        self.effectDuration : int | None = effectDuration

class EffectFunction(object):
    def __init__(self, effectTiming : EffectTimings):
        self.effectTiming : EffectTimings = effectTiming

"""An immediate effect upon using an active skill"""
class EFImmediate(EffectFunction):
    def __init__(self, func : Callable[[CombatController, CombatEntity, CombatEntity, EffectFunctionResult], None]):
        super().__init__(EffectTimings.IMMEDIATE)
        self.func : Callable[[CombatController, CombatEntity, CombatEntity, EffectFunctionResult], None] = func

    def applyEffect(self, controller : CombatController, user : CombatEntity, target : CombatEntity) -> EffectFunctionResult:
        result = EffectFunctionResult()
        self.func(controller, user, target, result)
        return result

"""(Usually) a temporary bonus before performing the next attack."""
class EFBeforeNextAttack(EffectFunction):
    def __init__(self, flatStatBonuses : dict[Stats, float], multStatBonuses : dict[Stats, float],
            applyFunc : None | Callable[[CombatController, CombatEntity, CombatEntity], None],
            revertFunc : None | Callable[[CombatController, CombatEntity, CombatEntity, EffectFunctionResult], None]):
        super().__init__(EffectTimings.BEFORE_ATTACK)
        self.flatStatBonuses : dict[Stats, float] = flatStatBonuses
        self.multStatBonuses : dict[Stats, float] = multStatBonuses
        self.applyFunc : None | Callable[[CombatController, CombatEntity, CombatEntity], None] = applyFunc
        self.revertFunc : None | Callable[[CombatController, CombatEntity, CombatEntity, EffectFunctionResult], None] = revertFunc


    def applyEffect(self, controller : CombatController, user : CombatEntity, target : CombatEntity) -> EffectFunctionResult:
        controller.applyFlatStatBonuses(user, self.flatStatBonuses)
        controller.applyMultStatBonuses(user, self.multStatBonuses)

        if self.applyFunc is not None:
            self.applyFunc(controller, user, target)
        revertEffect : SkillEffect = SkillEffect([EFBeforeNextAttack_Revert(self.flatStatBonuses, self.multStatBonuses, self.revertFunc)], 0)
        controller.addSkillEffect(user, revertEffect)

        return EffectFunctionResult()

class EFBeforeNextAttack_Revert(EffectFunction):
    def __init__(self, flatStatBonuses : dict[Stats, float], multStatBonuses : dict[Stats, float],
            revertFunc : None | Callable[[CombatController, CombatEntity, CombatEntity, EffectFunctionResult], None]):
        super().__init__(EffectTimings.AFTER_ATTACK)
        self.flatStatBonuses : dict[Stats, float] = flatStatBonuses
        self.multStatBonuses : dict[Stats, float] = multStatBonuses
        self.revertFunc : None | Callable[[CombatController, CombatEntity, CombatEntity, EffectFunctionResult], None] = revertFunc

    def applyEffect(self, controller : CombatController, user : CombatEntity, target : CombatEntity) -> EffectFunctionResult:
        controller.revertFlatStatBonuses(user, self.flatStatBonuses)
        controller.revertMultStatBonuses(user, self.multStatBonuses)

        result = EffectFunctionResult()
        if self.revertFunc is not None:
            self.revertFunc(controller, user, target, result)
        return result

"""A reaction to the results of the next attack."""
class EFAfterNextAttack(EffectFunction):
    def __init__(self, func : Callable[[CombatController, CombatEntity, CombatEntity, AttackResultInfo, EffectFunctionResult], None]):
        super().__init__(EffectTimings.AFTER_ATTACK)
        self.func : Callable[[CombatController, CombatEntity, CombatEntity, AttackResultInfo, EffectFunctionResult], None] = func

    def applyEffect(self, controller : CombatController, user : CombatEntity, target : CombatEntity,
            attackResultInfo : AttackResultInfo) -> EffectFunctionResult:
        result = EffectFunctionResult()
        self.func(controller, user, target, attackResultInfo, result)
        return result

class EffectFunctionResult(object):
    def __init__(self, bonusAttackData : AttackSkillData | None = None, actionTime : float | None = None, actionTimeMult : float | None = None):
        self.bonusAttackData = bonusAttackData
        self.actionTime = actionTime
        self.actionTimeMult = actionTimeMult

    def setBonusAttackData(self, bonusAttackData : AttackSkillData):
        self.bonusAttackData = bonusAttackData

    def setActionTime(self, actionTime: float):
        self.actionTime = actionTime

    def setActionTimeMult(self, actionTimeMult: float):
        self.actionTimeMult = actionTimeMult

# Should move these eventually
PassiveSkillData("Warrior's Resolution", BasePlayerClassNames.WARRIOR, 1, False,
    "Increases HP by 100, ATK by 10, and DEF by 5.",
    {BaseStats.HP: 100, BaseStats.ATK: 10, BaseStats.DEF: 5}, {}, [])

AttackSkillData("Great Swing", BasePlayerClassNames.WARRIOR, 2, False, 20,
    "Attack with 1.5x ATK.",
    True, 1.5, DEFAULT_ATTACK_TIMER_USAGE, [])

PassiveSkillData("Rogue's Instinct", BasePlayerClassNames.ROGUE, 1, False,
    "Increases AVO by 25, SPD by 10, and ATK by 5.",
    {BaseStats.AVO: 25, BaseStats.SPD: 10, BaseStats.ATK: 5}, {}, [])

AttackSkillData("Swift Strike", BasePlayerClassNames.ROGUE, 2, False, 10,
    "Attack with 0.7x ATK, but a reduced time until next action.",
    True, 0.7, DEFAULT_ATTACK_TIMER_USAGE / 2, [])

