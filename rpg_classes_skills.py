from __future__ import annotations
from functools import reduce
from typing import Callable, TYPE_CHECKING

from rpg_consts import *

if TYPE_CHECKING:
    from rpg_combat_entity import CombatEntity
    from rpg_combat_state import CombatController, AttackResultInfo

### Classes

class PlayerClassData(object):
    PLAYER_CLASS_DATA_MAP : dict[PlayerClassNames, PlayerClassData] = {}

    def __init__(self, className : PlayerClassNames, classRequirements : list[PlayerClassNames]) -> None:
        self.className : PlayerClassNames = className
        self.isBaseClass : bool = len(classRequirements) == 0
        self.classRequirements : list[PlayerClassNames] = classRequirements

        self.rankSkills : dict[int, SkillData] = {}

        PlayerClassData.PLAYER_CLASS_DATA_MAP[self.className] = self

    """ Adds a skill for the given rank of a given class. Returns true if successful (i.e. no overlap)."""
    @staticmethod
    def registerSkill(className : PlayerClassNames, rank : int, skillData : SkillData) -> bool:
        classData : PlayerClassData = PlayerClassData.PLAYER_CLASS_DATA_MAP[className]
        if classData.rankSkills.get(rank, None) is None:
            classData.rankSkills[rank] = skillData
            return True
        return False

    """
        Provides a list of all of this class's skills, up to the given rank.
        Also includes all skills for required classes.
    """
    @staticmethod
    def getSkillsForRank(className : PlayerClassNames, rank : int, _all : bool = False) -> list[SkillData]:
        classData : PlayerClassData = PlayerClassData.PLAYER_CLASS_DATA_MAP[className]
        results : list[SkillData] = []

        for requiredClass in classData.classRequirements:
            results += PlayerClassData.getSkillsForRank(requiredClass, 9, True)

        maxRank : int = MAX_BASE_CLASS_RANK if classData.isBaseClass else MAX_ADVANCED_CLASS_RANK
        if _all:
            rank = maxRank
        for i in range(1, min(maxRank, rank) + 1):
            if i in classData.rankSkills:
                results.append(classData.rankSkills[i])

        return results

    """ Gets the free skill for a specific rank. Returns None if it is not a free skill. """
    @staticmethod
    def getFreeSkillForRank(className : PlayerClassNames, rank : int) -> SkillData | None:
        classData : PlayerClassData = PlayerClassData.PLAYER_CLASS_DATA_MAP[className]
        if rank in classData.rankSkills:
            rankSkill = classData.rankSkills[rank]
            if rankSkill.isFreeSkill:
                return rankSkill
        return None
    
    """ Gets the base classes a class requires (indicating which weapons it can use, for instance). """
    @staticmethod
    def getBaseClasses(className : PlayerClassNames) -> list[BasePlayerClassNames]:
        classData : PlayerClassData = PlayerClassData.PLAYER_CLASS_DATA_MAP[className]
        if classData.isBaseClass:
            assert(isinstance(classData.className, BasePlayerClassNames))
            return [classData.className]
        else:
            result = []
            for requiredClass in classData.classRequirements:
                result += PlayerClassData.getBaseClasses(requiredClass)
            return result
    
    """ Gets all classes a class depends on (including itself), rather than just the base classes. """
    @staticmethod
    def getAllClassDependencies(className : PlayerClassNames) -> list[PlayerClassNames]:
        classData : PlayerClassData = PlayerClassData.PLAYER_CLASS_DATA_MAP[className]
        result = [className]
        for requiredClass in classData.classRequirements:
            result += PlayerClassData.getAllClassDependencies(requiredClass)
        return result


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

### Skills

class SkillData(object):
    def __init__(self, skillName : str, playerClass : PlayerClassNames, rank : int,
            isActiveSkill : bool, isFreeSkill : bool, description : str,
            mpCost : int | None, actionTime : float | None, causesAttack : bool, skillEffects : list[SkillEffect],
            expectedTargets : int | None, attackTargetIndex : int, targetOpponents : bool, register : bool = True) -> None:
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
        self.expectedTargets : int | None = expectedTargets
        self.attackTargetIndex : int = attackTargetIndex
        self.targetOpponents : bool = targetOpponents

        if register:
            self.registerSkill()

    """ Associates this skill with the appropriate ClassData; expected to be called on startup """
    def registerSkill(self) -> None:
        assert(PlayerClassData.registerSkill(self.playerClass, self.rank, self))

    def enablePassiveBonuses(self, entity : CombatEntity) -> None:
        pass

    def disablePassiveBonuses(self, entity : CombatEntity) -> None:
        pass

    def getAllEffectFunctions(self) -> list[EffectFunction]:
        return reduce(lambda a, b: a+b, list(map(lambda skillEffect : skillEffect.effectFunctions, self.skillEffects)), [])

class PassiveSkillData(SkillData):
    def __init__(self, skillName : str, playerClass : PlayerClassNames, rank : int, isFreeSkill : bool, description : str, 
            flatStatBonuses : dict[Stats, float], multStatBonuses : dict[Stats, float], skillEffects : list[SkillEffect], register : bool = True):
        super().__init__(skillName, playerClass, rank, False, isFreeSkill, description, None, None, False, skillEffects,
                         None, 0, True, register)

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
            isPhysical : bool, attackType : AttackType | None, attackStatMultiplier : float, actionTime : float, skillEffects : list[SkillEffect],
            register : bool = True):
        super().__init__(skillName, playerClass, rank, True, isFreeSkill, description, mpCost, actionTime, True, skillEffects,
                         1, 0, True, register)

        self.isPhysical = isPhysical
        self.attackType = attackType
        self.attackStatMultiplier = attackStatMultiplier

        attackingStat = BaseStats.ATK if isPhysical else BaseStats.MAG
        basicAttackSkillEffects = SkillEffect([
            EFBeforeNextAttack({}, {attackingStat : attackStatMultiplier}, None, None)
            # EFAfterNextAttack(lambda _1, _2, _3, _4, result: result.setActionTime(actionTime))
        ], 0)
        self.skillEffects.append(basicAttackSkillEffects)

class ActiveBuffSkillData(SkillData):
    def __init__(self, skillName : str, playerClass : PlayerClassNames, rank : int, isFreeSkill : bool, mpCost : int, description : str,
            actionTime : float, flatStatBonuses : dict[Stats, float], multStatBonuses : dict[Stats, float], skillEffects : list[SkillEffect],
            expectedTargets : int | None, attackTargetIndex : int, targetOpponents : bool, register : bool = True):
        super().__init__(skillName, playerClass, rank, True, isFreeSkill, description, mpCost, actionTime, False, skillEffects,
                         expectedTargets, attackTargetIndex, targetOpponents, register)

        self.flatStatBonuses : dict[Stats, float] = flatStatBonuses
        self.multStatBonuses : dict[Stats, float] = multStatBonuses

class ActiveToggleSkillData(ActiveBuffSkillData):
    def __init__(self, skillName : str, playerClass : PlayerClassNames, rank : int, isFreeSkill : bool, mpCost : int, description : str,
            actionTime : float, flatStatBonuses : dict[Stats, float], multStatBonuses : dict[Stats, float], skillEffects : list[SkillEffect],
            expectedTargets : int | None, attackTargetIndex : int, targetOpponents : bool, register : bool = True):
        super().__init__(skillName, playerClass, rank, isFreeSkill, mpCost, description, actionTime, flatStatBonuses,
                         multStatBonuses, skillEffects, expectedTargets, attackTargetIndex, targetOpponents, register)

class CounterSkillData(AttackSkillData):
    def __init__(self, isPhysical : bool, attackType : AttackType | None, attackStatMultiplier : float, skillEffects : list[SkillEffect]):
        super().__init__("", BasePlayerClassNames.WARRIOR, 0, False, 0, "",
            isPhysical, attackType, attackStatMultiplier, 0, skillEffects, False)
        
class PrepareParrySkillData(SkillData):
    def __init__(self, skillName : str, playerClass : PlayerClassNames, rank : int, isFreeSkill : bool, mpCost : int, description : str,
            actionTime : float, parryType : AttackType, parryEffectFunctions : list[EFOnParry], register : bool = True):
        fullParryEffect = SkillEffect([ef for ef in parryEffectFunctions], None)
        fullParryEffect.effectFunctions.append(EFImmediate(lambda controller, user, _1, result: (
            controller.combatStateMap[user].setParryType(parryType, fullParryEffect)
        )))
        super().__init__(skillName, playerClass, rank, True, isFreeSkill, description, mpCost, actionTime, False,
                         [fullParryEffect], 0, 0, True, register)
        
class ActiveSkillDataSelector(SkillData):
    def __init__(self, skillName : str, playerClass : PlayerClassNames, rank : int, isFreeSkill : bool, mpCost : int, description : str,
            actionTime : float, expectedTargets : int | None, targetOpponents : bool, skillGenerator : Callable[[str], SkillData],
            register : bool = True):
        super().__init__(skillName, playerClass, rank, True, isFreeSkill, description, mpCost, actionTime, False,
                         [], expectedTargets, 0, targetOpponents, register)
        self.skillGenerator = skillGenerator
        
    def selectSkill(self, selectorInput : str) -> SkillData:
        return self.skillGenerator(selectorInput)

class SkillEffect(object):
    def __init__(self, effectFunctions : list[EffectFunction], effectDuration : int | None):
        self.effectFunctions : list[EffectFunction] = effectFunctions[:]
        self.effectDuration : int | None = effectDuration

class EffectFunction(object):
    def __init__(self, effectTiming : EffectTimings):
        self.effectTiming : EffectTimings = effectTiming

"""An immediate effect upon using an active skill"""
class EFImmediate(EffectFunction):
    def __init__(self, func : Callable[[CombatController, CombatEntity, list[CombatEntity], EffectFunctionResult], None]):
        super().__init__(EffectTimings.IMMEDIATE)
        self.func : Callable[[CombatController, CombatEntity, list[CombatEntity], EffectFunctionResult], None] = func

    def applyEffect(self, controller : CombatController, user : CombatEntity, targets : list[CombatEntity]) -> EffectFunctionResult:
        result = EffectFunctionResult(self)
        self.func(controller, user, targets, result)
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

        return EffectFunctionResult(self)

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

        result = EffectFunctionResult(self)
        if self.revertFunc is not None:
            self.revertFunc(controller, user, target, result)
        return result

"""A reaction to being targeted by an attack."""
class EFBeforeAttacked(EffectFunction):
    def __init__(self, flatStatBonuses : dict[Stats, float], multStatBonuses : dict[Stats, float],
            applyFunc : None | Callable[[CombatController, CombatEntity, CombatEntity], None],
            revertFunc : None | Callable[[CombatController, CombatEntity, CombatEntity, EffectFunctionResult], None]):
        super().__init__(EffectTimings.BEFORE_ATTACKED)
        self.flatStatBonuses : dict[Stats, float] = flatStatBonuses
        self.multStatBonuses : dict[Stats, float] = multStatBonuses
        self.applyFunc : None | Callable[[CombatController, CombatEntity, CombatEntity], None] = applyFunc
        self.revertFunc : None | Callable[[CombatController, CombatEntity, CombatEntity, EffectFunctionResult], None] = revertFunc


    def applyEffect(self, controller : CombatController, user : CombatEntity, attacker : CombatEntity) -> EffectFunctionResult:
        controller.applyFlatStatBonuses(user, self.flatStatBonuses)
        controller.applyMultStatBonuses(user, self.multStatBonuses)

        if self.applyFunc is not None:
            self.applyFunc(controller, user, attacker)
        revertEffect : SkillEffect = SkillEffect([EFBeforeAttacked_Revert(self.flatStatBonuses, self.multStatBonuses, self.revertFunc)], 0)
        controller.addSkillEffect(attacker, revertEffect)

        return EffectFunctionResult(self)

# Note: tracked by attacker, so that it gets cleared at the end of the attack
class EFBeforeAttacked_Revert(EffectFunction):
    def __init__(self, flatStatBonuses : dict[Stats, float], multStatBonuses : dict[Stats, float],
            revertFunc : None | Callable[[CombatController, CombatEntity, CombatEntity, EffectFunctionResult], None]):
        super().__init__(EffectTimings.AFTER_ATTACK)
        self.flatStatBonuses : dict[Stats, float] = flatStatBonuses
        self.multStatBonuses : dict[Stats, float] = multStatBonuses
        self.revertFunc : None | Callable[[CombatController, CombatEntity, CombatEntity, EffectFunctionResult], None] = revertFunc

    def applyEffect(self, controller : CombatController, user : CombatEntity, attacker : CombatEntity) -> EffectFunctionResult:
        controller.revertFlatStatBonuses(user, self.flatStatBonuses)
        controller.revertMultStatBonuses(user, self.multStatBonuses)

        result = EffectFunctionResult(self)
        if self.revertFunc is not None:
            self.revertFunc(controller, user, attacker, result)
        return result

"""A reaction to the results of the next attack."""
class EFAfterNextAttack(EffectFunction):
    def __init__(self, func : Callable[[CombatController, CombatEntity, CombatEntity, AttackResultInfo, EffectFunctionResult], None]):
        super().__init__(EffectTimings.AFTER_ATTACK)
        self.func : Callable[[CombatController, CombatEntity, CombatEntity, AttackResultInfo, EffectFunctionResult], None] = func

    def applyEffect(self, controller : CombatController, user : CombatEntity, target : CombatEntity,
            attackResultInfo : AttackResultInfo) -> EffectFunctionResult:
        result = EffectFunctionResult(self)
        self.func(controller, user, target, attackResultInfo, result)
        return result

"""A reaction to the results of being attacked."""
class EFWhenAttacked(EffectFunction):
    def __init__(self, func : Callable[[CombatController, CombatEntity, CombatEntity, AttackResultInfo, EffectFunctionResult], None]):
        super().__init__(EffectTimings.AFTER_ATTACKED)
        self.func : Callable[[CombatController, CombatEntity, CombatEntity, AttackResultInfo, EffectFunctionResult], None] = func

    def applyEffect(self, controller : CombatController, user : CombatEntity, attacker : CombatEntity,
            attackResultInfo : AttackResultInfo) -> EffectFunctionResult:
        result = EffectFunctionResult(self)
        self.func(controller, user, attacker, attackResultInfo, result)
        return result

"""A reaction to an ally being targeted by an attack."""
class EFBeforeAllyAttacked(EffectFunction):
    def __init__(self, func : Callable[[CombatController, CombatEntity, CombatEntity, CombatEntity, EffectFunctionResult], None]):
        super().__init__(EffectTimings.BEFORE_ATTACKED)
        self.func : Callable[[CombatController, CombatEntity, CombatEntity, CombatEntity, EffectFunctionResult], None] = func

    def applyEffect(self, controller : CombatController, user : CombatEntity, attacker : CombatEntity, target: CombatEntity) -> EffectFunctionResult:
        result = EffectFunctionResult(self)
        self.func(controller, user, attacker, target, result)
        return result

"""A reaction to the distance to a target being changed."""
class EFOnDistanceChange(EffectFunction):
    def __init__(self, func : Callable[[CombatController, CombatEntity, CombatEntity, bool, int, int, EffectFunctionResult], None]):
        super().__init__(EffectTimings.ON_REPOSITION)
        self.func : Callable[[CombatController, CombatEntity, CombatEntity, bool, int, int, EffectFunctionResult], None] = func

    def applyEffect(self, controller : CombatController, user : CombatEntity, target : CombatEntity,
            userMoved : bool, initialDistance : int, finalDistance : int) -> EffectFunctionResult:
        result = EffectFunctionResult(self)
        self.func(controller, user, target, userMoved, initialDistance, finalDistance, result)
        return result

"""A reaction to HP, MP, or other stats changing."""
class EFOnStatsChange(EffectFunction):
    def __init__(self, func : Callable[[CombatController, CombatEntity, dict[Stats, float], dict[Stats, float], EffectFunctionResult], None]):
        super().__init__(EffectTimings.ON_STAT_CHANGE)
        self.func : Callable[[CombatController, CombatEntity, dict[Stats, float], dict[Stats, float], EffectFunctionResult], None] = func

    def applyEffect(self, controller : CombatController, user : CombatEntity,
            previousStats : dict[Stats, float], newStats : dict[Stats, float]) -> EffectFunctionResult:
        result = EffectFunctionResult(self)
        self.func(controller, user, previousStats, newStats, result)
        return result

"""A reaction to being attacked by a declared attack type."""
class EFOnParry(EffectFunction):
    def __init__(self, func : Callable[[CombatController, CombatEntity, CombatEntity, bool, EffectFunctionResult], None]):
        super().__init__(EffectTimings.PARRY)
        self.func : Callable[[CombatController, CombatEntity, CombatEntity, bool, EffectFunctionResult], None] = func

    def applyEffect(self, controller : CombatController, user : CombatEntity, attacker: CombatEntity, isPhysical : bool) -> EffectFunctionResult:
        result = EffectFunctionResult(self)
        self.func(controller, user, attacker, isPhysical, result)
        return result
    
"""An effect that always occurs at the beginning of a turn."""
class EFStartTurn(EffectFunction):
    def __init__(self, func : Callable[[CombatController, CombatEntity, EffectFunctionResult], None]):
        super().__init__(EffectTimings.START_TURN)
        self.func : Callable[[CombatController, CombatEntity, EffectFunctionResult], None] = func

    def applyEffect(self, controller : CombatController, user : CombatEntity) -> EffectFunctionResult:
        result = EffectFunctionResult(self)
        self.func(controller, user, result)
        return result
    
"""An effect that always occurs at the end of a turn (before duration ticks)."""
class EFEndTurn(EffectFunction):
    def __init__(self, func : Callable[[CombatController, CombatEntity, EffectFunctionResult], None]):
        super().__init__(EffectTimings.END_TURN)
        self.func : Callable[[CombatController, CombatEntity, EffectFunctionResult], None] = func

    def applyEffect(self, controller : CombatController, user : CombatEntity) -> EffectFunctionResult:
        result = EffectFunctionResult(self)
        self.func(controller, user, result)
        return result

class EffectFunctionResult(object):
    def __init__(self, effectFunction : EffectFunction, actionTime : float | None = None,
                 actionTimeMult : float | None = None, bonusAttack : tuple[CombatEntity, CombatEntity, AttackSkillData] | None = None,
                 damageMultiplier : float | None = None):
        self.effectFunction = effectFunction
        self.actionTime = actionTime
        self.actionTimeMult = actionTimeMult
        self.bonusAttack = bonusAttack
        self.damageMultiplier = damageMultiplier

    def setActionTime(self, actionTime: float):
        self.actionTime = actionTime

    def setActionTimeMult(self, actionTimeMult: float):
        self.actionTimeMult = actionTimeMult

    def setBonusAttack(self, user : CombatEntity, target : CombatEntity, attackData : AttackSkillData):
        self.bonusAttack = (user, target, attackData)

    def setDamageMultiplier(self, damageMultiplier: float):
        self.damageMultiplier = damageMultiplier

# load definitions
from rpg_skill_definitions import *