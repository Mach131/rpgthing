import math

from rpg_consts import *
from rpg_classes_skills import PassiveSkillData, AttackSkillData, ActiveBuffSkillData, ActiveToggleSkillData, CounterSkillData, \
    SkillEffect, EFImmediate, EFBeforeNextAttack, EFAfterNextAttack, EFWhenAttacked, EFOnStatsChange

# Warrior

PassiveSkillData("Warrior's Resolution", BasePlayerClassNames.WARRIOR, 1, False,
    "Increases HP by 100, ATK by 10, and DEF by 5.",
    {BaseStats.HP: 100, BaseStats.ATK: 10, BaseStats.DEF: 5}, {}, [])

AttackSkillData("Great Swing", BasePlayerClassNames.WARRIOR, 2, False, 20,
    "Attack with 1.5x ATK.",
    True, 1.5, DEFAULT_ATTACK_TIMER_USAGE, [])

PassiveSkillData("Endurance", BasePlayerClassNames.WARRIOR, 3, True,
    "Recovers 2% HP at the end of your turn.",
    {}, {}, [SkillEffect([EFAfterNextAttack(
      lambda controller, user, _1, _2, _3: void(controller.gainHealth(user, round(controller.getMaxHealth(user) * 0.02)))
    )], None)])


# Ranger

PassiveSkillData("Ranger's Focus", BasePlayerClassNames.RANGER, 1, False,
    "Increases ACC by 25, RES by 10, and SPD by 5.",
    {BaseStats.ACC: 25, BaseStats.RES: 10, BaseStats.SPD: 5}, {}, [])

def increaseDistanceFn(controller, user, target, _1, _2):
    currentDistance = controller.checkDistance(user, target)
    if currentDistance is not None:
        controller.updateDistance(user, target, currentDistance + 1)
AttackSkillData("Strafe", BasePlayerClassNames.RANGER, 2, False, 15,
    "Attack with 0.8x ATK, increasing distance to the target by 1.",
    True, 0.8, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect([EFAfterNextAttack(increaseDistanceFn)], 0)])

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
    True, 0.7, DEFAULT_ATTACK_TIMER_USAGE / 2, [])

def illusionFn(controller, user, attacker, attackInfo, _2):
    if attackInfo.inRange and not attackInfo.attackHit:
        counterData = CounterSkillData(True, 0.7,
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
    False, 1, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect([EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1}, {}, None, None)], 0)])

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
    True, 0.8, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect([EFAfterNextAttack(
        lambda controller, _1, target, attackInfo, _2:
            controller.applyMultStatBonuses(target, {BaseStats.DEF: 0.85}) if attackInfo.attackHit else None
    )], 0)])

def confrontationFn(controller, user, target, revert):
    if revert: # check if was initially at range 0
        if controller.combatStateMap[user].getTotalStatValue(CombatStats.FLAG_CONFRONT) == 0:
            return
    else: # check if currently at range 0
        if controller.checkDistance(user, target) > 0:
            return
    amount = 1.1 if not revert else 1/1.1
    controller.applyMultStatBonuses(user, {BaseStats.ATK: amount, BaseStats.ACC: amount})
    controller.applyFlatStatBonuses(user, {CombatStats.FLAG_CONFRONT: 1 if not revert else -1})
PassiveSkillData("Confrontation", AdvancedPlayerClassNames.MERCENARY, 3, True,
    "When attacking at distance 0, increase ATK and ACC by 10%.",
    {}, {}, [SkillEffect([EFBeforeNextAttack({}, {},
                    lambda controller, user, target: confrontationFn(controller, user, target, False),
                    lambda controller, user, target, _: confrontationFn(controller, user, target, True)
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
            counterData = CounterSkillData(True, 1,
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