from __future__ import annotations
from typing import TYPE_CHECKING
import math

from rpg_consts import *
from rpg_classes_skills import EFEndTurn, EFOnAdvanceTurn, EFOnDistanceChange, EFOnStatusApplied, EFStartTurn, PassiveSkillData, AttackSkillData, ActiveBuffSkillData, ActiveToggleSkillData, CounterSkillData, \
    ActiveSkillDataSelector, PrepareParrySkillData, \
    SkillEffect, EFImmediate, EFBeforeNextAttack, EFAfterNextAttack, EFWhenAttacked, EFOnStatsChange, \
        EFOnParry, EFBeforeAllyAttacked
from rpg_status_definitions import BlindStatusEffect, ExhaustionStatusEffect, FearStatusEffect, MisfortuneStatusEffect, PerplexityStatusEffect, \
    PoisonStatusEffect, RestrictStatusEffect, StunStatusEffect, TargetStatusEffect

if TYPE_CHECKING:
    from rpg_classes_skills import EffectFunctionResult
    from rpg_combat_entity import CombatEntity
    from rpg_combat_state import CombatController

# Warrior

PassiveSkillData("Warrior's Resolution", BasePlayerClassNames.WARRIOR, 1, False,
    "Increases HP by 100, ATK by 10, and DEF by 5.",
    {BaseStats.HP: 100, BaseStats.ATK: 10, BaseStats.DEF: 5}, {}, [])

AttackSkillData("Great Swing", BasePlayerClassNames.WARRIOR, 2, False, 20,
    "Attack with 1.5x ATK.",
    True, AttackType.MELEE, 1.5, DEFAULT_ATTACK_TIMER_USAGE, [])

PassiveSkillData("Endurance", BasePlayerClassNames.WARRIOR, 3, True,
    "Recovers 2% HP at the end of your turn.",
    {}, {}, [SkillEffect([EFAfterNextAttack(
      lambda controller, user, _1, _2, _3: void(controller.gainHealth(user, round(controller.getMaxHealth(user) * 0.02)))
    )], None)])


# Ranger

PassiveSkillData("Ranger's Focus", BasePlayerClassNames.RANGER, 1, False,
    "Increases ACC by 25, RES by 10, and SPD by 5.",
    {BaseStats.ACC: 25, BaseStats.RES: 10, BaseStats.SPD: 5}, {}, [])

def increaseDistanceFn(controller, user, target, _1, result : EffectFunctionResult):
    currentDistance = controller.checkDistance(user, target)
    if currentDistance is not None:
        reactionAttackData = controller.updateDistance(user, target, currentDistance + 1)
        [result.setBonusAttack(*reactionAttack) for reactionAttack in reactionAttackData]
AttackSkillData("Strafe", BasePlayerClassNames.RANGER, 2, False, 15,
    "Attack with 0.8x ATK, increasing distance to the target by 1.",
    True, AttackType.RANGED, 0.8, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect([EFAfterNextAttack(increaseDistanceFn)], 0)])

PassiveSkillData("Eagle Eye", BasePlayerClassNames.RANGER, 3, True,
    "Distance has less of a negative impact on your accuracy.",
    {}, {}, [SkillEffect([EFImmediate(
        lambda controller, user, _1, _2: controller.applyMultStatBonuses(user, {CombatStats.ACCURACY_DISTANCE_MOD: 0.5})
    )], None)])


# Rogue

PassiveSkillData("Rogue's Instinct", BasePlayerClassNames.ROGUE, 1, False,
    "Increases AVO by 25, SPD by 10, and ATK by 5.",
    {BaseStats.AVO: 25, BaseStats.SPD: 10, BaseStats.ATK: 5}, {}, [])

AttackSkillData("Swift Strike", BasePlayerClassNames.ROGUE, 2, False, 10,
    "Attack with 0.7x ATK, but a reduced time until next action.",
    True, None, 0.7, DEFAULT_ATTACK_TIMER_USAGE / 2, [])

def illusionFn(controller, user, attacker, attackInfo, _2):
    if attackInfo.inRange and not attackInfo.attackHit:
        counterData = CounterSkillData(True, None, 0.7,
                                       [SkillEffect([EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1}, {}, None, None)], 0)])
        attackInfo.addBonusAttack(user, attacker, counterData)
PassiveSkillData("Illusion", BasePlayerClassNames.ROGUE, 3, True,
    "When dodging an enemy in range, counter with 0.7x ATK.",
    {}, {}, [SkillEffect([EFWhenAttacked(illusionFn)], None)])


# Mage

PassiveSkillData("Mage's Patience", BasePlayerClassNames.MAGE, 1, False,
    "Increases MP by 50, MAG by 10, and RES by 5.",
    {BaseStats.MP: 50, BaseStats.MAG: 10, BaseStats.RES: 5}, {}, [])

AttackSkillData("Magic Missile", BasePlayerClassNames.MAGE, 2, False, 15,
    "Attack with 1x MAG from any range.",
    False, AttackType.MAGIC, 1, DEFAULT_ATTACK_TIMER_USAGE,
    [SkillEffect([EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1}, {}, None, None)], 0)])

PassiveSkillData("Mana Flow", BasePlayerClassNames.MAGE, 3, True,
    "When attacking, restore MP equal to 5% of the damge you deal (max 30).",
    {}, {}, [SkillEffect([EFAfterNextAttack(
        lambda controller, user, _1, attackInfo, _2: void(controller.gainMana(user, min(math.ceil(attackInfo.damageDealt * 0.05), 30)))
    )], None)])


####

# Mercenary

PassiveSkillData("Mercenary's Strength", AdvancedPlayerClassNames.MERCENARY, 1, False,
    "Increases ATK by 15% and ACC by 10%.",
    {}, {BaseStats.ATK: 1.15, BaseStats.ACC: 1.10}, [])

AttackSkillData("Sweeping Blow", AdvancedPlayerClassNames.MERCENARY, 2, False, 30,
    "Attack with 0.8x ATK, reducing DEF of the target by 15% on hit.",
    True, AttackType.MELEE, 0.8, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect([EFAfterNextAttack(
        lambda controller, _1, target, attackInfo, _2:
            controller.applyMultStatBonuses(target, {BaseStats.DEF: 0.85}) if attackInfo.attackHit else None
    )], 0)])

def confrontationFn(controller, user, target, revert, attackResultInfo = None):
    amount = 1.1
    if revert: # check if was initially at range 0
        if attackResultInfo is not None and attackResultInfo.originalDistance > 0:
            return
        controller.revertMultStatBonuses(user, {BaseStats.ATK: amount, BaseStats.ACC: amount})
    else: # check if currently at range 0
        if controller.checkDistance(user, target) > 0:
            return
        controller.applyMultStatBonuses(user, {BaseStats.ATK: amount, BaseStats.ACC: amount})
PassiveSkillData("Confrontation", AdvancedPlayerClassNames.MERCENARY, 3, True,
    "When attacking at distance 0, increase ATK and ACC by 10%.",
    {}, {}, [SkillEffect([EFBeforeNextAttack({}, {},
                    lambda controller, user, target: confrontationFn(controller, user, target, False),
                    lambda controller, user, target, attackResultInfo, _2: confrontationFn(controller, user, target, True, attackResultInfo)
    )], None)])

def frenzyFn(controller, user, originalStats, finalStats, _):
    originalMissing = 0
    newMissing = 0
    if SpecialStats.CURRENT_HP in originalStats:
        baseHP = controller.combatStateMap[user].getTotalStatValue(BaseStats.HP)
        originalMissing = baseHP - originalStats[SpecialStats.CURRENT_HP]
        newMissing = baseHP - finalStats[SpecialStats.CURRENT_HP]
    elif BaseStats.HP in originalStats:
        currentHP = controller.getCurrentHealth(user)
        originalMissing = originalStats[BaseStats.HP] - currentHP
        newMissing = finalStats[BaseStats.HP] - currentHP
    else:
        return
    controller.applyFlatStatBonuses(user, {BaseStats.ATK: (newMissing - originalMissing)* 0.1})
PassiveSkillData("Battle Frenzy", AdvancedPlayerClassNames.MERCENARY, 4, False,
    "Increases ATK by 10% of your missing HP.",
    {}, {}, [SkillEffect([EFOnStatsChange(frenzyFn)], None)])

ActiveToggleSkillData("Berserk", AdvancedPlayerClassNames.MERCENARY, 5, False, 10,
    "[Toggle] Decrease DEF, RES, and AVO by 50%. Increase ATK and SPD by 50%.", MAX_ACTION_TIMER / 10, {},
    {BaseStats.ATK: 1.5, BaseStats.SPD: 1.5, BaseStats.DEF: 0.5, BaseStats.RES: 0.5, BaseStats.AVO: 0.5}, [],
    0, 0, True)

PassiveSkillData("Determination", AdvancedPlayerClassNames.MERCENARY, 6, True,
    "Increases ATK by 15%, ACC by 5%, and SPD by 5%.",
    {}, {BaseStats.ATK: 1.15, BaseStats.ACC: 1.05, BaseStats.SPD: 1.05}, [])

def deadlyDanceFn(controller, user, target, attackInfo, _):
    if attackInfo.attackHit and not attackInfo.isBonus:
        otherOpponents = [opp for opp in controller.getTargets(user) if opp is not target]
        inRangeOpponents = list(filter(lambda opp: controller.checkInRange(user, opp), otherOpponents))
        if len(inRangeOpponents) > 0:
            bonusTarget = controller.rng.choice(inRangeOpponents)
            newPower = attackInfo.damageDealt * 0.3
            counterData = CounterSkillData(True, AttackType.MELEE, 1,
                                        [SkillEffect([EFBeforeNextAttack({CombatStats.FIXED_ATTACK_POWER: newPower}, {}, None, None)], 0)])
            attackInfo.addBonusAttack(user, bonusTarget, counterData)
PassiveSkillData("Deadly Dance", AdvancedPlayerClassNames.MERCENARY, 7, False,
    "If your first attack of a turn hits, trigger a bonus attack based on 30% of the damage dealt against another enemy in range.",
    {}, {}, [SkillEffect([EFAfterNextAttack(deadlyDanceFn)], None)])

def undeterredFn(controller, user, _1, attackInfo, _2):
    if attackInfo.inRange and not attackInfo.attackHit and not attackInfo.isBonus:
        buffEffect = SkillEffect([EFBeforeNextAttack({},
                                {BaseStats.ATK: 1.25, BaseStats.MAG: 1.25, BaseStats.ACC: 1.25}, None, None)], 2)
        controller.addSkillEffect(user, buffEffect)
PassiveSkillData("Undeterred", AdvancedPlayerClassNames.MERCENARY, 8, True,
    "When you miss a (non-bonus) attack, increase ATK, MAG, and ACC by 25% for your next attack.",
    {}, {}, [SkillEffect([EFAfterNextAttack(undeterredFn)], None)])

ActiveBuffSkillData("Heroic Legacy", AdvancedPlayerClassNames.MERCENARY, 9, True, 90,
    "[Buff] For your next 3 turns, (non-bonus) attacks are repeated as bonus attacks.", MAX_ACTION_TIMER / 10, {}, {},
    [SkillEffect([EFAfterNextAttack(
        lambda _1, _2, _3, attackResultInfo, _4: attackResultInfo.setRepeatAttack() if not attackResultInfo.isBonus else None)], 4)],
    0, 0, True)

# Knight

PassiveSkillData("Knight's Vitality", AdvancedPlayerClassNames.KNIGHT, 1, False,
    "Increases HP by 20% and DEF by 15%.",
    {}, {BaseStats.HP: 1.2, BaseStats.DEF: 1.15}, [])

AttackSkillData("Challenge", AdvancedPlayerClassNames.KNIGHT, 2, False, 10,
    "Attack with 1x ATK, generating 3x the aggro from the target.",
    True, AttackType.MELEE, 1, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect([EFBeforeNextAttack({}, {CombatStats.AGGRO_MULT: 3}, None, None)], 0)])

def chivalryUpdateFn(controller, user, oldStats, newStats, _):
    if BaseStats.DEF in oldStats:
        oldDefBonus = round(oldStats[BaseStats.DEF] * 0.4)
        newDefBonus = round(newStats[BaseStats.DEF] * 0.4)
        controller.applyFlatStatBonuses(user, {BaseStats.RES: newDefBonus - oldDefBonus})
PassiveSkillData("Chivalry", AdvancedPlayerClassNames.KNIGHT, 3, True,
    "Increases RES by 30% of your DEF.",
    {}, {}, [SkillEffect([
        EFImmediate(lambda controller, user, _1, _2:
                    controller.applyFlatStatBonuses(user, {BaseStats.RES: round(controller.combatStateMap[user].getTotalStatValue(BaseStats.DEF) * 0.3)})),
        EFOnStatsChange(chivalryUpdateFn)
    ], None)])

PassiveSkillData("Justified", AdvancedPlayerClassNames.KNIGHT, 4, False,
    "Restore 10% of the damage you deal as HP.",
    {}, {}, [SkillEffect([EFAfterNextAttack(
      lambda controller, user, _1, attackInfo, _2: void(controller.gainHealth(user, math.ceil(attackInfo.damageDealt * 0.1)))
    )], None)])

def parryFn(controller, user, attacker, isPhysical, effectResult):
    effectResult.setDamageMultiplier(0.35)
    offensiveStat = BaseStats.ATK if isPhysical else BaseStats.MAG
    parryStrength = controller.combatStateMap[attacker].getTotalStatValue(offensiveStat) * 0.5
    counterData = CounterSkillData(True, None, 1,
                                    [SkillEffect([EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1, BaseStats.ATK: parryStrength},
                                                                     {}, None, None)], 0)])
    effectResult.setBonusAttack(user, attacker, counterData)
ActiveSkillDataSelector("Parry", AdvancedPlayerClassNames.KNIGHT, 5, False, 25,
    "Select an attack type. If the next attack on you matches, reduce damage taken by 65% and parry based on 50% of their offensive stat.",
    MAX_ACTION_TIMER, 0, True,
        lambda parryType: PrepareParrySkillData(f"Parry ({parryType[0] + parryType[1:].lower()})", AdvancedPlayerClassNames.KNIGHT, 5, False, 25, "",
            MAX_ACTION_TIMER, AttackType[parryType], [EFOnParry(parryFn)], False), [attackType.name for attackType in AttackType]
    )

PassiveSkillData("Persistence", AdvancedPlayerClassNames.KNIGHT, 6, True,
    "Increases DEF by 15% and HP by 10%.",
    {}, {BaseStats.DEF: 1.15, BaseStats.HP: 1.10}, [])

def unifiedSpiritsFn(controller, user, attacker, defender, _):
    userDistance = controller.checkDistance(user, attacker)
    allyDistance = controller.checkDistance(defender, attacker)
    if userDistance is not None and allyDistance is not None and userDistance < allyDistance:
        defBonus = controller.combatStateMap[user].getTotalStatValue(BaseStats.DEF) * 0.3
        resBonus = controller.combatStateMap[user].getTotalStatValue(BaseStats.RES) * 0.3
        flatStatBonuses : dict[Stats, float] = {BaseStats.DEF: defBonus, BaseStats.RES: resBonus}
        controller.applyFlatStatBonuses(defender, flatStatBonuses)
        revertEffect : SkillEffect = SkillEffect([EFAfterNextAttack(
            lambda controller_, attacker_, defender_, _1, _2: controller_.revertFlatStatBonuses(defender, flatStatBonuses)
        )], 0)
        controller.addSkillEffect(attacker, revertEffect)
PassiveSkillData("Unified Spirits", AdvancedPlayerClassNames.KNIGHT, 7, False,
    "When an ally is attacked, if their distance from the target is greater than yours, they gain 30% of your DEF/RES.",
    {}, {}, [SkillEffect([
        EFBeforeAllyAttacked(unifiedSpiritsFn)
    ], None)])

PassiveSkillData("Protector's Insight", AdvancedPlayerClassNames.KNIGHT, 8, True,
    "Increases the effect of your resistances and targets' weaknesses, and decreases the effect of your weaknesses and targets' resistances.",
    {}, {CombatStats.WEAKNESS_MODIFIER: 0.5, CombatStats.RESISTANCE_MODIFIER: 1.5,
         CombatStats.BONUS_WEAKNESS_DAMAGE_MULT: 1.5, CombatStats.IGNORE_RESISTANCE_MULT: 0.5}, [])

def atlasFn(controller, user, attacker, defender, _):
    damageReduction : dict[Stats, float] = {CombatStats.DAMAGE_REDUCTION: 0.3}
    controller.applyFlatStatBonuses(defender, damageReduction)
    revertEffectFn = EFAfterNextAttack(
        lambda controller_, attacker_, defender_, _1, _2: controller_.revertFlatStatBonuses(defender, damageReduction)
    )
    redirectEffectFn = EFAfterNextAttack(
        lambda controller_, attacker_, _1, attackResult, _2:
            attackResult.addBonusAttack(attacker_, user, CounterSkillData(attackResult.isPhysical, attackResult.attackType, 1,
                    [SkillEffect([EFBeforeNextAttack({
                        CombatStats.IGNORE_RANGE_CHECK: 1,
                        CombatStats.FIXED_ATTACK_POWER: attackResult.damageDealt * 3/5
                    }, {}, None, None)], 0)]))
    )
    followupEffect : SkillEffect = SkillEffect([revertEffectFn, redirectEffectFn], 0)
    controller.addSkillEffect(attacker, followupEffect)
ActiveToggleSkillData("Burden of Atlas", AdvancedPlayerClassNames.KNIGHT, 9, True, 10,
    "[Toggle] Reduces the damage all allies take by 30%, redirecting part of it to you as a bonus attack.", MAX_ACTION_TIMER / 10,
    {}, {}, [SkillEffect([
        EFBeforeAllyAttacked(atlasFn)
    ], None)], 0, 0, True)

# Sniper

PassiveSkillData("Sniper's Aim", AdvancedPlayerClassNames.SNIPER, 1, False,
    "Increases ACC by 25% and SPD by 10%.",
    {}, {BaseStats.ACC: 1.25, BaseStats.SPD: 1.10}, [])

AttackSkillData("Target Lock", AdvancedPlayerClassNames.SNIPER, 2, False, 10,
    "Attack with 1x ATK, attempting to inflict TARGET for 3 turns. (Attacks against a TARGETED opponent always hit.)",
    True, AttackType.RANGED, 1, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect([
        EFAfterNextAttack(lambda controller, user, target, attackResult, _: void(
                        controller.applyStatusCondition(target, TargetStatusEffect(user, target, 3)) if attackResult.attackHit else None))
    ], 0)])

PassiveSkillData("Steady Hand", AdvancedPlayerClassNames.SNIPER, 3, True,
    "Gain 6% ATK at the end of every turn, up to a maximum of 60%. This bonus resets if your distance to any opponent changes.",
    {}, {}, [SkillEffect([
        EFImmediate(lambda controller, user, _1, _2: void((
            controller.combatStateMap[user].setStack(EffectStacks.STEADY_HAND, 0),
        ))),
        EFEndTurn(lambda controller, user, _: void((
            controller.revertMultStatBonuses(user, {BaseStats.ATK: 1 + (controller.combatStateMap[user].getStack(EffectStacks.STEADY_HAND) * 0.06)}),
            controller.combatStateMap[user].addStack(EffectStacks.STEADY_HAND, 10),
            controller.applyMultStatBonuses(user, {BaseStats.ATK: 1 + (controller.combatStateMap[user].getStack(EffectStacks.STEADY_HAND) * 0.06)})
        ))),
        EFOnDistanceChange(lambda controller, user, _1, _2, oldDist, newDist, _3: void((
            controller.revertMultStatBonuses(user, {BaseStats.ATK: 1 + (controller.combatStateMap[user].getStack(EffectStacks.STEADY_HAND) * 0.06)}),
            controller.combatStateMap[user].setStack(EffectStacks.STEADY_HAND, 0)
        )) if oldDist != newDist else None)
    ], None)])

PassiveSkillData("Suppressive Fire", AdvancedPlayerClassNames.SNIPER, 4, False,
    "Apply a debuff stack when hitting an opponent, up to 10 stacks. Each stack reduces SPD and AVO by 6%.",
    {}, {}, [SkillEffect([
        EFAfterNextAttack(lambda controller, _1, target, attackResult, _2: void((
            controller.revertMultStatBonuses(target, {
                BaseStats.SPD: 1 - (controller.combatStateMap[target].getStack(EffectStacks.SUPPRESSIVE_FIRE) * 0.06),
                BaseStats.AVO: 1 - (controller.combatStateMap[target].getStack(EffectStacks.SUPPRESSIVE_FIRE) * 0.06)
            }),
            controller.combatStateMap[target].addStack(EffectStacks.SUPPRESSIVE_FIRE, 10),
            controller.applyMultStatBonuses(target, {
                BaseStats.SPD: 1 - (controller.combatStateMap[target].getStack(EffectStacks.SUPPRESSIVE_FIRE) * 0.06),
                BaseStats.AVO: 1 - (controller.combatStateMap[target].getStack(EffectStacks.SUPPRESSIVE_FIRE) * 0.06)
            })
        )) if attackResult.attackHit else None)
    ], None)])

AttackSkillData("Perfect Shot", AdvancedPlayerClassNames.SNIPER, 5, False, 30,
    "Attack with 1x ATK, plus 0.4x ATK per distance from the target.",
    True, AttackType.RANGED, 1, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect([
        EFBeforeNextAttack({}, {},
                           lambda controller, user, target:
                                controller.applyMultStatBonuses(user, {BaseStats.ATK: 1 + (controller.checkDistanceStrict(user, target) * 0.4)}),
                           lambda controller, user, target, attackResult, _:
                                controller.revertMultStatBonuses(user, {BaseStats.ATK: 1 + (attackResult.originalDistance * 0.4)})
    )], 0)])

PassiveSkillData("Precision", AdvancedPlayerClassNames.SNIPER, 6, True,
    "Increases ACC by 15% and SPD by 10%.",
    {}, {BaseStats.ACC: 1.15, BaseStats.SPD: 1.10}, [])

PassiveSkillData("Clarity", AdvancedPlayerClassNames.SNIPER, 7, False,
    "Increases Critical Hit rate by 10% per distance from your target.",
    {}, {}, [SkillEffect([
        EFBeforeNextAttack({}, {},
                           lambda controller, user, target:
                                controller.applyFlatStatBonuses(user, {CombatStats.CRIT_RATE: controller.checkDistanceStrict(user, target) * 0.1}),
                           lambda controller, user, target, attackResult, _:
                                controller.revertFlatStatBonuses(user, {CombatStats.CRIT_RATE: attackResult.originalDistance * 0.1})
    )], None)])

PassiveSkillData("Nimble Feet", AdvancedPlayerClassNames.SNIPER, 8, True,
    "Decreases the time until your next action when repositioning.",
    {}, {CombatStats.REPOSITION_ACTION_TIME_MULT: 0.7}, [])

AttackSkillData("Winds of Solitude", AdvancedPlayerClassNames.SNIPER, 9, False, 25,
    "Attack with 1x ATK; on hit, increase distance to the target by 1 and attempt to inflict RESTRICT for 2 turns. (RESTRICTED opponents cannot reposition.)",
    True, AttackType.RANGED, 1, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect([
        EFAfterNextAttack(lambda controller, user, target, attackResult, _: void((
            increaseDistanceFn(controller, user, target, attackResult, _),
            controller.applyStatusCondition(target, RestrictStatusEffect(user, target, 2)))
        ) if attackResult.attackHit else None)
    ], 0)])


# Hunter

PassiveSkillData("Hunter's Willpower", AdvancedPlayerClassNames.HUNTER, 1, False,
    "Increases ACC by 15%, RES by 15%, and DEF by 5%.",
    {}, {BaseStats.ACC: 1.15, BaseStats.RES: 1.15, BaseStats.DEF: 1.05}, [])

def lacedStatus(statusString : str, controller : CombatController, user : CombatEntity, target : CombatEntity):
    if statusString.upper() == "POISON":
        poisonStrength = math.ceil(controller.combatStateMap[user].getTotalStatValue(BaseStats.ATK) * 0.5)
        return PoisonStatusEffect(user, target, 6, poisonStrength)
    elif statusString.upper() == "BLIND":
        return BlindStatusEffect(user, target, 4)
    elif statusString.upper() == "STUN":
        return StunStatusEffect(user, target, 2)
    else:
        raise KeyError
ActiveSkillDataSelector("Laced Ammunition", AdvancedPlayerClassNames.HUNTER, 2, False, 20,
    "Select POISON (50% Strength, 6 Turns), BLIND (4 Turns), or STUN (2 Turns). Attack with 0.8x ATK, attempting to inflict the selected status condition.",
    DEFAULT_ATTACK_TIMER_USAGE, 1, True,
    lambda statusString: AttackSkillData(f"Laced Ammunition ({statusString[0] + statusString[1:].lower()})",
                                         AdvancedPlayerClassNames.HUNTER, 2, False, 20, "",
    True, AttackType.RANGED, 0.7, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect([
        EFAfterNextAttack(lambda controller, user, target, attackResult, _: void(
                        controller.applyStatusCondition(target, lacedStatus(statusString, controller, user, target)) if attackResult.attackHit else None))
    ], 0)], False), ["POISON", "BLIND", "STUN"])

PassiveSkillData("Camouflage", AdvancedPlayerClassNames.HUNTER, 3, True,
    "Decrease aggro generated from attacks by 20% per distance from your target.",
    {}, {}, [SkillEffect([
        EFBeforeNextAttack({}, {},
                           lambda controller, user, target:
                                controller.applyMultStatBonuses(user, {CombatStats.AGGRO_MULT: 1 - (controller.checkDistanceStrict(user, target) * 0.2)}),
                           lambda controller, user, target, attackResult, _:
                                controller.revertMultStatBonuses(user, {CombatStats.AGGRO_MULT: 1 - (attackResult.originalDistance * 0.2)})
    )], None)])

def coveredTracksFn(controller : CombatController, user : CombatEntity, target : CombatEntity, userMoved : bool,
                    oldDistance : int, newDistance : int, effectResult : EffectFunctionResult):
    if not userMoved and newDistance < oldDistance:
        counterData = CounterSkillData(True, None, 0.7,
                                       [SkillEffect([
                                           EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1}, {}, None, None),
                                           EFAfterNextAttack(lambda controller, user, target, attackResult, _: void(
                        controller.applyStatusCondition(target, ExhaustionStatusEffect(user, target, 3, 1.3)) if attackResult.attackHit else None))
                                        ], 0)])
        effectResult.setBonusAttack(user, target, counterData)
PassiveSkillData("Covered Tracks", AdvancedPlayerClassNames.HUNTER, 4, False,
    "When an opponent approaches you, counter with 0.7x ATK, attempting to inflict EXHAUST (30% strength) for 3 turns.",
    {}, {}, [SkillEffect([EFOnDistanceChange(coveredTracksFn)], None)])

ActiveBuffSkillData("Weakening Trap", AdvancedPlayerClassNames.HUNTER, 5, False, 25,
    "[Buff] Target any ally. For their next three turns, attacks hitting them lower the attacker's DEF, RES, ACC, and AVO by 7%.",
    DEFAULT_ATTACK_TIMER_USAGE / 2, {}, {},
    [SkillEffect([EFImmediate(lambda controller, user, targets, _: controller.addSkillEffect(targets[0], SkillEffect([
        EFWhenAttacked(lambda controller, user, attacker, attackInfo, _: controller.applyMultStatBonuses(attacker, {
            BaseStats.DEF: 0.93,
            BaseStats.RES: 0.93,
            BaseStats.ACC: 0.93,
            BaseStats.AVO: 0.93
        }) if attackInfo.attackHit else None)
    ], 3)))], 0)],
    1, 0, False)

PassiveSkillData("Resourcefulness", AdvancedPlayerClassNames.HUNTER, 6, True,
    "Increases MP by 10%, DEF by 5%, RES by 5%, and ACC by 5%.",
    {}, {BaseStats.MP: 1.1, BaseStats.DEF: 1.05, BaseStats.RES: 1.05, BaseStats.ACC: 1.05}, [])

PassiveSkillData("Primal Fear", AdvancedPlayerClassNames.HUNTER, 7, False,
    "When successfully applying a status condition, additionally attempt to inflict FEAR (10% strength) for 3 turns.",
    {}, {}, [SkillEffect([EFOnStatusApplied(
        lambda controller, user, target, statusName, _:
            void(controller.applyStatusCondition(target, FearStatusEffect(user, target, 3, 0.9))) if statusName != StatusConditionNames.FEAR else None
    )], None)])

PassiveSkillData("Viral Evolution", AdvancedPlayerClassNames.HUNTER, 8, True,
    "Increases the success rate of applying status conditions by 40%.",
    {}, {CombatStats.STATUS_APPLICATION_TOLERANCE_MULTIPLIER: 0.6}, [])

AttackSkillData("Enclosing Fangs", AdvancedPlayerClassNames.HUNTER, 9, True, 25,
    "Attack with 1.2x ATK. On hit, decrease all of the target's current status condition tolerances by 20% of the damage dealt.",
    True, AttackType.RANGED, 1.2, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect([
        EFAfterNextAttack(lambda controller, user, target, attackResult, _: void(
            [controller.combatStateMap[target].reduceTolerance(status, math.ceil(attackResult.damageDealt * 0.15)) for status in StatusConditionNames]
        ) if attackResult.attackHit else None)
    ], 0)])


# Assassin

PassiveSkillData("Assassin's Swiftness", AdvancedPlayerClassNames.ASSASSIN, 1, False,
    "Increases SPD by 20% and ATK by 5%.",
    {}, {BaseStats.SPD: 1.2, BaseStats.ATK: 1.05}, [])

def shadowingMovementFn(controller : CombatController, user : CombatEntity, targets : list[CombatEntity], result : EffectFunctionResult):
    target = targets[0]
    currentDistance = controller.checkDistance(user, target)
    if currentDistance is not None:
        controller.combatStateMap[user].setStack(EffectStacks.SHADOWING, currentDistance)
        reactionAttackData = controller.updateDistance(user, target, 0)
        [result.setBonusAttack(*reactionAttack) for reactionAttack in reactionAttackData]
ActiveBuffSkillData("Shadowing", AdvancedPlayerClassNames.ASSASSIN, 2, False, 10,
    "Reposition to be distance 0 from your target. Until your next turn ends, gain 15% ATK per distance you moved.", DEFAULT_APPROACH_TIMER_USAGE, {}, {},
    [SkillEffect([
        EFImmediate(shadowingMovementFn),
        EFBeforeNextAttack({}, {}, 
                           lambda controller, user, _: controller.applyMultStatBonuses(user,
                                {BaseStats.ATK: 1 + (controller.combatStateMap[user].getStack(EffectStacks.SHADOWING) * 0.15)}),
                           lambda controller, user, _1, _2, _3: controller.revertMultStatBonuses(user,
                                {BaseStats.ATK: 1 + (controller.combatStateMap[user].getStack(EffectStacks.SHADOWING) * 0.15)})
                                )], 2)],
    1, 0, True)

PassiveSkillData("Vital Strike", AdvancedPlayerClassNames.ASSASSIN, 3, True,
    "Increases Critical Hit rate by 5% and Critical Hit damage by 50%.",
    {CombatStats.CRIT_RATE: 0.05, CombatStats.CRIT_DAMAGE: 0.5}, {}, [])

PassiveSkillData("Eyes of the Dark", AdvancedPlayerClassNames.ASSASSIN, 4, False,
    "Apply a debuff stack when hitting an opponent, up to 10 stacks. Each stack reduces AVO by 3% and DEF/RES by 2%.",
    {}, {}, [SkillEffect([
        EFAfterNextAttack(lambda controller, _1, target, attackResult, _2: void((
            controller.revertMultStatBonuses(target, {
                BaseStats.AVO: 1 - (controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) * 0.03),
                BaseStats.DEF: 1 - (controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) * 0.02),
                BaseStats.RES: 1 - (controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) * 0.02)
            }),
            controller.combatStateMap[target].addStack(EffectStacks.EYES_OF_THE_DARK, 10),
            controller.applyMultStatBonuses(target, {
                BaseStats.AVO: 1 - (controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) * 0.03),
                BaseStats.DEF: 1 - (controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) * 0.02),
                BaseStats.RES: 1 - (controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) * 0.02)
            })
        )) if attackResult.attackHit else None)
    ], None)])


ambushSkillEffects : dict[str, SkillEffect] = {
    "INTERROGATE": SkillEffect([
        EFBeforeNextAttack({}, {BaseStats.ATK: 0.5}, None, None),
        EFAfterNextAttack(lambda controller, user, target, attackResult, _: void((
                controller.applyMultStatBonuses(user, {
                    BaseStats.ATK: 1 + (controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) * 0.04),
                    BaseStats.SPD: 1 + (controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) * 0.04),
                    BaseStats.ACC: 1 + (controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) * 0.08)
                }),
                controller.revertMultStatBonuses(target, {
                    BaseStats.AVO: 1 - (controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) * 0.03),
                    BaseStats.DEF: 1 - (controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) * 0.02),
                    BaseStats.RES: 1 - (controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) * 0.02)
                }),
                controller.combatStateMap[target].setStack(EffectStacks.EYES_OF_THE_DARK, 0)
            )) if attackResult.attackHit else None)
    ], 0),
    "DISABLE": SkillEffect([
        EFBeforeNextAttack({}, {BaseStats.ATK: 0.8}, None, None),
        EFAfterNextAttack(lambda controller, _1, target, attackResult, _2: void((
                controller.applyMultStatBonuses(target, {
                    BaseStats.ATK: 1 - (controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) * 0.035),
                    BaseStats.DEF: 1 - (controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) * 0.035),
                    BaseStats.MAG: 1 - (controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) * 0.035),
                    BaseStats.RES: 1 - (controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) * 0.035)
                }),
                controller.revertMultStatBonuses(target, {
                    BaseStats.AVO: 1 - (controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) * 0.03),
                    BaseStats.DEF: 1 - (controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) * 0.02),
                    BaseStats.RES: 1 - (controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) * 0.02)
                }),
                controller.combatStateMap[target].setStack(EffectStacks.EYES_OF_THE_DARK, 0)
            )) if attackResult.attackHit else None)
    ], 0),
    "EXECUTE": SkillEffect([
        EFBeforeNextAttack({}, {},
            lambda controller, user, target:  void((
                controller.applyFlatStatBonuses(user, {
                    CombatStats.CRIT_RATE: controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) * 0.1
                }),
                controller.applyMultStatBonuses(user, {
                    BaseStats.ATK: 0.7 + (controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) * 0.1)
                }),
                controller.combatStateMap[user].setStack(EffectStacks.EOTD_CONSUMED, controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK))
            )),
            lambda controller, user, target, attackResult, _2: void((
                controller.revertFlatStatBonuses(user, {
                    CombatStats.CRIT_RATE: controller.combatStateMap[user].getStack(EffectStacks.EOTD_CONSUMED) * 0.1
                }),
                controller.revertMultStatBonuses(user, {
                    BaseStats.ATK: 0.7 + (controller.combatStateMap[user].getStack(EffectStacks.EOTD_CONSUMED) * 0.1)
                }),
                controller.revertMultStatBonuses(target, {
                    BaseStats.AVO: 1 - (controller.combatStateMap[user].getStack(EffectStacks.EOTD_CONSUMED) * 0.03),
                    BaseStats.DEF: 1 - (controller.combatStateMap[user].getStack(EffectStacks.EOTD_CONSUMED) * 0.02),
                    BaseStats.RES: 1 - (controller.combatStateMap[user].getStack(EffectStacks.EOTD_CONSUMED) * 0.02)
                }) if attackResult.attackHit else None,
                controller.combatStateMap[user].setStack(EffectStacks.EOTD_CONSUMED, 0),
                controller.combatStateMap[target].setStack(EffectStacks.EYES_OF_THE_DARK, 0) if attackResult.attackHit else None
            )))
    ], 0)
}
ActiveSkillDataSelector("Ambush", AdvancedPlayerClassNames.ASSASSIN, 5, False, 40,
    "Select an effect and attack a target, removing all Eyes of the Dark stacks on hit. | " +
    "INTERROGATE: Attack with 0.5x ATK. Per stack removed, +4% ATK/SPD and +8% ACC. | " +
    "DISABLE: Attack with 0.8x ATK. Per stack removed, opponent ATK/DEF/MAG/RES - 3.5%. | " +
    "EXECUTE: Attack with 0.7x ATK, +0.1x per stack removed. Additional 10% Critical Hit rate per stack removed.",
    DEFAULT_ATTACK_TIMER_USAGE, 1, True,
    lambda ambushString: AttackSkillData(f"Ambush ({ambushString[0] + ambushString[1:].lower()})",
                                         AdvancedPlayerClassNames.ASSASSIN, 5, False, 40, "",
    True, None, 0.7, DEFAULT_ATTACK_TIMER_USAGE, [ambushSkillEffects[ambushString]], False), ["INTERROGATE", "DISABLE", "EXECUTE"])

PassiveSkillData("Relentlessness", AdvancedPlayerClassNames.ASSASSIN, 6, True,
    "Increases SPD by 15%, ATK by 5%, and ACC by 5%.",
    {}, {BaseStats.SPD: 1.15, BaseStats.ATK: 1.05, BaseStats.ACC: 1.05}, [])

PassiveSkillData("Opportunism", AdvancedPlayerClassNames.ASSASSIN, 7, False,
    "Your attacks always calculate damage against the opponent's lower defensive stat (DEF or RES).",
    {CombatStats.OPPORTUNISM: 1}, {}, [])

PassiveSkillData("Unrelenting Assault", AdvancedPlayerClassNames.ASSASSIN, 8, True,
    "After each attack, +20% ATK/MAG. Resets when it is no longer your turn.",
    {}, {}, [SkillEffect([
        EFAfterNextAttack(
            lambda controller, user, target, _1, _2: void((
                controller.revertMultStatBonuses(user, {
                    BaseStats.ATK: 1 + (controller.combatStateMap[user].getStack(EffectStacks.UNRELENTING_ASSAULT) * 0.2),
                    BaseStats.MAG: 1 + (controller.combatStateMap[user].getStack(EffectStacks.UNRELENTING_ASSAULT) * 0.2)
                }),
                controller.combatStateMap[user].addStack(EffectStacks.UNRELENTING_ASSAULT, None),
                controller.applyMultStatBonuses(user, {
                    BaseStats.ATK: 1 + (controller.combatStateMap[user].getStack(EffectStacks.UNRELENTING_ASSAULT) * 0.2),
                    BaseStats.MAG: 1 + (controller.combatStateMap[user].getStack(EffectStacks.UNRELENTING_ASSAULT) * 0.2)
                })
            ))
        ),
        EFOnAdvanceTurn(
            lambda controller, user, _1, nextPlayer, _2: void((
                controller.revertMultStatBonuses(user, {
                    BaseStats.ATK: 1 + (controller.combatStateMap[user].getStack(EffectStacks.UNRELENTING_ASSAULT) * 0.2),
                    BaseStats.MAG: 1 + (controller.combatStateMap[user].getStack(EffectStacks.UNRELENTING_ASSAULT) * 0.2)
                }),
                controller.combatStateMap[user].setStack(EffectStacks.UNRELENTING_ASSAULT, 0)
            )) if nextPlayer != user and controller.combatStateMap[user].getStack(EffectStacks.UNRELENTING_ASSAULT) > 0 else None
        )
    ], None)])

ActiveBuffSkillData("Instantaneous Eternity", AdvancedPlayerClassNames.ASSASSIN, 9, True, 90,
    "Take three turns in a row. (You cannot gain any MP during the first two.)", 0, {}, {}, [SkillEffect([
        EFImmediate(
            lambda controller, user, _1, _2: controller.applyFlatStatBonuses(user, {CombatStats.INSTANTANEOUS_ETERNITY: 1})
        ),
        EFStartTurn(
            lambda controller, user, _: controller.applyFlatStatBonuses(user, {CombatStats.INSTANTANEOUS_ETERNITY: 1})
        ),
        EFEndTurn(
            lambda controller, user, _: controller.revertFlatStatBonuses(user, {CombatStats.INSTANTANEOUS_ETERNITY: 1})
        )
    ], 3)], 0, 0, True)


# Acrobot

PassiveSkillData("Acrobat's Flexibility", AdvancedPlayerClassNames.ACROBAT, 1, False,
    "Increases AVO by 25% and SPD by 10%.",
    {}, {BaseStats.AVO: 1.25, BaseStats.SPD: 1.1}, [])

AttackSkillData("Bedazzle", AdvancedPlayerClassNames.ACROBAT, 2, False, 15,
    "Attack with 1x ATK, attempting to inflict BLIND for 3 turns. (BLINDED opponents calculate accuracy as if their distance is 1 greater.)",
    True, None, 1, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect([
        EFAfterNextAttack(lambda controller, user, target, attackResult, _: void(
                        controller.applyStatusCondition(target, BlindStatusEffect(user, target, 3)) if attackResult.attackHit else None))
    ], 0)])

PassiveSkillData("Mockery", AdvancedPlayerClassNames.ACROBAT, 3, True,
    "All attacks generate 30% more aggro.",
    {}, {CombatStats.AGGRO_MULT: 1.3}, [])

PassiveSkillData("Ride the Wake", AdvancedPlayerClassNames.ACROBAT, 4, False,
    "When dodging an enemy in range, gain 10% ATK/ACC.",
    {}, {}, [SkillEffect([EFWhenAttacked(lambda controller, user, _1, attackResult, _2:
                                controller.applyMultStatBonuses(user, {
                                    BaseStats.ATK: 1.1,
                                    BaseStats.ACC: 1.1
                                }) if attackResult.inRange else None
    )], None)])

def sidestepFn(controller : CombatController, user : CombatEntity, _2, _3, effectResult : EffectFunctionResult):
    controller.increaseActionTimer(user, 0.75)
    effectResult.setGuaranteeDodge(True)
ActiveSkillDataSelector("Sidestep", AdvancedPlayerClassNames.ACROBAT, 5, False, 25,
    "Select an attack type. If the next attack on you matches, evade it and reduce the time to your next action.",
    MAX_ACTION_TIMER, 0, True,
        lambda parryType: PrepareParrySkillData(f"Sidestep ({parryType[0] + parryType[1:].lower()})", AdvancedPlayerClassNames.ACROBAT, 5, False, 25, "",
            MAX_ACTION_TIMER, AttackType[parryType], [EFOnParry(sidestepFn)], False), [attackType.name for attackType in AttackType]
    )

PassiveSkillData("Adaptation", AdvancedPlayerClassNames.ACROBAT, 6, True,
    "Increases AVO by 15%, MP by 5%, and SPD by 5%.",
    {}, {BaseStats.AVO: 1.15, BaseStats.MP: 1.05, BaseStats.SPD: 1.05}, [])

PassiveSkillData("Graceful Weaving", AdvancedPlayerClassNames.ACROBAT, 7, False,
    "Increases Range by 1. Your distance is treated as being reduced by 1 when you calculate accuracy.",
    {CombatStats.RANGE: 1, CombatStats.ACC_EFFECTIVE_DISTANCE_MOD: -1}, {}, [])

def confidenceFn(controller : CombatController, user : CombatEntity, originalStats : dict[Stats, float], finalStats : dict[Stats, float], _):
    originalFull = False
    newFull = False
    if SpecialStats.CURRENT_HP in originalStats:
        baseHP = controller.combatStateMap[user].getTotalStatValue(BaseStats.HP)
        originalFull = baseHP == originalStats[SpecialStats.CURRENT_HP]
        newFull = baseHP == finalStats[SpecialStats.CURRENT_HP]
    elif BaseStats.HP in originalStats:
        currentHP = controller.getCurrentHealth(user)
        originalFull = originalStats[BaseStats.HP] == currentHP
        newFull = finalStats[BaseStats.HP] == currentHP
    else:
        return
    
    if newFull and not originalFull:
        controller.applyMultStatBonuses(user, {
                BaseStats.ATK: 1.25,
                BaseStats.MAG: 1.25,
                BaseStats.SPD: 1.25,
                BaseStats.ACC: 1.25,
                BaseStats.AVO: 1.25
        })
    elif originalFull and not newFull:
        controller.revertMultStatBonuses(user, {
                BaseStats.ATK: 1.25,
                BaseStats.MAG: 1.25,
                BaseStats.SPD: 1.25,
                BaseStats.ACC: 1.25,
                BaseStats.AVO: 1.25
        })
PassiveSkillData("Earned Confidence", AdvancedPlayerClassNames.ACROBAT, 8, True,
    "At full health, +25% ATK/MAG/SPD/ACC/AVO.",
    {}, {}, [SkillEffect([
        EFImmediate(lambda controller, user, _1, _2:controller.applyMultStatBonuses(user, {
                BaseStats.ATK: 1.25,
                BaseStats.MAG: 1.25,
                BaseStats.SPD: 1.25,
                BaseStats.ACC: 1.25,
                BaseStats.AVO: 1.25
            }) if controller.combatStateMap[user].getTotalStatValue(BaseStats.HP) == controller.getCurrentHealth(user) else None
        ),
        EFOnStatsChange(confidenceFn)
    ], None)])

ActiveSkillDataSelector("Insidious Killer", AdvancedPlayerClassNames.ACROBAT, 9, True, 15,
    "Decrease DEF/RES by 25%. Increase AVO by 25% and SPD by 10%. This can be used up to 3 times simultaneously for greater effect.",
    MAX_ACTION_TIMER / 10, 0, True,
    lambda amount: ActiveBuffSkillData(f"Insidious Killer x{amount}",
                                         AdvancedPlayerClassNames.ACROBAT, 9, True, 15 * int(amount), "",
    0, {}, {}, [SkillEffect([
        EFImmediate(lambda controller, user, _1, _2: controller.applyMultStatBonuses(user, {
            BaseStats.DEF: 1 - (0.25 * int(amount)),
            BaseStats.RES: 1 - (0.25 * int(amount)),
            BaseStats.AVO: 1 + (0.25 * int(amount)),
            BaseStats.SPD: 1 + (0.1 * int(amount)),
        }))
    ], None)], 0, 0, True, False), ["1", "2", "3"])