from __future__ import annotations
from typing import TYPE_CHECKING
import math

from rpg_consts import *
from rpg_classes_skills import SkillEffect, EffectFunction, EFImmediate, EFBeforeNextAttack, EFAfterNextAttack, EFWhenAttacked, EFOnStatsChange, \
        EFOnParry, EFBeforeAllyAttacked, EFStartTurn, EFEndTurn, EFBeforeAttacked

if TYPE_CHECKING:
    from rpg_classes_skills import EffectFunctionResult
    from rpg_combat_entity import CombatEntity
    from rpg_combat_state import AttackResultInfo, CombatController

EFFECT_EXTENSION_CONST = 0.5 # The chance of a 2-duration stun extending an existing stun, for instance
def amplifyExtensionChance(newDuration : int):
    k = 1 / (1 - EFFECT_EXTENSION_CONST)
    exp = - math.log(k ** 0.5) * EFFECT_EXTENSION_CONST
    return 1 - math.exp(exp)

class StatusEffect(SkillEffect):
    def __init__(self, statusName : StatusConditionNames, inflicter : CombatEntity, duration : int,
                 effectFunctions : list[EffectFunction]):
        super().__init__(effectFunctions, duration)
        self.statusName : StatusConditionNames = statusName
        self.inflicter : CombatEntity = inflicter
        self.effectFunctions : list[EffectFunction] = effectFunctions
    
    """
        Updates the status effect as the result of another of the same type being applied.
        Returns any duration increases this may cause.
    """
    def amplifyStatus(self, controller : CombatController, target : CombatEntity, newStatus : StatusEffect, randRoll : float) -> int:
        return 0
    
    def onRemove(self, controller : CombatController, target : CombatEntity) -> None:
        pass

class PoisonStatusEffect(StatusEffect):
    def __init__(self, inflicter : CombatEntity, target : CombatEntity, duration : int, poisonStrength : int):
        self.poisonStrength : int = poisonStrength
        self.poisonEffectFunction : EffectFunction = EFEndTurn(self._poisonTick)
        super().__init__(StatusConditionNames.POISON, inflicter, duration, [self.poisonEffectFunction])

    def _poisonTick(self, controller : CombatController, target : CombatEntity, result : EffectFunctionResult):
        controller.applyDamage(self.inflicter, target, self.poisonStrength)
        print(f"{target.name} takes {self.poisonStrength} damage from POISON!")

    def amplifyStatus(self, controller : CombatController, target : CombatEntity, newStatus : StatusEffect, randRoll : float) -> int:
        if isinstance(newStatus, PoisonStatusEffect):
            self.poisonStrength += math.ceil(newStatus.poisonStrength * DOT_STACK_SCALING)
        return 0

class BurnStatusEffect(StatusEffect):
    def __init__(self, inflicter : CombatEntity, target : CombatEntity, duration : int, burnStrength : int):
        self.burnStrength : int = burnStrength
        burnEffectFunction : EffectFunction = EFEndTurn(self._burnTick)
        super().__init__(StatusConditionNames.BURN, inflicter, duration, [burnEffectFunction])

    def _burnTick(self, controller : CombatController, target : CombatEntity, result : EffectFunctionResult):
        controller.applyDamage(self.inflicter, target, self.burnStrength)
        print(f"{target.name} takes {self.burnStrength} damage from BURN!")

    def amplifyStatus(self, controller : CombatController, target : CombatEntity, newStatus : StatusEffect, randRoll : float) -> int:
        if isinstance(newStatus, BurnStatusEffect):
            self.burnStrength += math.ceil(newStatus.burnStrength * DOT_STACK_SCALING)
        return 0
    
class TargetStatusEffect(StatusEffect):
    def __init__(self, inflicter: CombatEntity, target : CombatEntity, duration : int):
        targetEffectFunction : EffectFunction = EFBeforeAttacked({CombatStats.GUARANTEE_SELF_HIT: 1}, {}, None, None)
        super().__init__(StatusConditionNames.TARGET, inflicter, duration, [targetEffectFunction])

    def amplifyStatus(self, controller : CombatController, target : CombatEntity, newStatus : StatusEffect, randRoll : float) -> int:
        if isinstance(newStatus, TargetStatusEffect):
            if newStatus.effectDuration is not None:
                if randRoll < amplifyExtensionChance(newStatus.effectDuration):
                    return 1
        return 0
    
class BlindStatusEffect(StatusEffect):
    def __init__(self, inflicter: CombatEntity, target : CombatEntity, duration : int):
        self.blindStacks = 0
        self.currentAppliedMultiplier = 1
        blindEffectFunction : EffectFunction = EFBeforeNextAttack({
            CombatStats.ACC_EFFECTIVE_DISTANCE_MOD: 1}, {}, self._applyBlindAccPenalty, self._revertBlindAccPenalty)
        super().__init__(StatusConditionNames.BLIND, inflicter, duration, [blindEffectFunction])

    def _applyBlindAccPenalty(self, controller : CombatController, user : CombatEntity, target : CombatEntity) -> None:
        self.currentAppliedMultiplier = BLIND_STACK_ACC_MULT ** self.blindStacks
        controller.applyMultStatBonuses(user, {BaseStats.ACC: self.currentAppliedMultiplier})

    def _revertBlindAccPenalty(self, controller : CombatController, user : CombatEntity, target : CombatEntity, _1, _2) -> None:
        controller.revertMultStatBonuses(user, {BaseStats.ACC: self.currentAppliedMultiplier})

    def amplifyStatus(self, controller : CombatController, target : CombatEntity, newStatus : StatusEffect, randRoll : float) -> int:
        if isinstance(newStatus, BlindStatusEffect):
            if newStatus.effectDuration is not None:
                self.blindStacks += newStatus.effectDuration
        return 0
    
class StunStatusEffect(StatusEffect):
    def __init__(self, inflicter: CombatEntity, target : CombatEntity, duration : int):
        super().__init__(StatusConditionNames.STUN, inflicter, duration, [])

    def amplifyStatus(self, controller : CombatController, target : CombatEntity, newStatus : StatusEffect, randRoll : float) -> int:
        if isinstance(newStatus, StunStatusEffect):
            if newStatus.effectDuration is not None:
                if randRoll < amplifyExtensionChance(newStatus.effectDuration):
                    return 1
        return 0
    
class ExhaustionStatusEffect(StatusEffect):
    def __init__(self, inflicter: CombatEntity, target : CombatEntity, duration : int, multiplier : float):
        self.multiplier = multiplier
        self.currentAppliedMultiplier = 1
        beginTurnEffect = EFStartTurn(self._applyExhaustionPenalty)
        endTurnEffect = EFEndTurn(self._revertExhaustionPenalty)
        super().__init__(StatusConditionNames.EXHAUSTION, inflicter, duration, [beginTurnEffect, endTurnEffect])

    def _applyExhaustionPenalty(self, controller : CombatController, user : CombatEntity, _) -> None:
        self.currentAppliedMultiplier = self.multiplier
        controller.applyMultStatBonuses(user, {CombatStats.ACTION_GAUGE_USAGE_MULTIPLIER: self.currentAppliedMultiplier})

    def _revertExhaustionPenalty(self, controller : CombatController, user : CombatEntity, _) -> None:
        if self.currentAppliedMultiplier != 1:
            controller.revertMultStatBonuses(user, {CombatStats.ACTION_GAUGE_USAGE_MULTIPLIER: self.currentAppliedMultiplier})

    def amplifyStatus(self, controller : CombatController, target : CombatEntity, newStatus : StatusEffect, randRoll : float) -> int:
        if isinstance(newStatus, ExhaustionStatusEffect):
            self.multiplier += (newStatus.multiplier - 1) * EXHAUST_STACK_SCALING
        return 0
    
class MisfortuneStatusEffect(StatusEffect):
    def __init__(self, inflicter: CombatEntity, target : CombatEntity, duration : int):
        self.bonusRolls = 1
        self.currentAppliedBonus = 0
        immediateEffect = EFImmediate(self._refreshMisfortunePenalty)
        super().__init__(StatusConditionNames.MISFORTUNE, inflicter, duration, [immediateEffect])

    def _refreshMisfortunePenalty(self, controller : CombatController, user : CombatEntity, _1, _2) -> None:
        if self.currentAppliedBonus != 0:
            controller.revertFlatStatBonuses(user, {CombatStats.LUCK: self.currentAppliedBonus})
        self.currentAppliedBonus = - self.bonusRolls
        controller.applyFlatStatBonuses(user, {CombatStats.LUCK: self.currentAppliedBonus})

    def amplifyStatus(self, controller : CombatController, target : CombatEntity, newStatus : StatusEffect, randRoll : float) -> int:
        if isinstance(newStatus, MisfortuneStatusEffect):
            if newStatus.effectDuration is not None:
                if randRoll < amplifyExtensionChance(newStatus.effectDuration):
                    self.bonusRolls += 1
                    self._refreshMisfortunePenalty(controller, target, None, None)
        return 0
    
    def onRemove(self, controller : CombatController, target : CombatEntity) -> None:
        controller.revertFlatStatBonuses(target, {CombatStats.LUCK: self.currentAppliedBonus})

class RestrictStatusEffect(StatusEffect):
    def __init__(self, inflicter: CombatEntity, target : CombatEntity, duration : int):
        super().__init__(StatusConditionNames.RESTRICT, inflicter, duration, [])

    def amplifyStatus(self, controller : CombatController, target : CombatEntity, newStatus : StatusEffect, randRoll : float) -> int:
        if isinstance(newStatus, RestrictStatusEffect):
            if newStatus.effectDuration is not None:
                if randRoll < amplifyExtensionChance(newStatus.effectDuration):
                    return 1
        return 0
    
class PerplexityStatusEffect(StatusEffect):
    def __init__(self, inflicter: CombatEntity, target : CombatEntity, duration : int, multiplier : float):
        self.multiplier = multiplier
        self.currentAppliedMultiplier = 1
        beginTurnEffect = EFStartTurn(self._applyPerplexityPenalty)
        endTurnEffect = EFEndTurn(self._revertPerplexityPenalty)
        super().__init__(StatusConditionNames.PERPLEXITY, inflicter, duration, [beginTurnEffect, endTurnEffect])

    def _applyPerplexityPenalty(self, controller : CombatController, user : CombatEntity, _) -> None:
        self.currentAppliedMultiplier = self.multiplier
        controller.applyMultStatBonuses(user, {CombatStats.MANA_COST_MULT: self.currentAppliedMultiplier})

    def _revertPerplexityPenalty(self, controller : CombatController, user : CombatEntity, _) -> None:
        if self.currentAppliedMultiplier != 1:
            controller.revertMultStatBonuses(user, {CombatStats.MANA_COST_MULT: self.currentAppliedMultiplier})

    def amplifyStatus(self, controller : CombatController, target : CombatEntity, newStatus : StatusEffect, randRoll : float) -> int:
        if isinstance(newStatus, PerplexityStatusEffect):
            self.multiplier += (newStatus.multiplier - 1) * PERPLEXITY_STACK_SCALING
        return 0
    
class FearStatusEffect(StatusEffect):
    def __init__(self, inflicter: CombatEntity, target : CombatEntity, duration : int, multiplier : float):
        self.multiplier = multiplier
        fearEffectFunction : EffectFunction = EFWhenAttacked(self._procFearEffect)
        super().__init__(StatusConditionNames.FEAR, inflicter, duration, [fearEffectFunction])

    def _procFearEffect(self, controller : CombatController, user : CombatEntity, attacker : CombatEntity, attackResult : AttackResultInfo, _):
        if attackResult.attackHit and attacker == self.inflicter:
            targetStat = controller.rng.choice([BaseStats.ATK, BaseStats.DEF, BaseStats.MAG, BaseStats.RES,
                                                BaseStats.ACC, BaseStats.AVO, BaseStats.SPD])
            controller.applyMultStatBonuses(user, {targetStat: self.multiplier})
            print(f"FEAR effect decreases {targetStat.name}!")

    def amplifyStatus(self, controller : CombatController, target : CombatEntity, newStatus : StatusEffect, randRoll : float) -> int:
        if isinstance(newStatus, FearStatusEffect):
            if newStatus.effectDuration is not None:
                if randRoll < amplifyExtensionChance(newStatus.effectDuration):
                    return 1
        return 0
    
STATUS_CLASS_MAP = {
    StatusConditionNames.BLIND: BlindStatusEffect,
    StatusConditionNames.BURN: BurnStatusEffect,
    StatusConditionNames.EXHAUSTION: ExhaustionStatusEffect,
    StatusConditionNames.FEAR: FearStatusEffect,
    StatusConditionNames.MISFORTUNE: MisfortuneStatusEffect,
    StatusConditionNames.PERPLEXITY: PerplexityStatusEffect,
    StatusConditionNames.POISON: PoisonStatusEffect,
    StatusConditionNames.RESTRICT: RestrictStatusEffect,
    StatusConditionNames.STUN: StunStatusEffect,
    StatusConditionNames.TARGET: TargetStatusEffect
}