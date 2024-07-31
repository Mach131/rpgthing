from __future__ import annotations
from typing import Any, Callable
import random

from gameData.rpg_item_data import *
from gameData.rpg_status_definitions import RestrictStatusEffect, StunStatusEffect
from structures.rpg_classes_skills import ActiveBuffSkillData, ActiveSkillDataSelector, ActiveToggleSkillData, AttackSkillData, CounterSkillData, EFAfterNextAttack, EFBeforeAllyAttacked, EFBeforeAttacked, EFBeforeNextAttack, EFEndTurn, EFImmediate, EFOnStatsChange, EFOnStatusApplied, EFOnToggle, EFStartTurn, EFWhenAttacked, EffectFunctionResult, SkillEffect, EFOnAdvanceTurn, EFOnOpponentDotDamage
from rpg_consts import *
from structures.rpg_combat_entity import *
from structures.rpg_combat_state import AttackResultInfo


def waitSkill(name, timeMult):
    return SkillData(name, BasePlayerClassNames.WARRIOR, 0, True, False, "", 0, MAX_ACTION_TIMER * timeMult, False,
                         [], 0, 0, True, False)

def rollEquip(controller : CombatController, entity : CombatEntity, dropChance : float, equip : Equipment) -> Equipment | None:
    if controller._randomRoll(None, entity) < dropChance:
        return equip
    
def weaknessEffect(attribute : AttackAttribute, stacks : int) -> SkillData:
    return PassiveSkillData(f"{enumName(attribute)} Weakness x{stacks}", BasePlayerClassNames.WARRIOR, 0, False, "",
                            {}, {}, [
                                SkillEffect(f"", [EFImmediate(
                                    lambda controller, user, _1, _2: controller.addWeaknessStacks(user, attribute, stacks))], None)
                            ], False)
def resistanceEffect(attribute : AttackAttribute, stacks : int) -> SkillData:
    return PassiveSkillData(f"{enumName(attribute)} Resistance x{stacks}", BasePlayerClassNames.WARRIOR, 0, False, "",
                            {}, {}, [
                                SkillEffect(f"", [EFImmediate(
                                    lambda controller, user, _1, _2: controller.addResistanceStacks(user, attribute, stacks))], None)
                            ], False)

def getIncreaseDistanceFn(dist):
    def newFn(controller, user, target, _1, result : EffectFunctionResult):
        currentDistance = controller.checkDistance(user, target)
        if currentDistance is not None:
            reactionAttackData = controller.updateDistance(user, target, currentDistance + dist)
            [result.setBonusAttack(*reactionAttack) for reactionAttack in reactionAttackData]
    return newFn

def makeAoeSkillEffect(isPhysical : bool, attackType : AttackType | None,
                            condition : Callable[[CombatController, CombatEntity, CombatEntity, AttackResultInfo], bool] | None = None):
    def aoeAfterFn(controller, user, target, attackInfo, _):
        conditionCheck = condition(controller, user, target, attackInfo) if condition is not None else True
        if not attackInfo.isBonus and conditionCheck:
            otherOpponents = [opp for opp in controller.getTargets(user) if opp is not target]
            for bonusTarget in otherOpponents:
                counterData = CounterSkillData(isPhysical, attackType, 1, [SkillEffect("", [], 0)])
                attackInfo.addBonusAttack(user, bonusTarget, counterData)
    return SkillEffect("", [EFAfterNextAttack(aoeAfterFn)], 0)
