from __future__ import annotations
from typing import TYPE_CHECKING
import math

from rpg_consts import *
from rpg_classes_skills import SkillEffect, EffectFunction, EFImmediate, EFBeforeNextAttack, EFAfterNextAttack, EFWhenAttacked, EFOnStatsChange, \
        EFOnParry, EFBeforeAllyAttacked, EFEndTurn, EFBeforeAttacked

if TYPE_CHECKING:
    from rpg_classes_skills import EffectFunctionResult
    from rpg_combat_entity import CombatEntity
    from rpg_combat_state import CombatController

EFFECT_EXTENSION_CONST = 0.5 # The chance of a 2-duration stun extending an existing stun, for instance
def amplifyExtensionChance(newDuration):
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
    def amplifyStatus(self, newStatus : StatusEffect, randRoll : float) -> int:
        return 0

class PoisonStatusEffect(StatusEffect):
    def __init__(self, inflicter : CombatEntity, target : CombatEntity, duration : int, poisonStrength : int):
        self.poisonStrength : int = poisonStrength
        self.poisonEffectFunction : EffectFunction = EFEndTurn(self._poisonTick)
        super().__init__(StatusConditionNames.POISON, inflicter, duration, [self.poisonEffectFunction])

    def _poisonTick(self, controller : CombatController, target : CombatEntity, result : EffectFunctionResult):
        controller.applyDamage(self.inflicter, target, self.poisonStrength)

    def amplifyStatus(self, newStatus : StatusEffect, randRoll : float) -> int:
        if isinstance(newStatus, PoisonStatusEffect):
            self.poisonStrength += math.ceil(newStatus.poisonStrength * POISON_STACK_SCALING)
        return 0
    
class TargetStatusEffect(StatusEffect):
    def __init__(self, inflicter: CombatEntity, target : CombatEntity, duration : int):
        targetEffectFunction : EffectFunction = EFBeforeAttacked({CombatStats.GUARANTEE_SELF_HIT: 1}, {}, None, None)
        super().__init__(StatusConditionNames.TARGET, inflicter, duration, [targetEffectFunction])

    def amplifyStatus(self, newStatus : StatusEffect, randRoll : float) -> int:
        if isinstance(newStatus, TargetStatusEffect):
            if randRoll < amplifyExtensionChance(newStatus.effectDuration):
                return 1
        return 0