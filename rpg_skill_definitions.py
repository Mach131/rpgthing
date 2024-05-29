from rpg_consts import *
from rpg_classes_skills import PassiveSkillData, AttackSkillData, CounterSkillData, SkillEffect, \
    EFImmediate, EFBeforeNextAttack, EFAfterNextAttack, EFWhenAttacked

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

# Rogue

PassiveSkillData("Rogue's Instinct", BasePlayerClassNames.ROGUE, 1, False,
    "Increases AVO by 25, SPD by 10, and ATK by 5.",
    {BaseStats.AVO: 25, BaseStats.SPD: 10, BaseStats.ATK: 5}, {}, [])

AttackSkillData("Swift Strike", BasePlayerClassNames.ROGUE, 2, False, 10,
    "Attack with 0.7x ATK, but a reduced time until next action.",
    True, 0.7, DEFAULT_ATTACK_TIMER_USAGE / 2, [])

def illusionFn(controller, user, attacker, attackInfo, _2):
    if not attackInfo.attackHit:
        counterData = CounterSkillData(True, 0.7, [])
        attackInfo.addBonusAttack(user, attacker, counterData)
PassiveSkillData("Illusion", BasePlayerClassNames.ROGUE, 3, True,
    "When dodging an enemy in range, counter with 0.7x ATK.",
    {}, {}, [SkillEffect([EFWhenAttacked(illusionFn)], None)])