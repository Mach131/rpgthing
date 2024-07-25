from __future__ import annotations
from typing import TYPE_CHECKING, Callable
import math

from rpg_consts import *
from structures.rpg_classes_skills import EFBeforeAttacked, EFEndTurn, EFOnAdvanceTurn, EFOnAttackSkill, EFOnDistanceChange, EFOnHealSkill, EFOnStatusApplied, EFStartTurn, EnchantmentSkillEffect, PassiveSkillData, AttackSkillData, ActiveBuffSkillData, ActiveToggleSkillData, CounterSkillData, \
    ActiveSkillDataSelector, PrepareParrySkillData, \
    SkillEffect, EFImmediate, EFBeforeNextAttack, EFAfterNextAttack, EFWhenAttacked, EFOnStatsChange, \
        EFOnParry, EFBeforeAllyAttacked, EFOnOpponentDotDamage
from gameData.rpg_status_definitions import BlindStatusEffect, BurnStatusEffect, ExhaustionStatusEffect, FearStatusEffect, MisfortuneStatusEffect, PerplexityStatusEffect, \
    PoisonStatusEffect, RestrictStatusEffect, StatusEffect, StunStatusEffect, TargetStatusEffect

if TYPE_CHECKING:
    from structures.rpg_classes_skills import EffectFunctionResult, EffectFunction
    from structures.rpg_combat_entity import CombatEntity
    from structures.rpg_combat_state import CombatController, AttackResultInfo

# Warrior

PassiveSkillData("Warrior's Resolution", BasePlayerClassNames.WARRIOR, 1, False,
    "Increases HP by 50, ATK by 10, and DEF by 5.",
    {BaseStats.HP: 50, BaseStats.ATK: 10, BaseStats.DEF: 5}, {}, [])

AttackSkillData("Great Swing", BasePlayerClassNames.WARRIOR, 2, False, 20,
    "Perform a slower attack with 1.5x ATK.",
    True, AttackType.MELEE, 1.5, DEFAULT_ATTACK_TIMER_USAGE * 1.2, [])

PassiveSkillData("Endurance", BasePlayerClassNames.WARRIOR, 3, True,
    "Recovers 2% HP at the end of your turn.",
    {}, {}, [SkillEffect("", [EFEndTurn(
        lambda controller, user, skipDurationTick, _: void(
          controller.gainHealth(user, round(controller.getMaxHealth(user) * 0.02))
        ) if not skipDurationTick and controller.getCurrentHealth(user) > 0 else None
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
    True, AttackType.RANGED, 0.8, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect("", [EFAfterNextAttack(increaseDistanceFn)], 0)])

PassiveSkillData("Eagle Eye", BasePlayerClassNames.RANGER, 3, True,
    "Distance has less of a negative impact on your accuracy.",
    {}, {}, [SkillEffect("", [EFImmediate(
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
                                       [SkillEffect("", [EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1}, {}, None, None)], 0)])
        attackInfo.addBonusAttack(user, attacker, counterData)
PassiveSkillData("Illusion", BasePlayerClassNames.ROGUE, 3, True,
    "When dodging an enemy in range, counter with 0.7x ATK.",
    {}, {}, [SkillEffect("", [EFWhenAttacked(illusionFn)], None)])


# Mage

PassiveSkillData("Mage's Patience", BasePlayerClassNames.MAGE, 1, False,
    "Increases MP by 50, MAG by 10, and RES by 5.",
    {BaseStats.MP: 50, BaseStats.MAG: 10, BaseStats.RES: 5}, {}, [])

AttackSkillData("Magic Missile", BasePlayerClassNames.MAGE, 2, False, 15,
    "Attack with 1x MAG from any range.",
    False, AttackType.MAGIC, 1, DEFAULT_ATTACK_TIMER_USAGE,
    [SkillEffect("", [EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1}, {}, None, None)], 0)])

PassiveSkillData("Mana Flow", BasePlayerClassNames.MAGE, 3, True,
    "When attacking, restore MP equal to 5% of the damge you deal (max 30).",
    {}, {}, [SkillEffect("", [EFAfterNextAttack(
        lambda controller, user, _1, attackInfo, _2: void(controller.gainMana(user, min(math.ceil(attackInfo.damageDealt * 0.05), 30)))
    )], None)])


####

# Mercenary

PassiveSkillData("Mercenary's Strength", AdvancedPlayerClassNames.MERCENARY, 1, False,
    "Increases ATK by 15% and ACC by 10%.",
    {}, {BaseStats.ATK: 1.15, BaseStats.ACC: 1.10}, [])

AttackSkillData("Sweeping Blow", AdvancedPlayerClassNames.MERCENARY, 2, False, 30,
    "Attack with 0.8x ATK, reducing DEF of the target by 15% on hit.",
    True, AttackType.MELEE, 0.8, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect("", [EFAfterNextAttack(
        lambda controller, _1, target, attackInfo, _2: void((
            controller.applyMultStatBonuses(target, {BaseStats.DEF: 0.85}),
            controller.logMessage(MessageType.EFFECT,
                                  f"{target.shortName}'s DEF was reduced!")
         )) if attackInfo.attackHit else None
    )], 0)])

def confrontationFn(controller, user, target, revert):
    amount = 1.1
    if revert: # check if was initially at range 0
        if controller.combatStateMap[user].getStack(EffectStacks.CONFRONTATION_BONUS) == 0:
            return
        controller.revertMultStatBonuses(user, {BaseStats.ATK: amount, BaseStats.ACC: amount})
        controller.combatStateMap[user].setStack(EffectStacks.CONFRONTATION_BONUS, 0)
    else: # check if currently at range 0
        currentDistance = controller.checkDistance(user, target)
        if currentDistance > 0:
            return
        controller.applyMultStatBonuses(user, {BaseStats.ATK: amount, BaseStats.ACC: amount})
        controller.combatStateMap[user].setStack(EffectStacks.CONFRONTATION_BONUS, 1)
PassiveSkillData("Confrontation", AdvancedPlayerClassNames.MERCENARY, 3, True,
    "When attacking at distance 0, increase ATK and ACC by 10%.",
    {}, {}, [SkillEffect("", [EFBeforeNextAttack({}, {},
                    lambda controller, user, target, _: confrontationFn(controller, user, target, False),
                    lambda controller, user, target, _1, _2: confrontationFn(controller, user, target, True)
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
    {}, {}, [SkillEffect("", [EFOnStatsChange(frenzyFn)], None)])

ActiveToggleSkillData("Berserk", AdvancedPlayerClassNames.MERCENARY, 5, False, 10,
    "[Toggle] Decrease DEF, RES, and AVO by 50%. Increase ATK by 50% and SPD by 25%.", MAX_ACTION_TIMER / 10, {},
    {BaseStats.ATK: 1.5, BaseStats.SPD: 1.25, BaseStats.DEF: 0.5, BaseStats.RES: 0.5, BaseStats.AVO: 0.5}, [],
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
            newPower = attackInfo.damageDealt * 0.5
            counterData = CounterSkillData(True, AttackType.MELEE, 1,
                                        [SkillEffect("", [EFBeforeNextAttack({CombatStats.FIXED_ATTACK_POWER: newPower}, {}, None, None)], 0)])
            attackInfo.addBonusAttack(user, bonusTarget, counterData)
PassiveSkillData("Deadly Dance", AdvancedPlayerClassNames.MERCENARY, 7, False,
    "If your first attack of a turn hits, trigger a bonus attack based on 50% of the damage dealt against another enemy in range.",
    {}, {}, [SkillEffect("", [EFAfterNextAttack(deadlyDanceFn)], None)])

def undeterredFn(controller, user, _1, attackInfo, _2):
    if attackInfo.inRange and not attackInfo.attackHit and not attackInfo.isBonus:
        buffEffect = SkillEffect("Undeterred", [EFBeforeNextAttack({},
                                {BaseStats.ATK: 1.25, BaseStats.MAG: 1.25, BaseStats.ACC: 1.25}, None, None)], 2)
        controller.addSkillEffect(user, buffEffect)
PassiveSkillData("Undeterred", AdvancedPlayerClassNames.MERCENARY, 8, True,
    "When you miss a (non-bonus) attack, increase ATK, MAG, and ACC by 25% for your next attack.",
    {}, {}, [SkillEffect("", [EFAfterNextAttack(undeterredFn)], None)])

ActiveBuffSkillData("Heroic Legacy", AdvancedPlayerClassNames.MERCENARY, 9, True, 90,
    "[Buff] For your next 3 turns, (non-bonus) attacks are repeated as bonus attacks.", MAX_ACTION_TIMER / 10, {}, {},
    [SkillEffect("Heroic Legacy", [
        EFImmediate(lambda controller, user, _1, _2: 
            controller.logMessage(MessageType.EFFECT,
                                  f"{user.shortName}'s attacks will be repeated!")),
        EFAfterNextAttack(lambda _1, _2, _3, attackResultInfo, _4: attackResultInfo.setRepeatAttack() if not attackResultInfo.isBonus else None)
    ], 4, "Heroic Legacy wore off.")],
    0, 0, True)

# Knight

PassiveSkillData("Knight's Vitality", AdvancedPlayerClassNames.KNIGHT, 1, False,
    "Increases HP by 20% and DEF by 15%.",
    {}, {BaseStats.HP: 1.2, BaseStats.DEF: 1.15}, [])

AttackSkillData("Challenge", AdvancedPlayerClassNames.KNIGHT, 2, False, 10,
    "Attack with 1.2x ATK, generating 3x the aggro from the target.",
    True, AttackType.MELEE, 1.2, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect("", [EFBeforeNextAttack({}, {CombatStats.AGGRO_MULT: 3}, None, None)], 0)])

def chivalryUpdateFn(controller, user, oldStats, newStats, _):
    if BaseStats.DEF in oldStats:
        oldDefBonus = round(oldStats[BaseStats.DEF] * 0.4)
        newDefBonus = round(newStats[BaseStats.DEF] * 0.4)
        controller.applyFlatStatBonuses(user, {BaseStats.RES: newDefBonus - oldDefBonus})
PassiveSkillData("Chivalry", AdvancedPlayerClassNames.KNIGHT, 3, True,
    "Increases RES by 30% of your DEF.",
    {}, {}, [SkillEffect("", [
        EFImmediate(lambda controller, user, _1, _2:
                    controller.applyFlatStatBonuses(user, {BaseStats.RES: round(controller.combatStateMap[user].getTotalStatValue(BaseStats.DEF) * 0.3)})),
        EFOnStatsChange(chivalryUpdateFn)
    ], None)])

PassiveSkillData("Justified", AdvancedPlayerClassNames.KNIGHT, 4, False,
    "Restore 15% of the damage you deal as HP.",
    {}, {}, [SkillEffect("", [EFAfterNextAttack(
      lambda controller, user, _1, attackInfo, _2: void(controller.gainHealth(user, math.ceil(attackInfo.damageDealt * 0.15)))
    )], None)])

def parryFn(controller, user, attacker, isPhysical, effectResult):
    effectResult.setDamageMultiplier(0.35)
    offensiveStat = BaseStats.ATK if isPhysical else BaseStats.MAG
    parryStrength = controller.combatStateMap[attacker].getTotalStatValue(offensiveStat) * 0.5
    counterData = CounterSkillData(True, None, 1,
                                    [SkillEffect("", [EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1, BaseStats.ATK: parryStrength},
                                                                     {}, None, None)], 0)])
    effectResult.setBonusAttack(user, attacker, counterData)
ActiveSkillDataSelector("Parry", AdvancedPlayerClassNames.KNIGHT, 5, False, 25,
    "Select an attack type. If the next attack on you matches, reduce damage taken by 65% and parry based on 50% of their offensive stat.",
    "Select the attack type to parry.",
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
        controller.logMessage(MessageType.EFFECT, f"{defender.shortName} is protected by {user.shortName}'s Unified Spirits!")
        revertEffect : SkillEffect = SkillEffect("", [EFAfterNextAttack(
            lambda controller_, attacker_, defender_, _1, _2: controller_.revertFlatStatBonuses(defender, flatStatBonuses)
        )], 0, forRevert=True)
        controller.addSkillEffect(attacker, revertEffect)
PassiveSkillData("Unified Spirits", AdvancedPlayerClassNames.KNIGHT, 7, False,
    "When an ally is attacked, if their distance from the target is greater than yours, they gain 30% of your DEF/RES.",
    {}, {}, [SkillEffect("", [
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
                    [SkillEffect("", [EFBeforeNextAttack({
                        CombatStats.IGNORE_RANGE_CHECK: 1,
                        CombatStats.FIXED_ATTACK_POWER: attackResult.damageDealt * 0.7
                    }, {}, None, None)], 0)]))
    )
    followupEffect : SkillEffect = SkillEffect("", [revertEffectFn, redirectEffectFn], 0)
    controller.addSkillEffect(attacker, followupEffect)
ActiveToggleSkillData("Burden of Atlas", AdvancedPlayerClassNames.KNIGHT, 9, True, 10,
    "[Toggle] Reduces the damage all allies take by 30%, redirecting part of it to you as a bonus attack.", MAX_ACTION_TIMER / 10,
    {}, {}, [SkillEffect("", [
        EFBeforeAllyAttacked(atlasFn)
    ], None)], 0, 0, True)

# Sniper

PassiveSkillData("Sniper's Aim", AdvancedPlayerClassNames.SNIPER, 1, False,
    "Increases ACC by 25% and SPD by 10%.",
    {}, {BaseStats.ACC: 1.25, BaseStats.SPD: 1.10}, [])

AttackSkillData("Target Lock", AdvancedPlayerClassNames.SNIPER, 2, False, 10,
    "Attack with 1x ATK, attempting to inflict TARGET for 4 turns. (Attacks against a TARGETED opponent always hit.)",
    True, AttackType.RANGED, 1, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect("", [
        EFAfterNextAttack(lambda controller, user, target, attackResult, _: void(
                        controller.applyStatusCondition(target, TargetStatusEffect(user, target, 4)) if attackResult.attackHit else None))
    ], 0)])

PassiveSkillData("Steady Hand", AdvancedPlayerClassNames.SNIPER, 3, True,
    "Gain 5% ATK and MAG at the end of every turn, up to a maximum of 50%. This bonus resets if you reposition.",
    {}, {}, [SkillEffect("", [
        EFImmediate(lambda controller, user, _1, _2: void((
            controller.combatStateMap[user].setStack(EffectStacks.STEADY_HAND, 0),
        ))),
        EFEndTurn(lambda controller, user, skipDurationTick, _2: void((
            controller.logMessage(MessageType.EFFECT, f"{user.shortName}'s ATK and MAG are increased by Steady Hand!")
                if controller.combatStateMap[user].getStack(EffectStacks.STEADY_HAND) < 10 else None,
            controller.revertMultStatBonuses(user, {
                BaseStats.ATK: 1 + (controller.combatStateMap[user].getStack(EffectStacks.STEADY_HAND) * 0.05),
                BaseStats.MAG: 1 + (controller.combatStateMap[user].getStack(EffectStacks.STEADY_HAND) * 0.05)
                }),
            controller.combatStateMap[user].addStack(EffectStacks.STEADY_HAND, 10),
            controller.applyMultStatBonuses(user, {
                BaseStats.ATK: 1 + (controller.combatStateMap[user].getStack(EffectStacks.STEADY_HAND) * 0.05),
                BaseStats.MAG: 1 + (controller.combatStateMap[user].getStack(EffectStacks.STEADY_HAND) * 0.05)
                })
        )) if not skipDurationTick else None),
        EFOnDistanceChange(lambda controller, user, _1, userMoved, oldDist, newDist, _3: void((
            controller.revertMultStatBonuses(user, {
                BaseStats.ATK: 1 + (controller.combatStateMap[user].getStack(EffectStacks.STEADY_HAND) * 0.05),
                BaseStats.MAG: 1 + (controller.combatStateMap[user].getStack(EffectStacks.STEADY_HAND) * 0.05)
                }),
            controller.combatStateMap[user].setStack(EffectStacks.STEADY_HAND, 0),
            controller.logMessage(MessageType.EFFECT,
                                  f"{user.shortName}'s Steady Hand ATK/MAG bonus is reset.")
        )) if userMoved and oldDist != newDist else None)
    ], None)])

PassiveSkillData("Suppressive Fire", AdvancedPlayerClassNames.SNIPER, 4, False,
    "Apply a debuff stack when hitting an opponent, up to 10 stacks. Each stack reduces SPD and AVO by 6%.",
    {}, {}, [SkillEffect("", [
        EFAfterNextAttack(lambda controller, _1, target, attackResult, _2: void((
            controller.logMessage(MessageType.EFFECT, f"{target.shortName}'s SPD and AVO are lowered by Suppressive Fire!")
                if controller.combatStateMap[target].getStack(EffectStacks.SUPPRESSIVE_FIRE) < 10 else None,
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
    True, AttackType.RANGED, 1, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect("", [
        EFBeforeNextAttack({}, {},
                           lambda controller, user, target, _: void((
                                controller.combatStateMap[user].setStack(EffectStacks.SAVED_DISTANCE, controller.checkDistanceStrict(user, target)),
                                controller.applyMultStatBonuses(user, {
                                    BaseStats.ATK: 1 + (controller.combatStateMap[user].getStack(EffectStacks.SAVED_DISTANCE) * 0.4)
                                })
                           )),
                           lambda controller, user, _1, _2, _3:
                                controller.revertMultStatBonuses(user, {
                                    BaseStats.ATK: 1 + (controller.combatStateMap[user].getStack(EffectStacks.SAVED_DISTANCE) * 0.4)
                                })
    )], 0)])

PassiveSkillData("Precision", AdvancedPlayerClassNames.SNIPER, 6, True,
    "Increases ACC by 15% and SPD by 10%.",
    {}, {BaseStats.ACC: 1.15, BaseStats.SPD: 1.10}, [])

PassiveSkillData("Clarity", AdvancedPlayerClassNames.SNIPER, 7, False,
    "Increases Critical Hit rate by 10% per distance from your target.",
    {}, {}, [SkillEffect("", [
        EFBeforeNextAttack({}, {},
                           lambda controller, user, target, _: void((
                                controller.combatStateMap[user].setStack(EffectStacks.SAVED_DISTANCE, controller.checkDistanceStrict(user, target)),
                                controller.applyFlatStatBonuses(user, {
                                    CombatStats.CRIT_RATE: controller.combatStateMap[user].getStack(EffectStacks.SAVED_DISTANCE) * 0.1
                                })
                           )),
                           lambda controller, user, _1, _2, _3:
                                controller.revertFlatStatBonuses(user, {
                                    CombatStats.CRIT_RATE: controller.combatStateMap[user].getStack(EffectStacks.SAVED_DISTANCE) * 0.1
                                })
    )], None)])

PassiveSkillData("Nimble Feet", AdvancedPlayerClassNames.SNIPER, 8, True,
    "Decreases the time until your next action when repositioning.",
    {}, {CombatStats.REPOSITION_ACTION_TIME_MULT: 0.7}, [])

AttackSkillData("Winds of Solitude", AdvancedPlayerClassNames.SNIPER, 9, False, 25,
    "Attack with 1x ATK; on hit, increase distance to the target by 1 and attempt to inflict RESTRICT for 2 turns. (RESTRICTED opponents cannot reposition.)",
    True, None, 1, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect("", [
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
    "Select a status effect. Attack with 0.8x ATK, attempting to inflict the selected status condition.",
    "__POISON__: The opponent takes damage at the end of their turn, based on your ATK when inflicting POISON. Duration: 6 Turns\n"
    "__BLIND__: The opponent's accuracy is reduced as if their distance from you is increased by 1. Duration: 4 Turns\n"
    "__STUN__: The opponent's turn is skipped. Duration: 2 Turns",
    DEFAULT_ATTACK_TIMER_USAGE, 1, True,
    lambda statusString: AttackSkillData(f"Laced Ammunition ({statusString[0] + statusString[1:].lower()})",
                                         AdvancedPlayerClassNames.HUNTER, 2, False, 20, "",
    True, AttackType.RANGED, 0.7, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect("", [
        EFAfterNextAttack(lambda controller, user, target, attackResult, _: void(
                        controller.applyStatusCondition(target, lacedStatus(statusString, controller, user, target)) if attackResult.attackHit else None))
    ], 0)], False), ["POISON", "BLIND", "STUN"])

PassiveSkillData("Camouflage", AdvancedPlayerClassNames.HUNTER, 3, True,
    "Decrease aggro generated from attacks by 20% per distance from your target.",
    {}, {}, [SkillEffect("", [
        EFBeforeNextAttack({}, {},
                           lambda controller, user, target, _: void((
                                controller.combatStateMap[user].setStack(EffectStacks.CAMOUFLAGE_DISTANCE, controller.checkDistanceStrict(user, target)),
                                controller.applyMultStatBonuses(user, {
                                    CombatStats.AGGRO_MULT: 1 - (controller.combatStateMap[user].getStack(EffectStacks.CAMOUFLAGE_DISTANCE) * 0.2)
                                })
                           )),
                           lambda controller, user, _1, _2, _3:
                                controller.revertMultStatBonuses(user, {
                                    CombatStats.AGGRO_MULT: 1 - (controller.combatStateMap[user].getStack(EffectStacks.CAMOUFLAGE_DISTANCE) * 0.2)
                                })
    )], None)])

def coveredTracksFn(controller : CombatController, user : CombatEntity, target : CombatEntity, userMoved : bool,
                    oldDistance : int, newDistance : int, effectResult : EffectFunctionResult):
    if not userMoved and newDistance < oldDistance:
        counterData = CounterSkillData(True, None, 0.7,
                                       [SkillEffect("", [
                                           EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1}, {}, None, None),
                                           EFAfterNextAttack(lambda controller, user, target, attackResult, _: void(
                        controller.applyStatusCondition(target, ExhaustionStatusEffect(user, target, 3, 1.3)) if attackResult.attackHit else None))
                                        ], 0)])
        effectResult.setBonusAttack(user, target, counterData)
PassiveSkillData("Covered Tracks", AdvancedPlayerClassNames.HUNTER, 4, False,
    "When an opponent approaches you, counter with 0.7x ATK, attempting to inflict EXHAUST (30% strength) for 3 turns.",
    {}, {}, [SkillEffect("", [EFOnDistanceChange(coveredTracksFn)], None)])

ActiveBuffSkillData("Weakening Trap", AdvancedPlayerClassNames.HUNTER, 5, False, 25,
    "[Buff] Target any ally. For their next three turns, attacks hitting them lower the attacker's DEF, RES, ACC, and AVO by 7%.",
    DEFAULT_ATTACK_TIMER_USAGE / 2, {}, {},
    [SkillEffect("", [EFImmediate(lambda controller, user, targets, _: void((
        controller.addSkillEffect(targets[0], SkillEffect("Weakening Trap Set", [
            EFWhenAttacked(lambda controller, user, attacker, attackInfo, _: void((
                controller.applyMultStatBonuses(attacker, {
                    BaseStats.DEF: 0.93,
                    BaseStats.RES: 0.93,
                    BaseStats.ACC: 0.93,
                    BaseStats.AVO: 0.93
                }),
                controller.logMessage(MessageType.EFFECT,
                                    f"{attacker.shortName}'s DEF, RES, ACC, and AVO are lowered by {user.shortName}'s Weakening Trap!")
            )) if attackInfo.attackHit else None)
        ], 3, "Weakening Trap wore off.")),
        controller.logMessage(MessageType.EFFECT,
                                f"{user.shortName} set a Weakening Trap for enemies attacking {targets[0].shortName}!")
    )))], 0)],
    1, 0, False)

PassiveSkillData("Resourcefulness", AdvancedPlayerClassNames.HUNTER, 6, True,
    "Increases MP by 10%, DEF by 5%, RES by 5%, and ACC by 5%.",
    {}, {BaseStats.MP: 1.1, BaseStats.DEF: 1.05, BaseStats.RES: 1.05, BaseStats.ACC: 1.05}, [])

PassiveSkillData("Primal Fear", AdvancedPlayerClassNames.HUNTER, 7, False,
    "When successfully applying a status condition, additionally attempt to inflict FEAR (10% strength) for 4 turns.",
    {}, {}, [SkillEffect("", [EFOnStatusApplied(
        lambda controller, user, target, statusName, _:
            void(controller.applyStatusCondition(target, FearStatusEffect(user, target, 4, 0.9))) if statusName != StatusConditionNames.FEAR else None
    )], None)])

PassiveSkillData("Viral Evolution", AdvancedPlayerClassNames.HUNTER, 8, True,
    "Increases the success rate of applying status conditions by 40%.",
    {}, {CombatStats.STATUS_APPLICATION_TOLERANCE_MULTIPLIER: 0.6}, [])

AttackSkillData("Enclosing Fangs", AdvancedPlayerClassNames.HUNTER, 9, True, 25,
    "Attack with 1.2x ATK. On hit, decrease all of the target's current status condition tolerances by 20% of the damage dealt.",
    True, None, 1.2, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect("", [
        EFAfterNextAttack(lambda controller, user, target, attackResult, _: void((
            [controller.combatStateMap[target].reduceTolerance(status, math.ceil(attackResult.damageDealt * 0.2)) for status in StatusConditionNames],
            controller.logMessage(MessageType.EFFECT,
                                  f"{target.shortName}'s tolerances were lowered by {math.ceil(attackResult.damageDealt * 0.2)}!")
        )) if attackResult.attackHit else None)
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
    [SkillEffect("Shadowing", [
        EFImmediate(shadowingMovementFn),
        EFBeforeNextAttack({}, {}, 
                           lambda controller, user, _1, _2: void((
                               controller.applyMultStatBonuses(
                                   user, {BaseStats.ATK: 1 + (controller.combatStateMap[user].getStack(EffectStacks.SHADOWING) * 0.15)}),
                                controller.logMessage(MessageType.EFFECT,
                                  f"{user.shortName}'s ATK increased due to Shadowing from distance {controller.combatStateMap[user].getStack(EffectStacks.SHADOWING)}!")
                                    if controller.combatStateMap[user].getStack(EffectStacks.SHADOWING) > 0 else None
                                )),
                           lambda controller, user, _1, _2, _3: controller.revertMultStatBonuses(user,
                                {BaseStats.ATK: 1 + (controller.combatStateMap[user].getStack(EffectStacks.SHADOWING) * 0.15)})
                                )], 2)],
    1, 0, True)

PassiveSkillData("Vital Strike", AdvancedPlayerClassNames.ASSASSIN, 3, True,
    "Increases Critical Hit rate by 5% and Critical Hit damage by 30%.",
    {CombatStats.CRIT_RATE: 0.05, CombatStats.CRIT_DAMAGE: 0.3}, {}, [])

PassiveSkillData("Eyes of the Dark", AdvancedPlayerClassNames.ASSASSIN, 4, False,
    "Apply a debuff stack when hitting an opponent, up to 10 stacks. Each stack reduces AVO by 3% and DEF/RES by 2%.",
    {}, {}, [SkillEffect("", [
        EFAfterNextAttack(lambda controller, _1, target, attackResult, _2: void((
            controller.logMessage(MessageType.EFFECT, f"{target.shortName}'s DEF, RES, and AVO are lowered by Eyes of the Dark!")
                if controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) < 10 else None,
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
    "INTERROGATE": SkillEffect("", [
        EFBeforeNextAttack({}, {BaseStats.ATK: 0.5}, None, None),
        EFAfterNextAttack(lambda controller, user, target, attackResult, _: void((
                controller.logMessage(MessageType.EFFECT, f"{target.shortName}'s Eyes of the Dark stacks were consumed to increase {user.shortName}'s ATK, ACC, and SPD!")
                    if controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) > 0 else None,
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
    "DISABLE": SkillEffect("", [
        EFBeforeNextAttack({}, {BaseStats.ATK: 0.8}, None, None),
        EFAfterNextAttack(lambda controller, _1, target, attackResult, _2: void((
                controller.logMessage(MessageType.EFFECT, f"{target.shortName}'s Eyes of the Dark stacks were consumed to decrease their ATK, DEF, MAG, and RES!")
                    if controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) > 0 else None,
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
    "EXECUTE": SkillEffect("", [
        EFBeforeNextAttack({}, {},
            lambda controller, user, target, _:  void((
                controller.applyFlatStatBonuses(user, {
                    CombatStats.CRIT_RATE: controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) * 0.1
                }),
                controller.applyMultStatBonuses(user, {
                    BaseStats.ATK: 0.7 + (controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK) * 0.2)
                }),
                controller.combatStateMap[user].setStack(EffectStacks.EOTD_CONSUMED, controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK)),
                controller.logMessage(MessageType.EFFECT, f"{target.shortName}'s Eyes of the Dark stacks were consumed to enhance the attack!")
                    if controller.combatStateMap[target].getStack(EffectStacks.EOTD_CONSUMED) > 0 else None,
            )),
            lambda controller, user, target, attackResult, _2: void((
                controller.revertFlatStatBonuses(user, {
                    CombatStats.CRIT_RATE: controller.combatStateMap[user].getStack(EffectStacks.EOTD_CONSUMED) * 0.1
                }),
                controller.revertMultStatBonuses(user, {
                    BaseStats.ATK: 0.7 + (controller.combatStateMap[user].getStack(EffectStacks.EOTD_CONSUMED) * 0.2)
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
ActiveSkillDataSelector("Ambush", AdvancedPlayerClassNames.ASSASSIN, 5, False, 30,
    "Select an effect and attack a target, removing all Eyes of the Dark stacks on hit.",
    "__INTERROGATE__: Attack with 0.5x ATK. Per stack removed, +4% ATK/SPD and +8% ACC.\n" +
    "__DISABLE__: Attack with 0.8x ATK. Per stack removed, opponent ATK/DEF/MAG/RES - 3.5%.\n" +
    "__EXECUTE__: Attack with 0.7x ATK, +0.2x per stack removed. Additional 10% Critical Hit rate per stack removed.",
    DEFAULT_ATTACK_TIMER_USAGE, 1, True,
    lambda ambushString: AttackSkillData(f"Ambush ({ambushString[0] + ambushString[1:].lower()})",
                                         AdvancedPlayerClassNames.ASSASSIN, 5, False, 30, "",
    True, None, 0.7, DEFAULT_ATTACK_TIMER_USAGE, [ambushSkillEffects[ambushString]], False), ["INTERROGATE", "DISABLE", "EXECUTE"])

PassiveSkillData("Relentlessness", AdvancedPlayerClassNames.ASSASSIN, 6, True,
    "Increases SPD by 15%, ATK by 5%, and ACC by 5%.",
    {}, {BaseStats.SPD: 1.15, BaseStats.ATK: 1.05, BaseStats.ACC: 1.05}, [])

PassiveSkillData("Opportunism", AdvancedPlayerClassNames.ASSASSIN, 7, False,
    "Your attacks always calculate damage against the opponent's lower defensive stat (DEF or RES).",
    {CombatStats.OPPORTUNISM: 1}, {}, [])

PassiveSkillData("Unrelenting Assault", AdvancedPlayerClassNames.ASSASSIN, 8, True,
    "After each attack, +20% ATK/MAG. Resets when an enemy takes a turn.",
    {}, {}, [SkillEffect("", [
        EFBeforeNextAttack({}, {}, 
            lambda controller, user, _1, _2:
                controller.logMessage(MessageType.EFFECT, f"{user.shortName}'s ATK/MAG were increased by Unrelenting Assault!")
                    if controller.combatStateMap[user].getStack(EffectStacks.UNRELENTING_ASSAULT) > 0 else None,
            None),
        EFAfterNextAttack(
            lambda controller, user, _, attackResult, _2: void((
                controller.revertMultStatBonuses(user, {
                    BaseStats.ATK: 1 + (controller.combatStateMap[user].getStack(EffectStacks.UNRELENTING_ASSAULT) * 0.2),
                    BaseStats.MAG: 1 + (controller.combatStateMap[user].getStack(EffectStacks.UNRELENTING_ASSAULT) * 0.2)
                }),
                controller.combatStateMap[user].addStack(EffectStacks.UNRELENTING_ASSAULT, None),
                controller.applyMultStatBonuses(user, {
                    BaseStats.ATK: 1 + (controller.combatStateMap[user].getStack(EffectStacks.UNRELENTING_ASSAULT) * 0.2),
                    BaseStats.MAG: 1 + (controller.combatStateMap[user].getStack(EffectStacks.UNRELENTING_ASSAULT) * 0.2)
                })
            )) if not attackResult.isBonus else None
        ),
        EFOnAdvanceTurn(
            lambda controller, user, _1, nextPlayer, _2: void((
                controller.logMessage(MessageType.EFFECT, f"{user.shortName}'s Unrelenting Assault ends.")
                    if controller.combatStateMap[user].getStack(EffectStacks.UNRELENTING_ASSAULT) > 1 else None,
                controller.revertMultStatBonuses(user, {
                    BaseStats.ATK: 1 + (controller.combatStateMap[user].getStack(EffectStacks.UNRELENTING_ASSAULT) * 0.2),
                    BaseStats.MAG: 1 + (controller.combatStateMap[user].getStack(EffectStacks.UNRELENTING_ASSAULT) * 0.2)
                }),
                controller.combatStateMap[user].setStack(EffectStacks.UNRELENTING_ASSAULT, 0)
            )) if nextPlayer not in controller.getTeammates(user) and controller.combatStateMap[user].getStack(EffectStacks.UNRELENTING_ASSAULT) > 0 else None
        )
    ], None)])

ActiveBuffSkillData("Instantaneous Eternity", AdvancedPlayerClassNames.ASSASSIN, 9, True, 90,
    "Take three turns in a row. (You cannot gain any MP during the first two.)", 0, {}, {}, [SkillEffect("Instantaneous Eternity", [
        EFImmediate(
            lambda controller, user, _1, _2: void((
                controller.applyFlatStatBonuses(user, {CombatStats.INSTANTANEOUS_ETERNITY: 1}),
                controller.logMessage(MessageType.EFFECT,
                                    f"{user.shortName} stops time!")
            ))
        ),
        EFStartTurn(
            lambda controller, user, _: controller.applyFlatStatBonuses(user, {CombatStats.INSTANTANEOUS_ETERNITY: 1})
        ),
        EFEndTurn(
            lambda controller, user, _1, _2: controller.revertFlatStatBonuses(user, {CombatStats.INSTANTANEOUS_ETERNITY: 1})
        )
    ], 3, "Instantaneous Eternity wears off.")], 0, 0, True)


# Acrobat

PassiveSkillData("Acrobat's Flexibility", AdvancedPlayerClassNames.ACROBAT, 1, False,
    "Increases AVO by 25% and SPD by 10%.",
    {}, {BaseStats.AVO: 1.25, BaseStats.SPD: 1.1}, [])

AttackSkillData("Bedazzle", AdvancedPlayerClassNames.ACROBAT, 2, False, 15,
    "Attack with 1x ATK, attempting to inflict BLIND for 3 turns. (BLINDED opponents calculate accuracy as if their distance is 1 greater.)",
    True, None, 1, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect("", [
        EFAfterNextAttack(lambda controller, user, target, attackResult, _: void(
                        controller.applyStatusCondition(target, BlindStatusEffect(user, target, 3)) if attackResult.attackHit else None))
    ], 0)])

PassiveSkillData("Mockery", AdvancedPlayerClassNames.ACROBAT, 3, True,
    "All attacks generate 30% more aggro.",
    {}, {CombatStats.AGGRO_MULT: 1.3}, [])

PassiveSkillData("Ride the Wake", AdvancedPlayerClassNames.ACROBAT, 4, False,
    "When dodging an enemy in range, gain 6% ATK/ACC.",
    {}, {}, [SkillEffect("", [EFWhenAttacked(lambda controller, user, _1, attackResult, _2: void((
            controller.applyMultStatBonuses(user, {
                BaseStats.ATK: 1.06,
                BaseStats.ACC: 1.06
            }),
            controller.logMessage(MessageType.EFFECT,
                                  f"{user.shortName}'s ATK and ACC are increased by Ride the Wake!")
        )) if attackResult.inRange and not attackResult.attackHit else None
    )], None)])

def sidestepFn(controller : CombatController, user : CombatEntity, _2, _3, effectResult : EffectFunctionResult):
    controller.increaseActionTimer(user, 0.85)
    effectResult.setGuaranteeDodge(True)
ActiveSkillDataSelector("Sidestep", AdvancedPlayerClassNames.ACROBAT, 5, False, 25,
    "Select an attack type. If the next attack on you matches, evade it and reduce the time to your next action.",
    "Select an attack type to react to.",
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
        controller.logMessage(MessageType.EFFECT,
                                f"{user.shortName}'s Earned Confidence is restored! Their ATK, MAG, ACC, AVO, and SPD increase.")
        controller.applyMultStatBonuses(user, {
                BaseStats.ATK: 1.25,
                BaseStats.MAG: 1.25,
                BaseStats.SPD: 1.25,
                BaseStats.ACC: 1.25,
                BaseStats.AVO: 1.25
        })
    elif originalFull and not newFull:
        controller.logMessage(MessageType.EFFECT,
                                f"{user.shortName}'s Earned Confidence is broken! Their ATK, MAG, ACC, AVO, and SPD decrease.")
        controller.revertMultStatBonuses(user, {
                BaseStats.ATK: 1.25,
                BaseStats.MAG: 1.25,
                BaseStats.SPD: 1.25,
                BaseStats.ACC: 1.25,
                BaseStats.AVO: 1.25
        })
PassiveSkillData("Earned Confidence", AdvancedPlayerClassNames.ACROBAT, 8, True,
    "At full health, +25% ATK/MAG/SPD/ACC/AVO.",
    {}, {}, [SkillEffect("", [
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
    "For 6 turns, increase AVO by 20% and SPD by 7.5%, but decrease DEF/RES by 25%. This can be used up to 3 times simultaneously for greater effect.",
    "Select how many times you'd like to use this effect at once.",
    MAX_ACTION_TIMER / 10, 0, True,
    lambda amount: ActiveBuffSkillData(f"Insidious Killer x{amount}",
                                         AdvancedPlayerClassNames.ACROBAT, 9, True, 15 * int(amount), "",
    MAX_ACTION_TIMER / 10, {}, {}, [SkillEffect("", [
        EFImmediate(lambda controller, user, _1, _2: void((
            controller.applyMultStatBonuses(user, {
                BaseStats.DEF: 1 - (0.25 * int(amount)),
                BaseStats.RES: 1 - (0.25 * int(amount)),
                BaseStats.AVO: 1 + (0.2 * int(amount)),
                BaseStats.SPD: 1 + (0.075 * int(amount)),
            }),
            controller.logMessage(MessageType.EFFECT,
                                  f"{user.shortName}'s DEF and RES decrease, but their AVO and SPD increase!")
        )))
    ], 6, "Insidious Killer wore off.", [
        EFImmediate(lambda controller, user, _1, _2:
            controller.revertMultStatBonuses(user, {
                BaseStats.DEF: 1 - (0.25 * int(amount)),
                BaseStats.RES: 1 - (0.25 * int(amount)),
                BaseStats.AVO: 1 + (0.2 * int(amount)),
                BaseStats.SPD: 1 + (0.075 * int(amount)),
            })
        )
    ])], 0, 0, True, False), ["1", "2", "3"])


# Wizard

PassiveSkillData("Wizard's Wisdom", AdvancedPlayerClassNames.WIZARD, 1, False,
    "Increases MAG by 15% and ACC by 10%.",
    {}, {BaseStats.MAG: 1.15, BaseStats.ACC: 1.1}, [])

natureBlessingEnchantments = {
    "FIRE": EnchantmentSkillEffect("Nature's Blessing (Fire)", MagicalAttackAttribute.FIRE, False, {}, {}, [
        EFBeforeNextAttack({}, {}, 
            lambda controller, user, _1, _2: void((
                controller.combatStateMap[user].setStack(
                    EffectStacks.FIRE_BLESSING, controller.combatStateMap[user].getTotalStatValue(BaseStats.ATK)),
                controller.applyFlatStatBonuses(
                    user, {BaseStats.MAG: round(controller.combatStateMap[user].getStack(EffectStacks.FIRE_BLESSING) * 0.5)})
            )),
            lambda controller, user, _1, _2, _3: void((
                controller.revertFlatStatBonuses(
                    user, {BaseStats.MAG: round(controller.combatStateMap[user].getStack(EffectStacks.FIRE_BLESSING) * 0.5)}),
                controller.combatStateMap[user].setStack(
                    EffectStacks.FIRE_BLESSING, 0)
            ))),
        EFAfterNextAttack(lambda controller, user, target, attackResult, _: void(
            controller.applyStatusCondition(
                target, BurnStatusEffect(user, target, 3, math.ceil(controller.combatStateMap[user].getTotalStatValue(BaseStats.MAG) * 0.25))
                ) if attackResult.attackHit else None))
    ], 8),
    "ICE": EnchantmentSkillEffect("Nature's Blessing (Ice)", MagicalAttackAttribute.ICE, False, {CombatStats.CRIT_RATE: 0.1}, {}, [
        EFAfterNextAttack(lambda controller, user, target, attackResult, _: void((
                controller.applyMultStatBonuses(target, {
                    BaseStats.SPD: 0.925,
                    BaseStats.AVO: 0.925
                }),
                controller.logMessage(MessageType.EFFECT,
                                    f"{target.shortName}'s SPD and AVO are lowered by {user.shortName}'s Ice enchantment!")
            )) if attackResult.attackHit and attackResult.isCritical else None),
    ], 8),
    "WIND": EnchantmentSkillEffect("Nature's Blessing (Wind)", MagicalAttackAttribute.WIND, False, {
        CombatStats.RANGE: 1
    }, {
        CombatStats.ACTION_GAUGE_USAGE_MULTIPLIER: 0.65
    }, [], 8)
}
natureBlessingMessage = {
    "FIRE": "{}'s attacks are Enchanted with Fire! When attacking, their MAG will be increased. Their attacks will attempt to inflict BURN.",
    "ICE": "{}'s attacks are Enchanted with Ice! Their Critical Hit rate increases, and Critical Hits will lower targets' DEF and RES.",
    "WIND": "{}'s attacks are Enchanted with Wind! Their Range increases, and the time between their actions decreases."
}
ActiveSkillDataSelector("Nature's Blessing", AdvancedPlayerClassNames.WIZARD, 2, False, 30,
    "Select an attribute and target an ally; for 8 turns, their attacks will be Enchanted with that attribute.",
    "(Note: Only the latest Enchantment's effects are applied to a player.)\n"
    "__FIRE__: Increases MAG by 50% of ATK. On hit, attempts to inflict BURN (DoT based on 25% of MAG) for 3 turns.\n" +
    "__ICE__: Increases critical hit rate by 10%. On critical hit, decreases the target's SPD/AVO by 7.5%.\n" +
    "__WIND__: Increases Range by 1. Decreases the time between the ally's actions by 35%.", MAX_ACTION_TIMER / 5, 1, False,
    lambda attribute: ActiveBuffSkillData(f"Nature's Blessing ({attribute[0] + attribute[1:].lower()})",
                    AdvancedPlayerClassNames.WIZARD, 2, False, 30, "", MAX_ACTION_TIMER / 5, {}, {}, [
                        SkillEffect("", [EFImmediate(lambda controller, _1, targets, _2: void((
                            controller.logMessage(MessageType.EFFECT, natureBlessingMessage[attribute].format(targets[0].shortName)),
                            controller.addSkillEffect(
                                targets[0], natureBlessingEnchantments[attribute]
                            )
                        )))], 0)], 1, 0, False, False), ["FIRE", "ICE", "WIND"])

PassiveSkillData("Serendipity", AdvancedPlayerClassNames.WIZARD, 3, True,
    "Increases critical hit rate by 5%. On critical hit, restore additional MP equal to 5% of the damge you deal (max 30).",
    {CombatStats.CRIT_RATE: 0.05}, {}, [SkillEffect("", [EFAfterNextAttack(
        lambda controller, user, _1, attackInfo, _2:
            void(controller.gainMana(user, min(math.ceil(attackInfo.damageDealt * 0.05), 30))) if attackInfo.isCritical else None
    )], None)])

PassiveSkillData("Arcane Flow", AdvancedPlayerClassNames.WIZARD, 4, False,
    "Attacks while you have an Enchantment active on yourself have 15% increased MAG.",
    {}, {}, [SkillEffect("", [EFBeforeNextAttack({}, {},
        lambda controller, user, _1, _2: controller.applyMultStatBonuses(user, {BaseStats.MAG: 1.15})
            if len(controller.combatStateMap[user].activeEnchantments) > 0 else None,
        lambda controller, user, _1, _2, _3: controller.revertMultStatBonuses(user, {BaseStats.MAG: 1.15})
            if len(controller.combatStateMap[user].activeEnchantments) > 0 else None
    )], None)])

AttackSkillData("Magic Circle", AdvancedPlayerClassNames.WIZARD, 5, False, 30,
    "Attack with 1.2x MAG from any range. If this targets an enemy's weakness, increases to 2.5x MAG.",
    False, AttackType.MAGIC, 1.2, DEFAULT_ATTACK_TIMER_USAGE,
    [SkillEffect("", [
        EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1}, {},
        lambda controller, user, target, _: void((
                controller.applyMultStatBonuses(user, {BaseStats.MAG: 2.5 / 1.2}),
                controller.logMessage(MessageType.EFFECT,
                                    f"{user.shortName}'s Magic Circle is strengthened by targeting a weakness!")
        )) if controller.combatStateMap[user].getCurrentAttackAttribute(False) in controller.combatStateMap[target].weaknesses else None,
        lambda controller, user, target, _2, _3: controller.revertMultStatBonuses(user, {BaseStats.MAG: 2.5 / 1.2})
            if controller.combatStateMap[user].getCurrentAttackAttribute(False) in controller.combatStateMap[target].weaknesses else None,)
    ], 0)])

PassiveSkillData("Comprehension", AdvancedPlayerClassNames.WIZARD, 6, True,
    "Increases MP by 15% and MAG by 10%.",
    {}, {BaseStats.MP: 1.15, BaseStats.MAG: 1.1}, [])

def ragingManaFn(controller, user, target, attackInfo, _):
    if attackInfo.attackHit and not attackInfo.isBonus:
        otherOpponents = [opp for opp in controller.getTargets(user) if opp is not target]
        if len(otherOpponents) > 0:
            bonusTarget = controller.rng.choice(otherOpponents)
            counterData = CounterSkillData(False, AttackType.MAGIC, 0.4,
                                        [SkillEffect("", [EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1}, {}, None, None)], 0)])
            attackInfo.addBonusAttack(user, bonusTarget, counterData)
PassiveSkillData("Raging Mana", AdvancedPlayerClassNames.WIZARD, 7, False,
    "When hitting with an enchanted attack, trigger a bonus attack against a random enemy with 0.4x MAG.",
    {}, {}, [SkillEffect("", [EFAfterNextAttack(ragingManaFn)], None)])

def enlightenmentFn(controller : CombatController, user : CombatEntity, originalStats : dict[Stats, float], finalStats : dict[Stats, float], _):
    originalOver = False
    newOver = False
    threshold = 0.35
    if SpecialStats.CURRENT_MP in originalStats:
        baseMP = controller.combatStateMap[user].getTotalStatValue(BaseStats.MP)
        originalOver = originalStats[SpecialStats.CURRENT_MP] / baseMP >= threshold
        newOver = finalStats[SpecialStats.CURRENT_MP] / baseMP >= threshold
    elif BaseStats.MP in originalStats:
        currentMP = controller.getCurrentMana(user)
        originalOver =currentMP / originalStats[BaseStats.MP] >= threshold
        newOver = currentMP / finalStats[BaseStats.MP] >= threshold
    else:
        return
    
    if newOver and not originalOver:
        controller.logMessage(MessageType.EFFECT,
                            f"{user.shortName}'s Enlightenment is re-established! Their ATK, MAG, RES, and SPD increase.")
        controller.applyMultStatBonuses(user, {
                BaseStats.ATK: 1.15,
                BaseStats.MAG: 1.15,
                BaseStats.RES: 1.15,
                BaseStats.SPD: 1.15
        })
    elif originalOver and not newOver:
        controller.logMessage(MessageType.EFFECT,
                            f"{user.shortName}'s Enlightenment is disrupted! Their ATK, MAG, RES, and SPD decrease.")
        controller.revertMultStatBonuses(user, {
                BaseStats.ATK: 1.15,
                BaseStats.MAG: 1.15,
                BaseStats.RES: 1.15,
                BaseStats.SPD: 1.15
        })
PassiveSkillData("Enlightenment", AdvancedPlayerClassNames.WIZARD, 8, True,
    "As long as your MP is at least 35% full, +15% ATK/MAG/RES/SPD.",
    {}, {}, [SkillEffect("", [
        EFImmediate(lambda controller, user, _1, _2: controller.applyMultStatBonuses(user, {
                BaseStats.ATK: 1.15,
                BaseStats.MAG: 1.15,
                BaseStats.RES: 1.15,
                BaseStats.SPD: 1.15
            }) if controller.getCurrentMana(user)/controller.combatStateMap[user].getTotalStatValue(BaseStats.MP) >= 0.35 else None
        ),
        EFOnStatsChange(enlightenmentFn)
    ], None)])

ActiveToggleSkillData("Enigmatic Mind", AdvancedPlayerClassNames.WIZARD, 9, True, 10,
    "[Toggle] Attacking skills have 3x the MP cost and 2x ATK/MAG when used.", MAX_ACTION_TIMER / 10, {}, {CombatStats.ATTACK_SKILL_MANA_COST_MULT: 3},
    [SkillEffect("", [EFOnAttackSkill(
            lambda controller, user, _1, _2: void((
                controller.addSkillEffect(user, SkillEffect("", [
                    EFBeforeNextAttack({}, {
                        BaseStats.ATK: 2,
                        BaseStats.MAG: 2
                    }, None, None)
                ], 0)),
                controller.logMessage(MessageType.EFFECT,
                                    f"{user.shortName}'s Enigmatic Mind increases the skill's power!")
            ))
    )], None)], 0, 0, True)


# Saint

PassiveSkillData("Saint's Grace", AdvancedPlayerClassNames.SAINT, 1, False,
    "Increases MP by 20% and RES by 15%.",
    {}, {BaseStats.MP: 1.2, BaseStats.RES: 1.15}, [])

ActiveBuffSkillData("Restoration", AdvancedPlayerClassNames.SAINT, 2, False, 30,
    "Heal one ally, based on your MAG and RES (3x strength).", MAX_ACTION_TIMER, {}, {}, [SkillEffect("", [
        EFImmediate(
            lambda controller, user, target, _2: controller.doHealSkill(user, target[0], 3)
        )
    ], 0)], 1, 0, False)

PassiveSkillData("Resilience", AdvancedPlayerClassNames.SAINT, 3, True,
    "Increases status condition resistance by 50%.",
    {}, {CombatStats.STATUS_RESISTANCE_MULTIPLIER: 1.5}, [])

PassiveSkillData("Aura of Peace", AdvancedPlayerClassNames.SAINT, 4, False,
    "When using Restoration, all other allies are healed by 25% of the health restored.",
    {}, {}, [SkillEffect("", [
        EFOnHealSkill(
            lambda controller, user, target, amount, _: void([
                controller.gainHealth(teammate, math.ceil(amount * 0.25)) for teammate in controller.getTeammates(user) if teammate != target
            ])
        )
    ], None)])

spiritBlessingEnchantments = {
    "LIGHT": EnchantmentSkillEffect("Spirits' Blessing (Light)", MagicalAttackAttribute.LIGHT, False, {}, {
        BaseStats.DEF: 1.1,
        BaseStats.RES: 1.1,
        BaseStats.AVO: 1.1
    }, [EFAfterNextAttack(lambda controller, user, _1, attackResult, _2:
            void(controller.gainHealth(user, math.ceil(controller.getMaxHealth(user) * 0.07))) if attackResult.attackHit else None)
    ], 6),
    "DARK": EnchantmentSkillEffect("Spirits' Blessing (Dark)", MagicalAttackAttribute.DARK, False, {}, {
        BaseStats.ATK: 1.1,
        BaseStats.MAG: 1.1,
        BaseStats.ACC: 1.1
    }, [EFAfterNextAttack(lambda controller, user, _1, attackResult, _2:
            void(controller.gainMana(user, math.ceil(controller.getMaxMana(user) * 0.07))) if attackResult.attackHit else None)
    ], 6),
}
spiritBlessingMessage = {
    "LIGHT": "{}'s attacks are Enchanted with Light! Their DEF, RES, and AVO increase, and their attacks will restore HP.",
    "DARK": "{}'s attacks are Enchanted with Dark! Their ATK, MAG, and ACC increase, and their attacks will restore MP.",
}
ActiveSkillDataSelector("Spirits' Blessing", AdvancedPlayerClassNames.SAINT, 5, False, 30,
    "Select an attribute and a target ally; for 6 turns, their attacks will be Enchanted with that attribute.",
    "(Note: Only the latest enchantment's effects are applied to a player.)\n" + 
    "__LIGHT__: Increases DEF, RES, and AVO by 10%. On hit, restores 7% of the ally's max HP.\n" +
    "__DARK__: Increases ATK, MAG, and ACC by 10%. On hit, restores 7% of the ally's max MP.", MAX_ACTION_TIMER / 5, 1, False,
    lambda attribute: ActiveBuffSkillData(f"Spirits' Blessing ({attribute[0] + attribute[1:].lower()})",
                    AdvancedPlayerClassNames.SAINT, 5, False, 30, "", MAX_ACTION_TIMER / 5, {}, {}, [
                        SkillEffect("", [EFImmediate(lambda controller, _1, targets, _2: void((
                            controller.logMessage(MessageType.EFFECT, spiritBlessingMessage[attribute].format(targets[0].shortName)),
                            controller.addSkillEffect(
                                targets[0], spiritBlessingEnchantments[attribute]
                            )
                        )))], 0)], 1, 0, False, False), ["LIGHT", "DARK"])

PassiveSkillData("Faith", AdvancedPlayerClassNames.SAINT, 6, True,
    "Increases RES by 10%, MAG by 10%, and MP by 5%.",
    {}, {BaseStats.RES: 1.1, BaseStats.MAG: 1.1, BaseStats.MP: 1.05}, [])

def prayerFn(controller : CombatController, user : CombatEntity, skipDurationTick : bool, _):
    if skipDurationTick or controller.getCurrentHealth(user) <= 0:
        return
    prayerLog = False
    for ally in controller.getTeammates(user):
        for effect in controller.combatStateMap[ally].activeSkillEffects:
            if isinstance(effect, StatusEffect):
                if not prayerLog:
                    controller.logMessage(MessageType.EFFECT,
                                            f"{user.shortName}'s Prayer reduces the durations of allies' status conditions!")
                    prayerLog = True
                controller.combatStateMap[ally].activeSkillEffects[effect] += 1
        controller._cleanupEffects(ally)
PassiveSkillData("Prayer", AdvancedPlayerClassNames.SAINT, 7, False,
    "At the end of your turns, the durations of all allies' status conditions are reduced by one turn.",
    {}, {}, [SkillEffect("", [EFEndTurn(prayerFn)], None)])

PassiveSkillData("Divine Punishment", AdvancedPlayerClassNames.SAINT, 8, True,
    "When attacking an enemy, they lose MP equal to 10% of the damage dealt (max 60).",
    {}, {}, [SkillEffect("", [EFAfterNextAttack(
        lambda controller, user, target, attackInfo, _:
            void((
                controller.logMessage(MessageType.EFFECT,
                                    f"{target.shortName} loses MP due to {user.shortName}'s Divine Punishment!"),
                controller.spendMana(target, min(round(attackInfo.damageDealt * 0.1), 60))
            )) if attackInfo.attackHit and controller.getCurrentMana(target) > 0 else None
    )], None)])

AttackSkillData("Sealing Ritual", AdvancedPlayerClassNames.SAINT, 9, True, 60,
    "Attack with 1x MAG from any range, attempting to inflict STUN for 2 turns. If successful, reduces the target's DEF, RES, and AVO by 20%.",
    False, AttackType.MAGIC, 1, DEFAULT_ATTACK_TIMER_USAGE,
    [SkillEffect("", [
        EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1}, {}, None, None),
        EFAfterNextAttack(lambda controller, user, target, attackResult, _: void(
            controller.applyStatusCondition(target, StunStatusEffect(user, target, 2)) if attackResult.attackHit else None)),
        EFOnStatusApplied(
            lambda controller, _1, target, statusName, _2: void((
                controller.applyMultStatBonuses(target, {
                    BaseStats.DEF: 0.8,
                    BaseStats.RES: 0.8,
                    BaseStats.AVO: 0.8
                }),
                controller.logMessage(MessageType.EFFECT,
                                    f"{target.shortName}'s DEF, RES, and AVO are lowered by the Sealing Ritual!")
                )) if statusName == StatusConditionNames.STUN else None)
    ], 0)])


####

# Striker

BASE_STRIKER_WEAPON_STATS = {
    BaseStats.ATK: 9,
    BaseStats.ACC: 8,
    BaseStats.SPD: 9
}
def strikerWeaponStatScaler(rarity : int, rank : int) -> dict[Stats, float]:
    currentRarityMultiplier = (rarity+1) ** 2
    nextRarityMultiplier = (rarity+2) ** 2 if rarity < MAX_ITEM_RARITY else ((MAX_ITEM_RARITY+1) ** 3) / MAX_RANK_STAT_SCALING
    rankScalingRange = (nextRarityMultiplier * MAX_RANK_STAT_SCALING) - currentRarityMultiplier
    rankScalingBonus = rankScalingRange * rank / MAX_ITEM_RANK

    finalMultiplier = currentRarityMultiplier + rankScalingBonus
    return { baseStat: math.ceil(BASE_STRIKER_WEAPON_STATS[baseStat] * finalMultiplier) for baseStat in BASE_STRIKER_WEAPON_STATS }
def conditioningFn(controller : CombatController, user : CombatEntity):
    if controller.combatStateMap[user].checkWeapon() is not None:
        return None
    sampleRarity = min((user.level - 1) // 4, MAX_ITEM_RARITY)
    sampleRank = math.floor(((user.level % 4) / 3) * MAX_ITEM_RANK)
    controller.applyFlatStatBonuses(user, strikerWeaponStatScaler(sampleRarity, sampleRank))
PassiveSkillData("Striker's Conditioning", SecretPlayerClassNames.STRIKER, 1, False,
    "When no weapon is equipped, increase ATK, ACC and SPD based on player level.",
    {}, {}, [
        SkillEffect("", [
            EFImmediate(
                lambda controller, user, _1, _2: conditioningFn(controller, user)
            )
        ], None)
    ])


strikerStanceMarkMap = {
    "TIGER": EffectStacks.STRIKER_TIGER,
    "HORSE": EffectStacks.STRIKER_HORSE,
    "CRANE": EffectStacks.STRIKER_CRANE
}
strikerStanceDescMap = {
    "TIGER": "enters Tiger stance! Their SPD and AVO increase, while their ATK and ACC decrease.",
    "HORSE": "enters Horse stance! Their DEF and RES increase, while their SPD and AVO decrease.",
    "CRANE": "enters Crane stance! Their Range and ACC increase, while their DEF and RES decrease."
}
strikerHorseStackDR = 0.08
innerPeaceMap : dict[Stats, float] = {
    BaseStats.ATK: 1.1,
    BaseStats.DEF: 1.1,
    BaseStats.MAG: 1.1,
    BaseStats.RES: 1.1,
    BaseStats.ACC: 1.1,
    BaseStats.AVO: 1.1,
    BaseStats.SPD: 1.1,
}
def deactivateStanceFn(controller : CombatController, user : CombatEntity):
    stateMap = controller.combatStateMap[user]
    innerPeaceCheck = controller.combatStateMap[user].getTotalStatValue(CombatStats.INNER_PEACE) > 0
    wasInStance = False
    if stateMap.getStack(EffectStacks.STRIKER_TIGER) > 0:
        controller.revertMultStatBonuses(user, {
            BaseStats.SPD: 1.3,
            BaseStats.AVO: 1.3,
            BaseStats.ATK: 0.85,
            BaseStats.ACC: 0.85
        })
        if controller.combatStateMap[user].getTotalStatValue(CombatStats.TIGER_INSTINCT) > 0:
            controller.revertMultStatBonuses(user, {
                CombatStats.MANA_GAIN_MULT: 1.5
            })
        stateMap.setStack(EffectStacks.STRIKER_TIGER, 0)
        wasInStance = True
    if stateMap.getStack(EffectStacks.STRIKER_HORSE) > 0:
        controller.revertMultStatBonuses(user, {
            BaseStats.DEF: 1.3,
            BaseStats.RES: 1.3,
            BaseStats.SPD: 0.85,
            BaseStats.AVO: 0.85
        })
        controller.revertFlatStatBonuses(user, {
            CombatStats.DAMAGE_REDUCTION: controller.combatStateMap[user].getStack(EffectStacks.HORSE_INSTINCTS) * strikerHorseStackDR
        })
        stateMap.setStack(EffectStacks.HORSE_INSTINCTS, 0)
        stateMap.setStack(EffectStacks.STRIKER_HORSE, 0)
        wasInStance = True
    if stateMap.getStack(EffectStacks.STRIKER_CRANE) > 0:
        controller.revertFlatStatBonuses(user, {
            CombatStats.RANGE: 1
        })
        controller.revertMultStatBonuses(user, {
            BaseStats.ACC: 1.3,
            BaseStats.DEF: 0.85,
            BaseStats.RES: 0.85
        })
        stateMap.setStack(EffectStacks.STRIKER_CRANE, 0)
        wasInStance = True

    if wasInStance and innerPeaceCheck:
        controller.revertMultStatBonuses(user, innerPeaceMap)
def activateStanceFn(controller : CombatController, user : CombatEntity, stance : str):
    newStanceMark = strikerStanceMarkMap[stance]
    innerPeaceCheck = controller.combatStateMap[user].getTotalStatValue(CombatStats.INNER_PEACE) > 0
    if newStanceMark == EffectStacks.STRIKER_TIGER:
        controller.applyMultStatBonuses(user, {
            BaseStats.SPD: 1.3,
            BaseStats.AVO: 1.3,
            BaseStats.ATK: 0.85,
            BaseStats.ACC: 0.85
        })
        if controller.combatStateMap[user].getTotalStatValue(CombatStats.TIGER_INSTINCT) > 0:
            controller.applyMultStatBonuses(user, {
                CombatStats.MANA_GAIN_MULT: 1.5
            })
    elif newStanceMark == EffectStacks.STRIKER_HORSE:
        controller.applyMultStatBonuses(user, {
            BaseStats.DEF: 1.3,
            BaseStats.RES: 1.3,
            BaseStats.SPD: 0.85,
            BaseStats.AVO: 0.85
        })
    elif newStanceMark == EffectStacks.STRIKER_CRANE:
        controller.applyFlatStatBonuses(user, {
            CombatStats.RANGE: 1
        })
        controller.applyMultStatBonuses(user, {
            BaseStats.ACC: 1.3,
            BaseStats.DEF: 0.85,
            BaseStats.RES: 0.85
        })
    controller.combatStateMap[user].setStack(newStanceMark, 1)
    if innerPeaceCheck:
        controller.applyMultStatBonuses(user, innerPeaceMap)
def horseAoeFn(controller : CombatController, user : CombatEntity, target : CombatEntity, attackInfo : AttackResultInfo, _):
    otherOpponents = [opp for opp in controller.getTargets(user) if opp is not target]
    for bonusTarget in otherOpponents:
        if controller.checkInRange(user, bonusTarget):
            counterData = CounterSkillData(True, AttackType.MELEE, 0.7, [])
            attackInfo.addBonusAttack(user, bonusTarget, counterData)
formShiftAttackEffects : dict[str, list[EffectFunction]] = {
    "TIGER": [EFBeforeNextAttack({}, {BaseStats.ATK: 1.3}, None, None)],
    "HORSE": [
        EFBeforeNextAttack({}, {BaseStats.ATK: 0.7}, None, None),
        EFAfterNextAttack(horseAoeFn)
    ],
    "CRANE": [EFAfterNextAttack(increaseDistanceFn)]
}
ActiveSkillDataSelector("Form Shift", SecretPlayerClassNames.STRIKER, 2, False, 20,
    "Select a stance you are not currently in; perform an attack, then shift into that stance.",
    "__TIGER__: Attack with 1.3x attack. Stance Effect: +30% SPD, +30% AVO; -15% ATK, -15% ACC \n"
    "__HORSE__: Attack all enemies in range for 0.7x ATK. Stance Effect: +30% DEF, +30% RES, -15% SPD, -15% AVO \n"
    "__CRANE__: Attack with 1x ATK, then increase distance to target 1. Stance Effect: +1 Range, +30% ACC; -15% DEF, -15% RES",
    DEFAULT_ATTACK_TIMER_USAGE, 1, True,
    lambda stance: AttackSkillData(
        f"Form Shift: {stance[0] + stance[1:].lower()} Stance", SecretPlayerClassNames.STRIKER, 2, False, 20, "",
        True, AttackType.MELEE, 1, DEFAULT_ATTACK_TIMER_USAGE, [
            SkillEffect("", formShiftAttackEffects[stance] + [
                EFAfterNextAttack(
                    lambda controller, user, _1, _2, _3: void((
                        deactivateStanceFn(controller, user),
                        activateStanceFn(controller, user, stance),
                        controller.logMessage(MessageType.EFFECT,
                                            f"{user.shortName} {strikerStanceDescMap[stance]}")
                    ))
                )
            ], 0)
        ], False),
    ["TIGER", "HORSE", "CRANE"],
    optionChecker = lambda stance, controller, user:
        controller.combatStateMap[user].getStack(strikerStanceMarkMap[stance]) == 0)


def decreaseDistanceFn(controller : CombatController, user : CombatEntity, target : CombatEntity, _1, result : EffectFunctionResult):
    currentDistance = controller.checkDistance(user, target)
    if currentDistance is not None:
        reactionAttackData = controller.updateDistance(user, target, currentDistance - 1)
        [result.setBonusAttack(*reactionAttack) for reactionAttack in reactionAttackData]
PassiveSkillData("Like A Butterfly", SecretPlayerClassNames.STRIKER, 3, True,
    "If attacking from out of range, decrease your distance to the target by 1 before attacking (slightly increasing the time until your next action).",
    {}, {}, [SkillEffect("", [EFBeforeNextAttack(
        {}, {},
        lambda controller, user, target, result: void((
            decreaseDistanceFn(controller, user, target, None, result),
            controller.spendActionTimer(user, DEFAULT_APPROACH_TIMER_USAGE * 0.3)
        )) if not controller.checkInRange(user, target) else None,
        None
    )], None)])

def tigerDodgeFn(controller : CombatController, user, attacker, attackInfo, _2):
    if controller.combatStateMap[user].getStack(EffectStacks.STRIKER_TIGER) == 0:
        return
    if attackInfo.inRange and not attackInfo.attackHit:
        controller.combatStateMap[user].setStack(EffectStacks.TIGER_BONUS, 1)
        controller.increaseActionTimer(user, 0.35)
def horseStackFn(controller : CombatController, user, attacker, attackInfo, _2):
    if controller.combatStateMap[user].getStack(EffectStacks.STRIKER_HORSE) == 0:
        return
    if attackInfo.attackHit and controller.combatStateMap[user].getStack(EffectStacks.HORSE_INSTINCTS) < 6:
        controller.revertFlatStatBonuses(user, {
            CombatStats.DAMAGE_REDUCTION: controller.combatStateMap[user].getStack(EffectStacks.HORSE_INSTINCTS) * strikerHorseStackDR
        })
        controller.combatStateMap[user].addStack(EffectStacks.HORSE_INSTINCTS, 6)
        controller.applyFlatStatBonuses(user, {
            CombatStats.DAMAGE_REDUCTION: controller.combatStateMap[user].getStack(EffectStacks.HORSE_INSTINCTS) * strikerHorseStackDR
        })
        controller.logMessage(MessageType.EFFECT, f"{user.shortName}'s guard tightens!")
def craneApplyFn(controller : CombatController, user : CombatEntity, target : CombatEntity, _):
    if controller.combatStateMap[user].getStack(EffectStacks.STRIKER_CRANE) == 0:
        return
    if controller.checkDistanceStrict(user, target) > 0:
        controller.combatStateMap[user].setStack(EffectStacks.CRANE_BONUS, 1)
        controller.applyFlatStatBonuses(user, {
            CombatStats.CRIT_RATE: 0.35,
            CombatStats.CRIT_DAMAGE: 0.15
        })
def craneRevertFn(controller : CombatController, user : CombatEntity, target : CombatEntity, _1, _2):
    if controller.combatStateMap[user].getStack(EffectStacks.CRANE_BONUS) == 1:
        controller.combatStateMap[user].setStack(EffectStacks.CRANE_BONUS, 0)
        controller.revertFlatStatBonuses(user, {
            CombatStats.CRIT_RATE: 0.35,
            CombatStats.CRIT_DAMAGE: 0.15
        })
PassiveSkillData("Awakened Instincts", SecretPlayerClassNames.STRIKER, 4, False,
    "In __Tiger Stance__: +50% MP Restoration. Reduce time to next action after dodging. " +
    "In __Horse Stance__: When you are hit, gain stacking buff increasing Damage Reduction by 8%, up to 6 stacks. " +
    "In __Crane Stance__: Increase Critical Hit Rate by 35% and Critical Damage by 15% when attacking at Distance 0 or greater.",
    {CombatStats.TIGER_INSTINCT: 1}, {}, [
        SkillEffect("", [
            EFWhenAttacked(tigerDodgeFn),
            EFWhenAttacked(horseStackFn),
            EFBeforeNextAttack({}, {}, craneApplyFn, craneRevertFn),
            EFEndTurn(
                lambda controller, user, skipDurationTick, _2:
                    controller.combatStateMap[user].setStack(EffectStacks.TIGER_BONUS, 0)
                    if not skipDurationTick else None
            )
        ], None)
    ])

def kiTigerApplyFn(controller : CombatController, user : CombatEntity, _1, _2):
    if controller.combatStateMap[user].getStack(EffectStacks.STRIKER_TIGER) == 0:
        return
    if controller.combatStateMap[user].getStack(EffectStacks.TIGER_BONUS) > 0:
        controller.logMessage(MessageType.EFFECT, f"{user.shortName}'s spirit burns brightly!")
        controller.applyMultStatBonuses(user, {
            BaseStats.ATK: 1.5
        })
        revertEffect = SkillEffect("", [EFAfterNextAttack(kiTigerRevertFn)], 0, forRevert=True)
        controller.addSkillEffect(user, revertEffect)
def kiTigerRevertFn(controller : CombatController, user : CombatEntity, _1, _2, result : EffectFunctionResult):
    controller.revertMultStatBonuses(user, {
        BaseStats.ATK: 1.5
    })
    result.setActionTime(DEFAULT_ATTACK_TIMER_USAGE * 0.2)

def kiHorseApplyFn(controller : CombatController, user : CombatEntity, _1, _2):
    if controller.combatStateMap[user].getStack(EffectStacks.STRIKER_HORSE) == 0:
        return
    instinctStacks = controller.combatStateMap[user].getStack(EffectStacks.HORSE_INSTINCTS)
    if instinctStacks > 0:
        controller.combatStateMap[user].setStack(EffectStacks.HORSE_BONUS, instinctStacks)
        controller.applyMultStatBonuses(user, {
            BaseStats.ATK: 1 + (0.04 * instinctStacks)
        })
        revertEffect = SkillEffect("", [EFAfterNextAttack(kiHorseRevertFn)], 0, forRevert=True)
        controller.addSkillEffect(user, revertEffect)
def kiHorseRevertFn(controller : CombatController, user : CombatEntity, target : CombatEntity, result : AttackResultInfo, _):
    instinctStacks = controller.combatStateMap[user].getStack(EffectStacks.HORSE_BONUS)
    controller.revertMultStatBonuses(user, {
            BaseStats.ATK: 1 + (0.04 * instinctStacks)
    })
    if result.attackHit and instinctStacks >= 2:
        controller.logMessage(MessageType.EFFECT, f"{user.shortName} delivers a crumpling blow!")
        controller.applyStatusCondition(target, StunStatusEffect(user, target, instinctStacks // 2))

def kiCraneApplyFn(controller : CombatController, user : CombatEntity, _1, _2):
    if controller.combatStateMap[user].getStack(EffectStacks.STRIKER_CRANE) == 0:
        return
    controller.logMessage(MessageType.EFFECT, f"{user.shortName} executes a precise strike!")
    controller.applyFlatStatBonuses(user, {
        CombatStats.CRIT_DAMAGE: 1
    })
    revertEffect = SkillEffect("", [EFAfterNextAttack(kiCraneRevertFn)], 0, forRevert=True)
    controller.addSkillEffect(user, revertEffect)
def kiCraneRevertFn(controller : CombatController, user : CombatEntity, target : CombatEntity, _, result : EffectFunctionResult):
    controller.revertFlatStatBonuses(user, {
        CombatStats.CRIT_DAMAGE: 1
    })
    decreaseDistanceFn(controller, user, target, _, result)

AttackSkillData("Ki Strike", SecretPlayerClassNames.STRIKER, 5, False, 30,
    "Attack with 1.2x ATK. If in stance, gains additional effects and exits stance. " +
    "(__Tiger__ enhanced when used after dodging, __Horse__ enhanced based on Instinct stacks, __Crane__ gains Critical Damage and approaches after)",
    True, AttackType.MELEE, 1.2, DEFAULT_ATTACK_TIMER_USAGE, [
        SkillEffect("", [
            EFBeforeNextAttack({}, {}, kiTigerApplyFn, None),
            EFBeforeNextAttack({}, {}, kiHorseApplyFn, None),
            EFBeforeNextAttack({}, {}, kiCraneApplyFn, None),

            EFAfterNextAttack(
                lambda controller, user, _1, _2, _3: void((
                    controller.logMessage(MessageType.EFFECT,
                        f"{user.shortName} returns to a neutral stance!"),
                    deactivateStanceFn(controller, user)
                )) if controller.combatStateMap[user].getStack(EffectStacks.STRIKER_TIGER) > 0
                    or controller.combatStateMap[user].getStack(EffectStacks.STRIKER_HORSE) > 0
                    or controller.combatStateMap[user].getStack(EffectStacks.STRIKER_CRANE) > 0 else None
            )
        ], 0)
    ])


staminaMaxReduction = 0.2
def staminaFn(controller, user, originalStats, finalStats, _):
    originalRatio = 1
    newRatio = 1
    if SpecialStats.CURRENT_MP in originalStats:
        baseMP = controller.combatStateMap[user].getTotalStatValue(BaseStats.MP)
        originalRatio = originalStats[SpecialStats.CURRENT_MP] / baseMP
        newRatio = finalStats[SpecialStats.CURRENT_MP] / baseMP
    elif BaseStats.MP in originalStats:
        currentMP = controller.getCurrentMana(user)
        originalRatio = currentMP / originalStats[BaseStats.MP]
        newRatio = currentMP / finalStats[BaseStats.MP]
    else:
        return
    
    oldMult = 1 - (originalRatio * staminaMaxReduction)
    newMult = 1 - (newRatio * staminaMaxReduction)
    controller.revertMultStatBonuses(user, {
        CombatStats.ACTION_GAUGE_USAGE_MULTIPLIER: oldMult
    })
    controller.applyMultStatBonuses(user, {
        CombatStats.ACTION_GAUGE_USAGE_MULTIPLIER: newMult
    })
PassiveSkillData("Stamina", SecretPlayerClassNames.STRIKER, 6, True,
    "Decreases the time between your actions by up to 20% based on your remaining MP percentage.",
    {}, {}, [SkillEffect("", [
        EFImmediate(
            lambda controller, user, _1, _2: controller.applyMultStatBonuses(user, {
                CombatStats.ACTION_GAUGE_USAGE_MULTIPLIER: 1 - staminaMaxReduction
            })
        ),
        EFOnStatsChange(staminaFn)
    ], None)])


PassiveSkillData("Inner Peace", SecretPlayerClassNames.STRIKER, 7, False,
    "While in a stance, increase all stats except HP and MP by 10%.",
    {CombatStats.INNER_PEACE: 1}, {}, [])


PassiveSkillData("Combat Aura", SecretPlayerClassNames.STRIKER, 8, True,
    "Gain 2 stacks of resistance to all Physical attack attributes.",
    {}, {}, [
        SkillEffect("", [
            EFImmediate(
                lambda controller, user, _1, _2: void((
                    controller.addResistanceStacks(user, PhysicalAttackAttribute.CRUSHING, 2),
                    controller.addResistanceStacks(user, PhysicalAttackAttribute.PIERCING, 2),
                    controller.addResistanceStacks(user, PhysicalAttackAttribute.SLASHING, 2)
            )))
        ], None)
    ])


secretArtNameMap = {
    "TIGER": "Tiger Destruction",
    "OROCHI": "Orochi Breaker",
    "HOYOKUSEN": "Hoyokusen",
    "DEMON": "Raging Demon"
}
secretArtEnchantmentMap = {
    "TIGER": [EnchantmentSkillEffect("", PhysicalAttackAttribute.SLASHING, False, {}, {}, [], 0)],
    "OROCHI": [EnchantmentSkillEffect("", PhysicalAttackAttribute.CRUSHING, False, {}, {}, [], 0)],
    "HOYOKUSEN": [EnchantmentSkillEffect("", PhysicalAttackAttribute.PIERCING, False, {}, {}, [], 0)],
    "DEMON": []
}
def secretArtApplyFn(controller : CombatController, user : CombatEntity, target : CombatEntity,
                     result : EffectFunctionResult, technique : str):
    if technique != "DEMON":
        stanceCheck = False
        statCheck = False
        hitBonus = None
        
        maxStats = set()
        maxStatVal = 0
        for stat in BaseStats:
            if stat in [BaseStats.HP, BaseStats.MP]:
                continue
            statVal = controller.combatStateMap[user].getTotalStatValue(stat)
            if statVal > maxStatVal:
                maxStatVal = statVal
                maxStats = set()
            if statVal == maxStatVal:
                maxStats.add(stat)

        if technique == "TIGER":
            stanceCheck = controller.combatStateMap[user].getStack(EffectStacks.STRIKER_TIGER) > 0
            statCheck = len(maxStats.intersection([BaseStats.SPD, BaseStats.AVO])) > 0
            hitBonus = EffectStacks.SECRET_ART_TIGER
        elif technique == "OROCHI":
            stanceCheck = controller.combatStateMap[user].getStack(EffectStacks.STRIKER_HORSE) > 0
            statCheck = len(maxStats.intersection([BaseStats.DEF, BaseStats.RES])) > 0
            hitBonus = EffectStacks.SECRET_ART_HORSE
        elif technique == "HOYOKUSEN":
            stanceCheck = controller.combatStateMap[user].getStack(EffectStacks.STRIKER_CRANE) > 0
            statCheck = len(maxStats.intersection([BaseStats.ATK, BaseStats.MAG, BaseStats.ACC])) > 0
            hitBonus = EffectStacks.SECRET_ART_CRANE

        if stanceCheck or statCheck:
            assert hitBonus is not None
            controller.logMessage(MessageType.EFFECT,
                f"{user.shortName} brings out the Secret Art's full power!")
            controller.applyMultStatBonuses(user, {
                BaseStats.ATK: 2 / 1.5
            })
            revertEffect = SkillEffect("", [EFAfterNextAttack(
                lambda controller, user, _1, result, _2: secretArtNormalRevertFn(controller, user, result, hitBonus)
            )], 0, forRevert=True)
            controller.addSkillEffect(user, revertEffect)
    else:
        controller.logMessage(MessageType.EFFECT,
            f"***Messatsu.***")
        shadowingMovementFn(controller, user, [target], result)
        controller.combatStateMap[user].setStack(EffectStacks.SHADOWING, 0)
        controller.applyFlatStatBonuses(user, {
            CombatStats.CRIT_RATE: 1
        })
        controller.applyMultStatBonuses(user, {
            BaseStats.ATK: 3 / 1.5,
            BaseStats.ACC: 2
        })
        revertEffect = SkillEffect("", [EFAfterNextAttack(
            lambda controller, user, _1, _2, _3: secretArtDemonRevertFn(controller, user)
        )], 0, forRevert=True)
        controller.addSkillEffect(user, revertEffect)
def secretArtNormalRevertFn(controller : CombatController, user : CombatEntity, result : AttackResultInfo, hitBonus : EffectStacks):
    controller.revertMultStatBonuses(user, {
        BaseStats.ATK: 2 / 1.5
    })
    if result.attackHit:
        controller.combatStateMap[user].setStack(hitBonus, 1)
def secretArtDemonRevertFn(controller : CombatController, user : CombatEntity):
    controller.revertFlatStatBonuses(user, {
        CombatStats.CRIT_RATE: 1
    })
    controller.revertMultStatBonuses(user, {
        BaseStats.ATK: 3 / 1.5,
        BaseStats.ACC: 2
    })
    for stack in [EffectStacks.SECRET_ART_TIGER, EffectStacks.SECRET_ART_HORSE, EffectStacks.SECRET_ART_CRANE]:
        controller.combatStateMap[user].setStack(stack, 0)
ActiveSkillDataSelector("Secret Art", SecretPlayerClassNames.STRIKER, 9, True, 40,
    "Select a technique; attack with 1.5x ATK. Bonus power may apply based on your stance or highest stat, excluding HP and MP.",
    "__TIGER DESTRUCTION__: Attacks with Slashing damage. +50% ATK if in Tiger stance or highest stat is SPD/AVO.\n" + 
    "__OROCHI BREAKER__: Attacks with Crushing damage. +50% ATK if in Horse stance or highest stat is DEF/RES.\n" + 
    "__HOYOKUSEN__: Attacks with Piercing damage. +50% ATK if in Crane stance or highest stat is ATK/MAG/ACC.\n" + 
    "*(And if you hit all three with their full power...)*",
    DEFAULT_ATTACK_TIMER_USAGE, 1, True, 
    lambda technique: AttackSkillData(
        f"Secret Art: {secretArtNameMap[technique]}", SecretPlayerClassNames.STRIKER, 9, True, 40, "",
        True, AttackType.MELEE, 1.5, DEFAULT_ATTACK_TIMER_USAGE, secretArtEnchantmentMap[technique] +
        [
            SkillEffect("", [
                EFBeforeNextAttack({}, {},
                    lambda controller, user, target, result: secretArtApplyFn(controller, user, target, result, technique),
                    None)
            ], 0)
        ], False),
    ["TIGER", "OROCHI", "HOYOKUSEN", "DEMON"],
    optionChecker = lambda technique, controller, user:
            all([controller.combatStateMap[user].getStack(checkStack) == 1
                 for checkStack in [EffectStacks.SECRET_ART_TIGER, EffectStacks.SECRET_ART_HORSE, EffectStacks.SECRET_ART_CRANE]])
        if technique == "DEMON" else True)


# Alchefist

##### yippee ######

nightbloomStatuses : list[Callable[[CombatController, CombatEntity, CombatEntity], StatusEffect]] = [
    lambda controller, u, t: PoisonStatusEffect(u, t, 4, math.ceil(controller.combatStateMap[u].getTotalStatValue(BaseStats.ATK) * 0.35)),
    lambda controller, u, t: BurnStatusEffect(u, t, 4, math.ceil(controller.combatStateMap[u].getTotalStatValue(BaseStats.MAG) * 0.35)),
    lambda _, u, t: TargetStatusEffect(u, t, 3),
    lambda _, u, t: BlindStatusEffect(u, t, 3),
    lambda _, u, t: StunStatusEffect(u, t, 2),
    lambda _, u, t: ExhaustionStatusEffect(u, t, 3, 1.2),
    lambda _, u, t: MisfortuneStatusEffect(u, t, 4),
    lambda _, u, t: RestrictStatusEffect(u, t, 2),
    lambda _, u, t: PerplexityStatusEffect(u, t, 4, 1.3),
    lambda _, u, t: FearStatusEffect(u, t, 3, 0.9)
]
def alchefyProductEffectFn(controller : CombatController, user : CombatEntity, target : CombatEntity,
                           result : EffectFunctionResult, alchefyProduct : AlchefyProducts):
    controller.logMessage(
        MessageType.EFFECT, f"{user.name}'s Alchefy activates: {ALCHEFY_PRODUCT_NAMES[alchefyProduct]}!")
    
    if alchefyProduct == AlchefyProducts.FLOUR_FLOWER:
        controller.logMessage(
            MessageType.EFFECT, f"The attack is enveloped by magic!")
        controller.addSkillEffect(
            user, EnchantmentSkillEffect("", MagicalAttackAttribute.NEUTRAL, True, {}, {
                BaseStats.MAG: 1.2
            }, [], 0))
        
    elif alchefyProduct == AlchefyProducts.POLLEN_DOUGH:
        controller.logMessage(
            MessageType.EFFECT, f"The attack is enveloped by magic!")
        controller.addSkillEffect(
            user, EnchantmentSkillEffect("", MagicalAttackAttribute.NEUTRAL, True, {}, {
                BaseStats.MAG: 1.5
            }, [
                EFAfterNextAttack(
                    lambda _controller, _user, _target, _attackResult, _: void((
                        _controller.applyMultStatBonuses(_target, {
                            BaseStats.ACC: 0.92
                        }),
                        _controller.logMessage(MessageType.EFFECT, f"{_target.shortName}'s ACC was lowered!")
                    )) if _attackResult.attackHit else None
                )
            ], 0))

    elif alchefyProduct == AlchefyProducts.BUTTERY_SILVER:
        controller.logMessage(
            MessageType.EFFECT, f"The attack flies swiftly through the air!")
        controller.addSkillEffect(
            user, SkillEffect("", [
                EFBeforeNextAttack(
                    {}, { BaseStats.ATK: 0.8 }, None, None
                ),
                EFAfterNextAttack(
                    lambda _controller, _user, _1, _2, _result:
                        _result.setActionTimeMult(0.5)
                )
            ], 0)
        )

    elif alchefyProduct == AlchefyProducts.MERCURY_DRESSING:
        controller.logMessage(
            MessageType.EFFECT, f"The attack slashes swiftly through the air!")
        controller.addSkillEffect(
            user, EnchantmentSkillEffect("", PhysicalAttackAttribute.SLASHING, False, {}, { BaseStats.ATK: 1.2 }, [
                EFAfterNextAttack(
                    lambda _controller, _user, _target, _attackResult, _result: void((
                        _result.setActionTimeMult(0.3),
                        (
                            _controller.applyMultStatBonuses(_target, {
                                BaseStats.DEF: 0.94,
                                BaseStats.RES: 0.94
                            }),
                            _controller.logMessage(MessageType.EFFECT, f"{_target.shortName}'s DEF and RES were lowered!")
                        ) if _attackResult.attackHit else None
                    ))
                )
            ], 0)
        )

    elif alchefyProduct == AlchefyProducts.HATCHING_STONE:
        controller.logMessage(
            MessageType.EFFECT, f"The attack hurtles towards {target.shortName}!")
        controller.addSkillEffect(
            user, SkillEffect("", [
                EFBeforeNextAttack(
                    {}, { BaseStats.ATK: 1.2 }, None, None
                )
            ], 0)
        )

    elif alchefyProduct == AlchefyProducts.QUICKSAND_OMELET:
        controller.logMessage(
            MessageType.EFFECT, f"The attack crashes towards {target.shortName}!")
        controller.addSkillEffect(
            user, EnchantmentSkillEffect("", PhysicalAttackAttribute.CRUSHING, False, {}, { BaseStats.ATK: 1.5 }, [
                EFAfterNextAttack(
                    lambda _controller, _user, _target, _attackResult, _: void((
                        _controller.applyMultStatBonuses(_target, {
                            BaseStats.SPD: 0.93
                        }),
                        _controller.logMessage(MessageType.EFFECT, f"{_target.shortName}'s SPD was lowered!")
                    )) if _attackResult.attackHit else None
                )
            ], 0)
        )

    elif alchefyProduct == AlchefyProducts.BREAD_DOLL:
        controller.logMessage(
            MessageType.EFFECT, f"The piercing attack seeks additional targets!")
        controller.addSkillEffect(
            user, EnchantmentSkillEffect("", PhysicalAttackAttribute.PIERCING, False, {}, { }, [
                EFAfterNextAttack(
                    lambda _controller, _user, _target, _attackResult, _: void((
                        _attackResult.addBonusAttack(
                            _user,
                            _controller.rng.choice([bonusTarget for bonusTarget in _controller.getTargets(_user)
                                                    if _controller.checkInRange(_user, bonusTarget)]),
                            CounterSkillData(True, AttackType.RANGED, 0.75, [])
                        )
                    ))
                )
            ], 0)
        )


    elif alchefyProduct == AlchefyProducts.SYLPHID_NOODLES:
        randomStat = controller.rng.choice([stat for stat in BaseStats
                                            if stat not in [BaseStats.HP, BaseStats.MP, BaseStats.ACC, BaseStats.AVO]])
        controller.logMessage(
            MessageType.EFFECT, f"The attack's winds envelop their allies, increasing {randomStat.name}!")
        controller.addSkillEffect(
            user, EnchantmentSkillEffect("", MagicalAttackAttribute.WIND, True, {}, {
                BaseStats.MAG: 1.3
            }, [
                EFAfterNextAttack(
                    lambda _controller, _user, _target, _attackResult, _: void((
                        [_controller.applyMultStatBonuses(ally, {
                            randomStat: 1.07
                        }) for ally in _controller.getTeammates(_user)]
                    ))
                )
            ], 0))

    elif alchefyProduct == AlchefyProducts.BEDROCK_QUICHE:
        controller.logMessage(
            MessageType.EFFECT, f"The attack raises the earth beneath it!")
        controller.addSkillEffect(
            user, SkillEffect("", [
                EFBeforeNextAttack(
                    {}, { BaseStats.ATK: 1.2 }, None,
                    lambda _controller, _1, _target, _attackResult, _2: void((
                        _controller.logMessage(
                            MessageType.EFFECT, f"{_target.shortName}'s projectiles are obstructed, reducing ATK/MAG/ACC for attacks from a distance!"),
                        _controller.addSkillEffect(_target, SkillEffect(
                            "Bedrock Quiche", [
                                EFBeforeNextAttack(
                                    {}, {},
                                    lambda _controller, _user, _target, _: void((
                                        _controller.combatStateMap[_user].setStack(EffectStacks.SAVED_DISTANCE, _controller.checkDistanceStrict(_user, _target)),
                                        _controller.applyMultStatBonuses(_user, {
                                            BaseStats.ATK: 1 - (_controller.combatStateMap[_user].getStack(EffectStacks.SAVED_DISTANCE) * 0.15),
                                            BaseStats.MAG: 1 - (_controller.combatStateMap[_user].getStack(EffectStacks.SAVED_DISTANCE) * 0.15),
                                            BaseStats.ACC: 1 - (_controller.combatStateMap[_user].getStack(EffectStacks.SAVED_DISTANCE) * 0.15)
                                        })
                                    )),
                                    lambda _controller, _user, _1, _attackResult, _2:
                                        _controller.revertMultStatBonuses(_user, {
                                            BaseStats.ATK: 1 - (_controller.combatStateMap[_user].getStack(EffectStacks.SAVED_DISTANCE) * 0.15),
                                            BaseStats.MAG: 1 - (_controller.combatStateMap[_user].getStack(EffectStacks.SAVED_DISTANCE) * 0.15),
                                            BaseStats.ACC: 1 - (_controller.combatStateMap[_user].getStack(EffectStacks.SAVED_DISTANCE) * 0.15)
                                        })
                                )
                            ], 5, "Bedrock Quiche wore off."
                        ))
                    )) if _attackResult.attackHit else None
                )
            ], 0)
        )

    elif alchefyProduct == AlchefyProducts.MOLTEN_MONOSACCHARIDE:
        controller.logMessage(
            MessageType.EFFECT, f"The attack is enveloped by fire!")
        controller.addSkillEffect(
            user, EnchantmentSkillEffect("", MagicalAttackAttribute.FIRE, True, {}, {
                BaseStats.MAG: 1.2
            }, [], 0))

    elif alchefyProduct == AlchefyProducts.SOLAR_SUGAR:
        controller.logMessage(
            MessageType.EFFECT, f"The attack bursts into an ethereal light! The ACC of allies is increased!")
        controller.addSkillEffect(
            user, EnchantmentSkillEffect("", MagicalAttackAttribute.LIGHT, True, {}, {
                BaseStats.MAG: 1.5
            }, [
                EFAfterNextAttack(
                    lambda _controller, _user, _target, _attackResult, _: void((
                        [_controller.applyMultStatBonuses(ally, {
                            BaseStats.ACC: 1.1
                        }) for ally in _controller.getTeammates(_user)]
                    ))
                )
            ], 0))

    elif alchefyProduct == AlchefyProducts.BASIC_BROTH:
        controller.logMessage(
            MessageType.EFFECT, f"The attack is enveloped by ice!")
        controller.addSkillEffect(
            user, EnchantmentSkillEffect("", MagicalAttackAttribute.ICE, True, {}, {
                BaseStats.MAG: 1.2
            }, [], 0))

    elif alchefyProduct == AlchefyProducts.LUNAR_LEAVENER:
        controller.logMessage(
            MessageType.EFFECT, f"The attack bursts into an ethereal darkness! The AVO of allies is increased!")
        controller.addSkillEffect(
            user, EnchantmentSkillEffect("", MagicalAttackAttribute.DARK, True, {}, {
                BaseStats.MAG: 1.5
            }, [
                EFAfterNextAttack(
                    lambda _controller, _user, _target, _attackResult, _: void((
                        [_controller.applyMultStatBonuses(ally, {
                            BaseStats.AVO: 1.1
                        }) for ally in _controller.getTeammates(_user)]
                    ))
                )
            ], 0))

    elif alchefyProduct == AlchefyProducts.CONFECTIONERS_HAZE:
        randomStat = controller.rng.choice([stat for stat in BaseStats
                                            if stat not in [BaseStats.HP, BaseStats.MP]])
        controller.logMessage(
            MessageType.EFFECT, f"The attack bursts into disorienting magic!")
        controller.addSkillEffect(
            user, EnchantmentSkillEffect("", MagicalAttackAttribute.NEUTRAL, True, {}, {
                BaseStats.MAG: 1.2
            }, [
                EFAfterNextAttack(
                    lambda _controller, _user, _target, _attackResult, _: void((
                        _controller.applyMultStatBonuses(_target, {
                            randomStat: 0.88
                        }),
                        _controller.logMessage(MessageType.EFFECT, f"{_target.shortName}'s {randomStat.name} was lowered!")
                    )) if _attackResult.attackHit else None
                )
            ], 0))
    
    elif alchefyProduct == AlchefyProducts.NIGHTBLOOM_TEA:
        randomStatusFn = controller.rng.choice(nightbloomStatuses)
        controller.logMessage(
            MessageType.EFFECT, f"The attack's magic seeps ominously into {target.shortName}!")
        controller.addSkillEffect(
            user, EnchantmentSkillEffect("", MagicalAttackAttribute.NEUTRAL, True, {}, {
                BaseStats.MAG: 1.2
            }, [
                EFAfterNextAttack(
                    lambda _controller, _user, _target, _attackResult, _: void((
                        _controller.applyStatusCondition(_target, randomStatusFn(_controller, _user, _target))
                    )) if _attackResult.attackHit else None
                )
            ], 0))
    
    elif alchefyProduct == AlchefyProducts.ALLOY_BRULEE:
        controller.logMessage(
            MessageType.EFFECT, f"The attack briefly but violently explodes on impact!")
        controller.addSkillEffect(
            user, SkillEffect("", [
                EFBeforeNextAttack(
                    {}, {},
                    lambda _controller, _user, _1, _2: void((
                        _controller.combatStateMap[_user].setStack(
                            EffectStacks.ALLOY_BRULEE, round(_controller.combatStateMap[_user].getTotalStatValue(BaseStats.MAG) * 0.6)),
                        _controller.applyFlatStatBonuses(_user, {
                            BaseStats.ATK: _controller.combatStateMap[_user].getStack(EffectStacks.ALLOY_BRULEE)
                        })
                    )),
                    lambda _controller, _user, _1, _2, _3:
                        _controller.revertFlatStatBonuses(_user, {
                            BaseStats.ATK: _controller.combatStateMap[_user].getStack(EffectStacks.ALLOY_BRULEE)
                        })
                )
            ], 0)
        )
    
    elif alchefyProduct == AlchefyProducts.CREAM_OF_BISMUTH:
        controller.logMessage(
            MessageType.EFFECT, f"The attack rapidly spirals towards {target.shortName}!")
        controller.addSkillEffect(
            user, SkillEffect("", [
                EFBeforeNextAttack({ CombatStats.CRIT_RATE: 0.3 }, { BaseStats.ATK: 1.1 }, None, None),
                EFAfterNextAttack(
                    lambda _controller, _user, _target, _attackResult, _effectResult: void((
                        _attackResult.setRepeatAttack(),
                        _controller.logMessage(MessageType.EFFECT, f"{_user.shortName}'s attack spirals faster on impact!")
                    )) if _attackResult.attackHit and _attackResult.isCritical and not _attackResult.isBonus else None
                )
            ], 0)
        )
    
    elif alchefyProduct == AlchefyProducts.SCRAMBLED_SUNLIGHT:
        controller.logMessage(
            MessageType.EFFECT, f"The attack's magic shines brightly upon their allies, reducing the time between actions!")
        controller.addSkillEffect(
            user, EnchantmentSkillEffect("", MagicalAttackAttribute.LIGHT, True, {}, {
                BaseStats.MAG: 0.8
            }, [
                EFAfterNextAttack(
                    lambda _controller, _user, _target, _attackResult, _: void((
                        [(
                            _controller.applyMultStatBonuses(ally, {
                                CombatStats.ACTION_GAUGE_USAGE_MULTIPLIER: 0.75
                            }),
                            _controller.addSkillEffect(
                                ally, SkillEffect(
                                    "Scrambled Sunlight", [], 4, "Scrambled Sunlight wore off.", [
                                        EFImmediate(
                                            lambda controller, user, _1, _2: controller.revertMultStatBonuses(user, {
                                                CombatStats.ACTION_GAUGE_USAGE_MULTIPLIER: 0.75
                                            })
                                        )
                                    ]
                                )
                        )) for ally in _controller.getTeammates(_user)]
                    ))
                )
            ], 0))
    
    elif alchefyProduct == AlchefyProducts.POACHED_JADE:
        controller.logMessage(
            MessageType.EFFECT, f"The attack's magic washes calmingly over their allies, reducing MP costs!")
        controller.addSkillEffect(
            user, EnchantmentSkillEffect("", MagicalAttackAttribute.DARK, True, {}, {
                BaseStats.MAG: 0.6
            }, [
                EFAfterNextAttack(
                    lambda _controller, _user, _target, _attackResult, _: void((
                        [(
                            _controller.applyMultStatBonuses(ally, {
                                CombatStats.MANA_COST_MULT: 0.7
                            }),
                            _controller.addSkillEffect(
                                ally, SkillEffect(
                                    "Poached Jade", [], 4, "Poached Jade wore off.", [
                                        EFImmediate(
                                            lambda controller, user, _1, _2: controller.revertMultStatBonuses(user, {
                                                CombatStats.MANA_COST_MULT: 0.7
                                            })
                                        )
                                    ]
                                )
                        )) for ally in _controller.getTeammates(_user)]
                    ))
                )
            ], 0))
    
    elif alchefyProduct == AlchefyProducts.ELIXIR_TEA:
        controller.logMessage(
            MessageType.EFFECT, f"The attack's soothing magic revitalizes their allies!")
        controller.addSkillEffect(
            user, EnchantmentSkillEffect("", MagicalAttackAttribute.NEUTRAL, True, {}, {
                BaseStats.MAG: 1,
            }, [
                EFAfterNextAttack(
                    lambda _controller, _user, _1, _2, _3: void((
                        [
                            _controller.doHealSkill(user, ally, 1.2)
                            for ally in _controller.getTeammates(_user)
                        ]
                    ))
                )
            ], 0))
    
    # else:
    #     assert(False, "Unexpected Alchefy Product") # type: ignore

#####

def activateAlchefyFn(controller : CombatController, user : CombatEntity, target : CombatEntity, result : EffectFunctionResult):
    preparedAlchefy = controller.combatStateMap[user].getAlchefyProduct()
    if preparedAlchefy is not None and controller.combatStateMap[user].getStack(EffectStacks.ALCHEFY_ACTIVATED) == 0:
        alchefyProductEffectFn(controller, user, target, result, preparedAlchefy)
        controller.combatStateMap[user].alchefyPrepared = controller.combatStateMap[user].alchefyPrepared[2:]
        controller.combatStateMap[user].setStack(EffectStacks.ALCHEFY_ACTIVATED, 1)
PassiveSkillData("Alchefist's Reasoning", SecretPlayerClassNames.ALCHEFIST, 1, False,
    "Increases ATK/MAG/ACC by 5% and MP by 10%.",
    {}, {
        BaseStats.ATK: 1.05,
        BaseStats.MAG: 1.05,
        BaseStats.ACC: 1.05,
        BaseStats.MP: 1.1
    }, [
        # Secretly activates alchefy skills
        SkillEffect(
            "", [
                EFBeforeNextAttack({}, {}, activateAlchefyFn, None),
                EFEndTurn(
                    lambda controller, user, _1, _2: controller.combatStateMap[user].setStack(EffectStacks.ALCHEFY_ACTIVATED, 0)
                )
            ], None
        )
    ])

baseAlchefyTime = 0.45
enhancedAlchefyTimeMult = 0.3 / baseAlchefyTime

selectorToElementMap = {
    "FLOUR": AlchefyElements.WOOD,
    "BUTTER": AlchefyElements.METAL,
    "EGG": AlchefyElements.EARTH,
    "SUGAR": AlchefyElements.FIRESUN,
    "YEAST": AlchefyElements.WATERMOON
}
def alchefyCheckCostFn(controller : CombatController, user : CombatEntity, selectedElement : str, displayMode : bool = False):
    element = selectorToElementMap[selectedElement]
    repeats = controller.combatStateMap[user].alchefyRepeatQueue.count(element)
    displayMult = controller.combatStateMap[user].getTotalStatValueFloat(CombatStats.MANA_COST_MULT) if displayMode else 1
    return round(min(10 * (repeats + 1), 40) * displayMult)
def alchefyAddElementFn(controller : CombatController, user : CombatEntity, selectedElement : str):
    element = selectorToElementMap[selectedElement]
    stateMap = controller.combatStateMap[user]
    maxPrepared = stateMap.getTotalStatValue(CombatStats.ALCHEFY_MAX_PREPARED)
    repeatQueue = stateMap.getTotalStatValue(CombatStats.ALCHEFY_REPEAT_MEMORY)

    stateMap.alchefyPrepared.insert(0, element)
    if len(stateMap.alchefyPrepared) > maxPrepared:
        stateMap.alchefyPrepared = stateMap.alchefyPrepared[:maxPrepared]

    stateMap.alchefyRepeatQueue.insert(0, element)
    if len(stateMap.alchefyRepeatQueue) > repeatQueue:
        stateMap.alchefyRepeatQueue = stateMap.alchefyRepeatQueue[:repeatQueue]

    newProduct = stateMap.getAlchefyProduct()
    if newProduct is not None:
        controller.logMessage(
            MessageType.EFFECT, f"{user.shortName} readies {ALCHEFY_ELEMENT_NAMES[element]} Alchefy! " + 
                                f"\"{ALCHEFY_PRODUCT_NAMES[newProduct]}\" is now prepared!")
ActiveSkillDataSelector("Corporeal Ingredients", SecretPlayerClassNames.ALCHEFIST, 2, False, 10,
    "Select an ingredient to combine into your next attack. Attacks use up to 2 ingredients, and " +
    "the MP cost of preparing the same ingredient multiple times will increase.",
    lambda controller, user:
        f"__FLOUR__: Prepares Wood Alchefy. (Current Cost: {alchefyCheckCostFn(controller, user, 'FLOUR', True)} MP)\n" + 
        f"__BUTTER__: Prepares Metal Alchefy (Current Cost: {alchefyCheckCostFn(controller, user, 'BUTTER', True)} MP).\n" + 
        f"__EGG__: Prepares Earth Alchefy (Current Cost: {alchefyCheckCostFn(controller, user, 'EGG', True)} MP).",
    MAX_ACTION_TIMER * baseAlchefyTime, 0, False,
    lambda element: ActiveBuffSkillData(
        f"Alchefy Ingredient ({element[0] + element[1:].lower()})", SecretPlayerClassNames.ALCHEFIST, 2, False,
        lambda controller, user: alchefyCheckCostFn(controller, user, element), "",
        MAX_ACTION_TIMER * baseAlchefyTime, {}, {}, [
            SkillEffect("", [
                EFImmediate(
                    lambda controller, user, _1, _2: void((
                        alchefyAddElementFn(controller, user, element),
                        controller.applyMultStatBonuses(user, {
                            CombatStats.ACTION_GAUGE_USAGE_MULTIPLIER: enhancedAlchefyTimeMult
                        }) if controller.combatStateMap[user].getTotalStatValue(CombatStats.ALCHEFY_MAX_PREPARED) > 2 else None
                    ))
                ),
                EFEndTurn(
                    lambda controller, user, _1, _2: controller.revertMultStatBonuses(user, {
                            CombatStats.ACTION_GAUGE_USAGE_MULTIPLIER: enhancedAlchefyTimeMult
                    }) if controller.combatStateMap[user].getTotalStatValue(CombatStats.ALCHEFY_MAX_PREPARED) > 2 else None
                )
            ], 0)
        ], 0, 0, False, False),
    ["FLOUR", "BUTTER", "EGG"])


def mirrorKnifeFn(controller : CombatController, user : CombatEntity):
    weapon = controller.combatStateMap[user].checkWeapon()
    if weapon is not None:
        statMap = weapon.getStatMap()
        weaponAtk = statMap.get(BaseStats.ATK, 0)
        weaponMag = statMap.get(BaseStats.MAG, 0)
        newOffense = math.ceil((weaponAtk + weaponMag) * 0.8)
        controller.applyFlatStatBonuses(user, {
            BaseStats.ATK: newOffense - weaponAtk,
            BaseStats.MAG: newOffense - weaponMag
        })
PassiveSkillData("Mirror Knife", SecretPlayerClassNames.ALCHEFIST, 3, True,
    "In battle, the ATK and MAG of equipped weapons both become equal to 80% of their sum.",
    {}, {}, [
        SkillEffect("", [
            EFImmediate(
                lambda controller, user, _1, _2: mirrorKnifeFn(controller, user)
            )
        ], None)
    ])


PassiveSkillData("Philosopher's Scone", SecretPlayerClassNames.ALCHEFIST, 4, False,
    "Reduces the number of recent ingredients considered when determining their MP cost.",
    {CombatStats.ALCHEFY_REPEAT_MEMORY: -2}, {}, [])


ActiveSkillDataSelector("Ethereal Ingredients", SecretPlayerClassNames.ALCHEFIST, 5, False, 10,
    "Select an ingredient to combine into your next attack. Similar to Corporeal Ingredients.",
    lambda controller, user:
        f"__SUGAR__: Prepares Fire and Sun Alchefy. (Current Cost: {alchefyCheckCostFn(controller, user, 'SUGAR', True)} MP)\n" + 
        f"__YEAST__: Prepares Water and Moon Alchefy (Current Cost: {alchefyCheckCostFn(controller, user, 'YEAST', True)} MP).",
    MAX_ACTION_TIMER * baseAlchefyTime, 0, False,
    lambda element: ActiveBuffSkillData(
        f"Alchefy Ingredient ({element[0] + element[1:].lower()})", SecretPlayerClassNames.ALCHEFIST, 5, False,
        lambda controller, user: alchefyCheckCostFn(controller, user, element), "",
        MAX_ACTION_TIMER * baseAlchefyTime, {}, {}, [
            SkillEffect("", [
                EFImmediate(
                    lambda controller, user, _1, _2: void((
                        alchefyAddElementFn(controller, user, element),
                        controller.applyMultStatBonuses(user, {
                            CombatStats.ACTION_GAUGE_USAGE_MULTIPLIER: enhancedAlchefyTimeMult
                        }) if controller.combatStateMap[user].getTotalStatValue(CombatStats.ALCHEFY_MAX_PREPARED) > 2 else None
                    ))
                ),
                EFEndTurn(
                    lambda controller, user, _1, _2: controller.revertMultStatBonuses(user, {
                            CombatStats.ACTION_GAUGE_USAGE_MULTIPLIER: enhancedAlchefyTimeMult
                    }) if controller.combatStateMap[user].getTotalStatValue(CombatStats.ALCHEFY_MAX_PREPARED) > 2 else None
                )
            ], 0)
        ], 0, 0, False, False),
    ["SUGAR", "YEAST"])


PassiveSkillData("Curiosity", SecretPlayerClassNames.ALCHEFIST, 6, True,
    "Increases ACC, AVO, and MP by 10%.",
    {}, {
        BaseStats.ACC: 1.1,
        BaseStats.AVO: 1.1,
        BaseStats.MP: 1.1
    }, [])


PassiveSkillData("Seasoned Cookware", SecretPlayerClassNames.ALCHEFIST, 7, False,
    "Decreases the time taken by ingredient skills, and allows up to 5 ingredients to be prepared (attacks will use the 2 most recently prepared).",
    {CombatStats.ALCHEFY_MAX_PREPARED: 3}, {}, [])


PassiveSkillData("Stewing Schemes", SecretPlayerClassNames.ALCHEFIST, 8, True,
    "After taking at least 3 turns without attacking, gain 50% ATK/MAG/ACC on your next attack.",
    {}, {}, [SkillEffect("", [
        EFImmediate(
            lambda controller, user, _1, _2:
                controller.combatStateMap[user].setStack(EffectStacks.STEWING_SCHEMES, 1)
        ),
        EFBeforeNextAttack({}, {}, 
            lambda controller, user, _1, _2: void((
                controller.logMessage(MessageType.EFFECT, f"{user.shortName}'s ATK, MAG, and ACC were increased by Stewing Schemes!"),
                controller.applyMultStatBonuses(user, {
                    BaseStats.ATK: 1.5,
                    BaseStats.MAG: 1.5,
                    BaseStats.ACC: 1.5
                })
            )) if controller.combatStateMap[user].getStack(EffectStacks.STEWING_SCHEMES) >= 4 else None,
            lambda controller, user, _1, _2, _3: void((
                controller.revertMultStatBonuses(user, {
                    BaseStats.ATK: 1.5,
                    BaseStats.MAG: 1.5,
                    BaseStats.ACC: 1.5
                }) if controller.combatStateMap[user].getStack(EffectStacks.STEWING_SCHEMES) >= 4 else None,
                controller.combatStateMap[user].setStack(EffectStacks.STEWING_SCHEMES, 0)
            ))),
        EFEndTurn(
            lambda controller, user, skipDurationTick, _: 
                controller.combatStateMap[user].addStack(EffectStacks.STEWING_SCHEMES, 4)
                if not skipDurationTick else None
        )
    ], None)])


ActiveBuffSkillData("Transcendent Brunch", SecretPlayerClassNames.ALCHEFIST, 9, True, 0,
    "Gain 45 MP.",
    MAX_ACTION_TIMER * 2, {}, {}, [
        SkillEffect("", [EFImmediate(lambda controller, user, _1, _2: void(controller.gainMana(user, 45)))], 0)
    ], 0, 0, False)


# Saboteur

PassiveSkillData("Saboteur's Interference", SecretPlayerClassNames.SABOTEUR, 1, False,
    "Apply a stacking debuff when hitting opponents (max 10). Gain 5% ATK per stack on target when attacking. " + 
    "*(Inevitability: Remove all stacks; apply POISON for 5 turns with 6% Strength per mark.)*",
    {}, {}, [
        SkillEffect("", [
            EFBeforeNextAttack(
                {}, {},
                lambda controller, user, target, _: void((
                    controller.combatStateMap[user].setStack(
                        EffectStacks.SABOTEUR_INTERFERENCE_STORED, controller.combatStateMap[target].getStack(EffectStacks.SABOTEUR_INTERFERENCE)),
                    controller.applyMultStatBonuses(user, {
                        BaseStats.ATK: 1 + (controller.combatStateMap[user].getStack(EffectStacks.SABOTEUR_INTERFERENCE_STORED) * 0.05)
                    })
                )),
                lambda controller, user, _1, _2, _3: void((
                    controller.revertMultStatBonuses(user, {
                        BaseStats.ATK: 1 + (controller.combatStateMap[user].getStack(EffectStacks.SABOTEUR_INTERFERENCE_STORED) * 0.05)
                    })
                ))
            ),
            EFAfterNextAttack(
                lambda controller, _1, target, attackResult, _2: void((
                    controller.combatStateMap[target].addStack(EffectStacks.SABOTEUR_INTERFERENCE, 10)
                )) if attackResult.attackHit else None
            )
        ], None)
    ])

def siphonSetPowerBonusFn(controller : CombatController, user : CombatEntity, target : CombatEntity):
    targetStatusEffects = controller.combatStateMap[target].currentStatusEffects
    totalDotPower = 0
    effectString = ""

    poisonEffect = targetStatusEffects.get(StatusConditionNames.POISON)
    if poisonEffect is not None and isinstance(poisonEffect, PoisonStatusEffect):
        totalDotPower += poisonEffect.poisonStrength
        effectString = "POISON"

    burnEffect = targetStatusEffects.get(StatusConditionNames.BURN)
    if burnEffect is not None and isinstance(burnEffect, BurnStatusEffect):
        totalDotPower += burnEffect.burnStrength
        if len(effectString) > 0:
            effectString += " and "
        effectString += "BURN"
    
    controller.logMessage(
        MessageType.EFFECT, f"{user.shortName} exploits the {effectString} applied to {target.shortName}!"
    )
    controller.combatStateMap[user].setStack(
        EffectStacks.SABOTEUR_SIPHON_BONUS, math.ceil(totalDotPower * 1)
    )
AttackSkillData("Inevitability", SecretPlayerClassNames.SABOTEUR, 2, False, 30,
    "Attack with 1x ATK. The Inevitability effects of Saboteur debuffs on the target will activate if there are a sufficient number of stacks.",
    True, None, 1, DEFAULT_ATTACK_TIMER_USAGE, [
        SkillEffect("", [
            EFAfterNextAttack(
                lambda controller, user, target, attackResult, _: void((
                    (
                        controller.applyStatusCondition(
                            target, PoisonStatusEffect(user, target, 5, math.ceil(
                                controller.combatStateMap[user].getTotalStatValue(BaseStats.ATK) *
                                (controller.combatStateMap[target].getStack(EffectStacks.SABOTEUR_INTERFERENCE) * 0.06)))
                        ),
                        controller.combatStateMap[target].setStack(EffectStacks.SABOTEUR_INTERFERENCE, 0)
                    ) if controller.combatStateMap[target].getStack(EffectStacks.SABOTEUR_INTERFERENCE) > 0 else None,

                    (
                        controller.logMessage(
                            MessageType.EFFECT, f"{user.shortName}'s actions become Traceless, greatly reducing MP costs!"
                        ),
                        controller.applyMultStatBonuses(user, {
                            CombatStats.MANA_COST_MULT: 0.35
                        }),
                        controller.addSkillEffect(
                            user, SkillEffect("Traceless Actions", [], 3, "Traceless Actions wore off.", [
                                EFImmediate(
                                    lambda controller, user, _1, _2: controller.revertMultStatBonuses(user, {
                                        CombatStats.MANA_COST_MULT: 0.35
                                    })
                                )
                            ])
                        ),
                        [controller.combatStateMap[target].removeStack(EffectStacks.SABOTEUR_TRACELESS) for i in range(4)]
                    ) if controller.combatStateMap[target].getStack(EffectStacks.SABOTEUR_TRACELESS) >= 4 else None,

                    (
                        controller.logMessage(
                            MessageType.EFFECT, f"{user.shortName}'s Infiltration increases their Critical Hit Rate!"
                        ),
                        controller.applyFlatStatBonuses(user, {
                            CombatStats.CRIT_RATE: 0.05
                        }),
                        [controller.combatStateMap[target].removeStack(EffectStacks.SABOTEUR_INFILTRATION) for i in range(3)]
                    ) if controller.combatStateMap[target].getStack(EffectStacks.SABOTEUR_INFILTRATION) >= 3 else None,
                )) if attackResult.attackHit else None
            ),

            EFBeforeNextAttack(
                {}, {},
                lambda controller, user, target, _: void((
                    (
                        siphonSetPowerBonusFn(controller, user, target),
                        controller.applyFlatStatBonuses(
                            user, {
                                BaseStats.ATK: controller.combatStateMap[user].getStack(EffectStacks.SABOTEUR_SIPHON_BONUS)
                            }
                        )
                    ) if controller.combatStateMap[target].getStack(EffectStacks.SABOTEUR_SIPHON) >= 3 else None,

                    (
                        controller.applyFlatStatBonuses(
                            user, {
                                CombatStats.CRIT_RATE: 0.35
                            }
                        )
                    ) if controller.combatStateMap[target].getStack(EffectStacks.SABOTEUR_BLACKOUT) >= 2 else None
                )),
                lambda controller, user, target, attackResult, effectResult: void((
                    (
                        controller.revertFlatStatBonuses(
                            user, {
                                BaseStats.ATK: controller.combatStateMap[user].getStack(EffectStacks.SABOTEUR_SIPHON_BONUS)
                            }
                        ),
                        controller.combatStateMap[target].setStack(EffectStacks.SABOTEUR_SIPHON_BONUS, 0),
                        [controller.combatStateMap[target].removeStack(EffectStacks.SABOTEUR_SIPHON) for i in range(3)]
                            if attackResult.attackHit else None
                    ) if controller.combatStateMap[target].getStack(EffectStacks.SABOTEUR_SIPHON) >= 3 else None,

                    (
                        controller.revertFlatStatBonuses(
                            user, {
                                CombatStats.CRIT_RATE: 0.35
                            }
                        ),
                        (
                            controller.logMessage(
                                MessageType.EFFECT, f"{user.shortName} capitalizes on the Blackout appllied to {target.shortName}!"
                            ),
                            effectResult.setActionTimeMult(0.5),
                            [controller.combatStateMap[target].removeStack(EffectStacks.SABOTEUR_BLACKOUT) for i in range(2)]
                        ) if attackResult.attackHit else None
                    ) if controller.combatStateMap[target].getStack(EffectStacks.SABOTEUR_BLACKOUT) >= 2 else None
                ))
            )
        ], 0)
    ])

PassiveSkillData("Siphon", SecretPlayerClassNames.SABOTEUR, 3, True,
    "Apply a stacking debuff when opponents take POISON/BURN damage (max 5). Restore 1% of max HP/MP per stack on target when attacking. " + 
    "*(Inevitability: Remove 3 stacks; increase attack's ATK by the strength of target's active POISON/BURN effects.)*",
    {}, {}, [
        SkillEffect("", [
            EFOnOpponentDotDamage(
                lambda controller, _1, target, _2, _3: void((
                    controller.combatStateMap[target].addStack(EffectStacks.SABOTEUR_SIPHON, 5)
                ))
            ),
            EFAfterNextAttack(
                lambda controller, user, target, attackResult, _: void((
                    controller.gainHealth(user, math.ceil(
                        controller.getMaxHealth(user) * (controller.combatStateMap[target].getStack(EffectStacks.SABOTEUR_SIPHON) * 0.01))
                    ),
                    controller.gainMana(user, math.ceil(
                        controller.getMaxMana(user) * (controller.combatStateMap[target].getStack(EffectStacks.SABOTEUR_SIPHON) * 0.01))
                    )
                )) if attackResult.attackHit and controller.combatStateMap[target].getStack(EffectStacks.SABOTEUR_SIPHON) > 0 else None 
            )
        ], None)
    ])

PassiveSkillData("Blackout", SecretPlayerClassNames.SABOTEUR, 4, False,
    "Apply a stacking debuff when dodging an attack (max 6). Gain 10% ACC/AVO per stack on target or attacker. " + 
    "*(Inevitability: Remove 2 stacks; increase attack's Critical Hit Rate by 35% and decrease time to next action.)*",
    {}, {}, [
        SkillEffect("", [
            EFBeforeNextAttack(
                {}, {},
                lambda controller, user, target, _: void((
                    controller.combatStateMap[user].setStack(
                        EffectStacks.SABOTEUR_BLACKOUT_STORED, controller.combatStateMap[target].getStack(EffectStacks.SABOTEUR_BLACKOUT)),
                    controller.applyMultStatBonuses(user, {
                        BaseStats.ACC: 1 + (controller.combatStateMap[user].getStack(EffectStacks.SABOTEUR_BLACKOUT_STORED) * 0.1)
                    })
                )),
                lambda controller, user, _1, _2, _3: void((
                    controller.revertMultStatBonuses(user, {
                        BaseStats.ACC: 1 + (controller.combatStateMap[user].getStack(EffectStacks.SABOTEUR_BLACKOUT_STORED) * 0.1)
                    })
                ))
            ),
            EFBeforeAttacked(
                {}, {},
                lambda controller, user, attacker: void((
                    controller.combatStateMap[user].setStack(
                        EffectStacks.SABOTEUR_BLACKOUT_STORED, controller.combatStateMap[attacker].getStack(EffectStacks.SABOTEUR_BLACKOUT)),
                    controller.applyMultStatBonuses(user, {
                        BaseStats.AVO: 1 + (controller.combatStateMap[user].getStack(EffectStacks.SABOTEUR_BLACKOUT_STORED) * 0.1)
                    })
                )),
                lambda controller, user, _1, _2: void((
                    controller.revertMultStatBonuses(user, {
                        BaseStats.AVO: 1 + (controller.combatStateMap[user].getStack(EffectStacks.SABOTEUR_BLACKOUT_STORED) * 0.1)
                    })
                ))
            ),
            EFWhenAttacked(
                lambda controller, _1, attacker, attackResult, _2: void((
                    controller.combatStateMap[attacker].addStack(EffectStacks.SABOTEUR_BLACKOUT, 6)
                )) if attackResult.inRange and not attackResult.attackHit else None
            )
        ], None)
    ])

def tamperingFn(controller : CombatController, user : CombatEntity, target : CombatEntity):
    targetStatusEffects = controller.combatStateMap[target].currentStatusEffects
    totalDotPower = 0

    poisonEffect = targetStatusEffects.get(StatusConditionNames.POISON)
    if poisonEffect is not None and isinstance(poisonEffect, PoisonStatusEffect):
        totalDotPower += poisonEffect.poisonStrength

    burnEffect = targetStatusEffects.get(StatusConditionNames.BURN)
    if burnEffect is not None and isinstance(burnEffect, BurnStatusEffect):
        totalDotPower += burnEffect.burnStrength
    
    if totalDotPower > 0:
        newDotPower = math.ceil(totalDotPower * 0.5)
        controller.applyStatusCondition(target, PoisonStatusEffect(user, target, 3, newDotPower))
        controller.applyStatusCondition(target, BurnStatusEffect(user, target, 3, newDotPower))
AttackSkillData("Tampering", SecretPlayerClassNames.SABOTEUR, 5, False, 20,
    "Attack with 1x ATK. If the opponent is POISONED or BURNED, inflict both conditions for 3 turns with a strength based on the existing ones.",
    True, None, 1, DEFAULT_ATTACK_TIMER_USAGE, [
        SkillEffect("", [
            EFAfterNextAttack(
                lambda controller, user, target, result, _:
                    tamperingFn(controller, user, target) if result.attackHit else None
            )
        ], 0)
    ])

PassiveSkillData("Efficiency", SecretPlayerClassNames.SABOTEUR, 6, True,
    "Increases critical hit rate by 5%. On a critical hit, reduce the time to your next action.",
    {CombatStats.CRIT_RATE: 0.05}, {}, [SkillEffect("", [EFAfterNextAttack(
        lambda controller, user, _1, attackInfo, result:
            void(result.setActionTimeMult(0.85)) if attackInfo.isCritical else None
    )], None)])

PassiveSkillData("Traceless", SecretPlayerClassNames.SABOTEUR, 7, False,
    "Apply a stacking debuff when landing an attacking skill (max 4). Status application success rate +10% per stack on target when attacking. " + 
    "*(Inevitability: Remove 4 stacks; reduce MP costs by 65% for the next 2 turns.)*",
    {}, {}, [
        SkillEffect("", [
            EFOnAttackSkill(
                lambda controller, user, _1, _2: void((
                    controller.addSkillEffect(user, SkillEffect("", [
                        EFAfterNextAttack(
                            lambda controller, _1, target, attackResult, _2: void((
                                controller.combatStateMap[target].addStack(EffectStacks.SABOTEUR_TRACELESS, 4)
                            )) if attackResult.attackHit else None
                        )
                    ], 0))
                ))
            ),
            EFBeforeNextAttack(
                {}, {},
                lambda controller, user, target, _: void((
                    controller.combatStateMap[user].setStack(
                        EffectStacks.SABOTEUR_TRACELESS_STORED, controller.combatStateMap[target].getStack(EffectStacks.SABOTEUR_TRACELESS)),
                    controller.applyMultStatBonuses(user, {
                        CombatStats.STATUS_APPLICATION_TOLERANCE_MULTIPLIER:
                            1 - (controller.combatStateMap[user].getStack(EffectStacks.SABOTEUR_TRACELESS_STORED) * 0.1)
                    })
                )),
                None
            ),
            EFEndTurn(
                lambda controller, user, _1, _2: void((
                    controller.revertMultStatBonuses(user, {
                        CombatStats.STATUS_APPLICATION_TOLERANCE_MULTIPLIER:
                            1 - (controller.combatStateMap[user].getStack(EffectStacks.SABOTEUR_TRACELESS_STORED) * 0.1)
                    }),
                    controller.combatStateMap[user].setStack(EffectStacks.SABOTEUR_TRACELESS_STORED, 0)
                )) if controller.combatStateMap[user].getStack(EffectStacks.SABOTEUR_TRACELESS_STORED) > 0 else None
            )
        ], None)
    ])

PassiveSkillData("Infiltration", SecretPlayerClassNames.SABOTEUR, 8, True,
    "Apply a stacking debuff when landing critical hits (max 5). Gain 4% Critical Damage per stack on target when attacking. " + 
    "*(Inevitability: Remove 3 stacks; increase Critical Hit Rate by 5%.)*",
    {}, {}, [
        SkillEffect("", [
            EFBeforeNextAttack(
                {}, {},
                lambda controller, user, target, _: void((
                    controller.combatStateMap[user].setStack(
                        EffectStacks.SABOTEUR_INFILTRATION_STORED, controller.combatStateMap[target].getStack(EffectStacks.SABOTEUR_INFILTRATION)),
                    controller.applyFlatStatBonuses(user, {
                        CombatStats.CRIT_DAMAGE: controller.combatStateMap[user].getStack(EffectStacks.SABOTEUR_INFILTRATION_STORED) * 0.04
                    })
                )),
                lambda controller, user, _1, _2, _3: void((
                    controller.revertFlatStatBonuses(user, {
                        CombatStats.CRIT_DAMAGE: controller.combatStateMap[user].getStack(EffectStacks.SABOTEUR_INFILTRATION_STORED) * 0.04
                    })
                ))
            ),

            EFAfterNextAttack(
                lambda controller, _1, target, attackResult, _2: void((
                    controller.combatStateMap[target].addStack(EffectStacks.SABOTEUR_INFILTRATION, 5)
                )) if attackResult.attackHit and attackResult.isCritical else None
            )
        ], None)
    ])

AttackSkillData("No Witnesses", SecretPlayerClassNames.SABOTEUR, 9, True, 45,
    "Attack with 0.65x ATK and 0.7x ACC. If this defeats an opponent, restore HP and MP equal to your maximum.",
    True, None, 0.65, DEFAULT_ATTACK_TIMER_USAGE, [
        SkillEffect("", [
            EFBeforeNextAttack(
                {}, { BaseStats.ACC: 0.7 }, None, None
            ),
            EFAfterNextAttack(
                lambda controller, user, target, _1, _2: void((
                    controller.gainHealth(user, controller.getMaxHealth(user)),
                    controller.gainMana(user, controller.getMaxMana(user))
                )) if controller.getCurrentHealth(target) <= 0 else None
            )
        ], 0)
    ])