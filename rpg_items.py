import math
import random
import numpy as np
from typing import Callable


from rpg_consts import *
from rpg_classes_skills import EffectFunction, PassiveSkillData, SkillEffect, \
    EFImmediate, EFBeforeNextAttack, EFAfterNextAttack, EFWhenAttacked
from rpg_status_definitions import STATUS_CLASS_MAP, StatusEffect

DESCRIPTIVE_ADJECTIVES = [
    "Accurate", "Advanced", "Alluring", "Antique", "Appealing", "Artificial", "Astonishing", "Attractive","Automated", "Bad", "Beautiful",
    "Big", "Small", "Bland", "Bold", "Boring", "Breakable", "Bright", "Broken", "Cheap", "Classic", "Classy", "Clean", "Clear", "Clever",
    "Colorful", "Comfortable", "Common", "Compact", "Complete", "Complicated", "Cool", "Craft", "Crafted", "Fine Crafted", "Cute", "Damaged",
    "Dangerous", "Dashing", "Definitive", "Delicate", "Delightful", "Detailed", "Dreadful", "Distinct", "Dull", "Durable", "Effective", "Efficient",
    "Electric", "Elegant", "Emergent", "Enchanted", "Engaging", "Entertaining", "Essential", "Expensive", "Inexpensive", "Faded", "Fake",
    "Fancy", "Fashionable", "Unfashionable", "Fast", "Slow", "Fine", "Finished", "Unfinished", "Flat", "Flawless", "Folk", "Fragile",
    "Fresh", "Friendly", "Unfriendly", "Frightful", "Fun", "Futuristic", "Genuine", "Good", "Hideous", "Hot", "Cold", "Iconic",
    "Idiosyncratic", "Imaginative", "Imperfect", "Important", "Imported", "Impromptu", "Improved", "Inadequate", "Ineffectual", "Inferior",
    "Innovative", "Inoperative", "Insubstantial", "Intelligent", "Inventive", "Lame", "Latest", "Light", "Local", "Lovely", "Lush",
    "Luxurious", "Makeshift", "Massive", "Masterpiece", "Material", "Messy", "Modern", "Modish", "Moldy", "Musty", "Monstrous", "Natural",
    "Neat", "Necessary", "Nice", "Nondescript", "Nonsensical", "Nonstop", "Nontraditional", "Notable", "Novel", "Odd", "Offbeat", "Old",
    "New", "Old-fashioned", "Open", "Ordinary", "Organic", "Original", "Outstanding", "Overengineered", "Pathetic", "Perfect", "Pleasant",
    "Pleasing", "Polished", "Poor", "Popular", "Posh", "Precious", "Quaint", "Quality", "Quiet", "Rapid", "Red", "Blue", "Green", "Black",
    "White", "Yellow", "Orange", "Purple", "Redundant", "Refined", "Regular", "Repulsive", "Resilient", "Responsible", "Rotten", "Rough",
    "Round", "Sad", "Safe", "Scientific", "Second-rate", "Shiny", "Simple", "Slick", "Smart", "Snappy", "Sophisticated", "Stable",
    "Standard", "State of the Art", "Strange", "Streamlined", "Stunning", "Stylish", "Sublime", "Subtle", "Superb", "Superficial",
    "Superior", "Sweet", "Tall", "Tangible", "Tasteful", "Terrible", "Traditional", "Trashy", "Trendy", "Trim", "Typical", "Ugly",
    "Ultramodern", "Unassuming", "Unattractive", "Uncommon", "Unconventional", "Unique", "Unnatural", "Unnecessary", "Unsightly", "Unusable",
    "Urbane", "Usable", "Used", "Useful", "Useless", "Vacuous", "Valuable", "Venerable", "Vintage", "Visionary", "Wacky", "Wasteful",
    "Weird", "Wild", "Wonderful", "Worthless", "Based", "Gray", "Pink"]

DESCRIPTIVE_ADVERBS = [
    "Very", "Always", "Ever", "Seldom", "Rarely", "Gradually", "Eventually", "Most", "Quickly", "Slowly", "Incidentally", "Immediately",
    "Simultaneously", "Happily", "Sadly", "Frequently", "Commonly", "Sincerely", "Faithfully", "Sweetly", "Badly", "Dearly", "Patiently",
    "Mostly", "Silently", "Willingly", "Hardly", "Often", "Occasionally", "Regularly", "Normally", "Actually", "Basically",
    "Extremely", "Exceedingly", "Arguably", "Comparatively", "Consecutively", "Honestly", "Truthfully", "Lovingly", "Perfectly", "Highly",
    "Likely", "Nearly", "Barely", "Least", "Deeply", "Fully", "Completely", "Casually", "Tastefully", "Madly", "Purely", "Privately",
    "Publicly", "Eagerly", "Beautifully", "Proudly", "Elegantly", "Confidently", "Incessantly", "Boldly", "Carefully", "Cautiously",
    "Carelessly", "Easily", "Awkwardly", "Nearby", "Cheerfully", "Abruptly", "Late", "Everyday", "Coldly", "Angrily", "Curiously",
    "Noisily", "Loudly", "Earnestly", "Interestingly", "Readily", "Vaguely", "Unwillingly", "Obediently", "Rapidly", "Continuously",
    "Consciously", "Instinctively", "Boldly", "Brightly", "Cunningly", "Suitably", "Appropriately", "Currently", "Doubtfully", "Ambiguously",
    "Momentarily", "Gently", "Superficially", "Supremely", "Adequately", "Comfortably", "Conveniently", "Generously", "Briefly",
    "Accidentally", "Fiercely", "Fearfully", "Gracefully", "Graciously", "Busily", "Randomly", "Joyously", "Mysteriously", "Joyfully",
    "Poorly", "Repeatedly", "Seriously", "Smoothly", "Promptly", "Roughly", "Successfully", "Sufficiently", "Skillfully", "Sceptically",
    "Differently", "Physically", "Psychologically", "Logically", "Analytically", "Graphically", "Tightly", "Loosely", "Unexpectedly",
    "Tactfully", "Lazily", "Tremendously", "Vicariously", "Vividly", "Cleverly", "Victoriously", "Widely", "Purposefully", "Wisely",
    "Properly", "Sickly", "Legally", "Nicely", "Legibly", "Thoroughly", "Shortly", "Simply", "Tidily", "Necessarily", "Tenaciously",
    "Strongly", "Humbly", "Consequently", "Similarly", "Unlikely", "Possibly", "Probably"]

# Concept: all items are named "[adjective] [item type]"; rarity-3 gets 1 adverb, rarity-5 gets two

class Item(object):
    def __init__(self, name : str):
        self.name : str = name

class EquipmentTrait(object):
    def __init__(self, descriptionGenerator: Callable[[int, bool], str], effectSkillGenerator : Callable[[int, bool], PassiveSkillData]) -> None:
        self.descriptionGenerator : Callable[[int, bool], str] = descriptionGenerator
        self.effectSkillGenerator : Callable[[int, bool], PassiveSkillData] = effectSkillGenerator

    def getDescription(self, rarity : int, curseBoost : bool) -> str:
        return self.descriptionGenerator(rarity, curseBoost)

    def getEffectSkill(self, rarity : int, curseBoost : bool) -> PassiveSkillData:
        return self.effectSkillGenerator(rarity, curseBoost)

class Equipment(Item):
    def __init__(self, name : str, equipSlot : EquipmentSlot, baseStats : dict[BaseStats, int],
                curse : EquipmentTrait | None, traits : list[EquipmentTrait], rarity : int, rank : int) -> None:
        super().__init__(name)
        self.equipSlot : EquipmentSlot = equipSlot
        self.baseStats : dict[BaseStats, int] = baseStats.copy()
        self.rarity : int = rarity
        self.rank : int = rank

        self.curse : EquipmentTrait | None = curse
        self.traits : list[EquipmentTrait] = traits[:]
        self.currentTraitSkills : list[PassiveSkillData] = []
        self.reloadTraitSkills()

    def getDescription(self) -> str:
        statMap = self.getStatMap()
        mainLine =  f"{self.name}: {itemRarityStrings[self.rarity]} Rank {self.rank}\n"
        statLine = ", ".join([f"{statMap[stat]} {stat.name}" for stat in statMap]) + "\n"
        curseLine = "" if self.curse is None else f"Curse: {self.curse.getDescription(self.rarity, False)}\n"
        traitLine = "Traits:\n- " + "\n- ".join([
            trait.getDescription(self.rarity, i == 0 and self.curse is not None) for i, trait in enumerate(self.traits)
        ])
        return mainLine + statLine + curseLine + traitLine

    """ Re-creates the list of skills from traits. Any removal of existing skills should be handled before calling. """
    def reloadTraitSkills(self):
        self.currentTraitSkills = []
        startingTraitIndex : int = 0

        if self.curse is not None:
            self.currentTraitSkills.append(self.curse.getEffectSkill(self.rarity, False))
            self.currentTraitSkills.append(self.traits[0].getEffectSkill(self.rarity, True))
            startingTraitIndex = 1
        for i in range(startingTraitIndex, len(self.traits)):
            self.currentTraitSkills.append(self.traits[i].getEffectSkill(self.rarity, False))

    """ Gets the stats of the weapon, scaled for its rarity and rank. """
    def getStatMap(self) -> dict[BaseStats, int]:
        currentRarityMultiplier = (self.rarity+1) ** 2
        nextRarityMultiplier = (self.rarity+2) ** 2 if self.rarity < MAX_ITEM_RARITY else ((MAX_ITEM_RARITY+1) ** 3) / MAX_RANK_STAT_SCALING
        rankScalingRange = (nextRarityMultiplier * MAX_RANK_STAT_SCALING) - currentRarityMultiplier
        rankScalingBonus = rankScalingRange * self.rank / MAX_ITEM_RANK

        finalMultiplier = currentRarityMultiplier + rankScalingBonus
        return { baseStat: math.ceil(self.baseStats[baseStat] * finalMultiplier) for baseStat in self.baseStats}
    
class Weapon(Equipment):
    def __init__(self, name : str, weaponType : WeaponType, baseStats : dict[BaseStats, int],
                curse : EquipmentTrait | None, traits : list[EquipmentTrait], rarity : int, rank : int) -> None:
        weaponRange = weaponTypeAttributeMap[weaponType].maxRange
        self.rangeSkill = PassiveSkillData("", BasePlayerClassNames.WARRIOR, 0, False, "", {CombatStats.RANGE: weaponRange}, {}, [], False)

        super().__init__(name, EquipmentSlot.WEAPON, baseStats, curse, traits, rarity, rank)
        self.weaponType : WeaponType = weaponType

    def reloadTraitSkills(self):
        super().reloadTraitSkills()
        self.currentTraitSkills.append(self.rangeSkill)

# Weapon/trait definition; move later?

def makeStatUpTrait(stat: Stats, scaling : int):
    return EquipmentTrait(lambda r, c: f"Increase {stat.name} by {scaling*(r+1)*(1.5 if c else 1)}%.",
                   lambda r, c: PassiveSkillData("", BasePlayerClassNames.WARRIOR, 0, False, "", {},
                                                 {stat: 1 + (scaling*(r+1)*(0.015 if c else 0.01))}, [], False))
    
def makeStatDownTrait(stat: Stats, scaling : int):
    return EquipmentTrait(lambda r, c: f"Decrease {stat.name} by {scaling*(r+1)}%.",
                   lambda r, c: PassiveSkillData("", BasePlayerClassNames.WARRIOR, 0, False, "", {},
                                                 {stat: 1 - (scaling*(r+1)*0.01)}, [], False))

# TODO: probably needs more specific revert
def makeWeaknessTrait(attribute : AttackAttribute):
    attributeString = attribute.name[0] + attribute.name[1:].lower()
    return EquipmentTrait(lambda r, c: f"Gain {r+1} stack(s) of {attributeString}-attribute weakness.",
                    lambda r, c: PassiveSkillData("", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {}, [SkillEffect(
                        [EFImmediate(lambda controller, user, _1, _2: controller.addWeaknessStacks(user, attribute, r+1))], None)], False))

def makeResistanceTrait(attribute : AttackAttribute):
    attributeString = attribute.name[0] + attribute.name[1:].lower()
    return EquipmentTrait(lambda r, c: f"Gain {r+1+(1 if c else 0)} stack(s) of {attributeString}-attribute resistance.",
                    lambda r, c: PassiveSkillData("", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {}, [SkillEffect(
                        [EFImmediate(lambda controller, user, _1, _2: controller.addResistanceStacks(user, attribute, r+1+(1 if c else 0)))],
                        None)], False))

statHpTrait = makeStatUpTrait(BaseStats.HP, 2)
statMpTrait = makeStatUpTrait(BaseStats.MP, 3)
statAtkTrait = makeStatUpTrait(BaseStats.ATK, 5)
statMagTrait = makeStatUpTrait(BaseStats.MAG, 5)
statDefTrait = makeStatUpTrait(BaseStats.DEF, 6)
statResTrait = makeStatUpTrait(BaseStats.RES, 6)
statAccTrait = makeStatUpTrait(BaseStats.ACC, 3)
statAvoTrait = makeStatUpTrait(BaseStats.AVO, 3)
statSpdTrait = makeStatUpTrait(BaseStats.SPD, 5)

resistSlashTrait = makeResistanceTrait(PhysicalAttackAttribute.SLASHING)
resistPierceTrait = makeResistanceTrait(PhysicalAttackAttribute.PIERCING)
resistCrushTrait = makeResistanceTrait(PhysicalAttackAttribute.CRUSHING)
resistFireTrait = makeResistanceTrait(MagicalAttackAttribute.FIRE)
resistIceTrait = makeResistanceTrait(MagicalAttackAttribute.ICE)
resistWindTrait = makeResistanceTrait(MagicalAttackAttribute.WIND)
resistLightTrait = makeResistanceTrait(MagicalAttackAttribute.LIGHT)
resistDarkTrait = makeResistanceTrait(MagicalAttackAttribute.DARK)

""" Use a formatting field in description to indicate the part to replace with the amount. """
def makeFlatStatBonusTrait(stat: Stats, scaling : int, description : str):
    return EquipmentTrait(lambda r, c: description.format(abs(scaling*(r+1)*(1.5 if c else 1))),
                          lambda r, c: PassiveSkillData("", BasePlayerClassNames.WARRIOR, 0, False, "",
                                                        {stat: scaling*(r+1)*(0.015 if c else 0.01)}, {}, [], False))
def makeMultStatBonusTrait(stat: Stats, scaling : int, description : str):
    return EquipmentTrait(lambda r, c: description.format(abs(scaling*(r+1)*(1.5 if c else 1))),
                          lambda r, c: PassiveSkillData("", BasePlayerClassNames.WARRIOR, 0, False, "", {},
                                                        {stat: 1 + (scaling*(r+1)*(0.015 if c else 0.01))}, [], False))

bonusWeaknessTrait = makeMultStatBonusTrait(CombatStats.BONUS_WEAKNESS_DAMAGE_MULT, 4, "Increase damage by {}% when targeting a weakness.")
ignoreResistanceTrait = makeMultStatBonusTrait(CombatStats.IGNORE_RESISTANCE_MULT, 5, "Ignore {}% of opponent resistances.")
critRateTrait = makeFlatStatBonusTrait(CombatStats.CRIT_RATE, 2, "Increase critical hit rate by {}%.")
critDamageTrait = makeFlatStatBonusTrait(CombatStats.CRIT_RATE, 3, "Increase critical hit damage by {}%.")
aggroIncreaseTrait = makeFlatStatBonusTrait(CombatStats.AGGRO_MULT, 5, "Increase aggro generated by {}%.")
aggroDecreaseTrait = makeFlatStatBonusTrait(CombatStats.AGGRO_MULT, -4, "Decrease aggro generated by {}%.")
statusResistanceTrait = makeMultStatBonusTrait(CombatStats.STATUS_RESISTANCE_MULTIPLIER, 4, "Increase status condition resistance by {}%.")

def makeStatusEffectTrait(statusName : StatusConditionNames, procScaling : int, duration : int, valMethod : Callable | None, description : str):
    statusClass = STATUS_CLASS_MAP[statusName]
    return EquipmentTrait(lambda r, c: description.format(abs(procScaling*(r+1)*(1.5 if c else 1)), duration + (1 if c else 0)),
                            lambda r, c: PassiveSkillData("", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {},
            [SkillEffect([EFAfterNextAttack(
                lambda controller, user, target, attackInfo, _: void(
                    controller.applyStatusCondition(target, statusClass(user, target, duration + (1 if c else 0)) if valMethod is None else
                                                    statusClass(user, target, duration + (1 if c else 0), valMethod(controller, user, target)))
                        if (attackInfo.attackHit and controller._randomRoll(target, user) < (procScaling*(r+1)*(0.015 if c else 0.01))) else None
            ))], None)], False))

poisonEffectTrait = makeStatusEffectTrait(StatusConditionNames.POISON, 5, 4,
                                          lambda controller, user, target:
                                            math.ceil(controller.combatStateMap[user].getTotalStatValue(BaseStats.ATK) * 0.3),
                                          "{}% chance to attempt to apply POISON (30% strength) on hit for {} turns.")
burnEffectTrait = makeStatusEffectTrait(StatusConditionNames.BURN, 5, 4,
                                          lambda controller, user, target:
                                            math.ceil(controller.combatStateMap[user].getTotalStatValue(BaseStats.MAG) * 0.3),
                                          "{}% chance to attempt to apply BURN (30% strength) on hit for {} turns.")
targetEffectTrait = makeStatusEffectTrait(StatusConditionNames.TARGET, 3, 3, None,
                                          "{}% chance to attempt to apply TARGET on hit for {} turns.")
blindEffectTrait = makeStatusEffectTrait(StatusConditionNames.BLIND, 3, 3, None,
                                          "{}% chance to attempt to apply BLIND on hit for {} turns.")
stunEffectTrait = makeStatusEffectTrait(StatusConditionNames.STUN, 2, 1, None,
                                          "{}% chance to attempt to apply STUN on hit for {} turns.")
exhaustionEffectTrait = makeStatusEffectTrait(StatusConditionNames.EXHAUSTION, 4, 3,
                                          lambda controller, user, target: 1.3,
                                          "{}% chance to attempt to apply EXHAUSTION (30% strength) on hit for {} turns.")
misfortuneEffectTrait = makeStatusEffectTrait(StatusConditionNames.MISFORTUNE, 3, 4, None,
                                          "{}% chance to attempt to apply MISFORTUNE on hit for {} turns.")
restrictEffectTrait = makeStatusEffectTrait(StatusConditionNames.RESTRICT, 3, 2, None,
                                          "{}% chance to attempt to apply RESTRICT on hit for {} turns.")
perplexityEffectTrait = makeStatusEffectTrait(StatusConditionNames.PERPLEXITY, 3, 3,
                                          lambda controller, user, target: 1.5,
                                          "{}% chance to attempt to apply PERPLEXITY (50% strength) on hit for {} turns.")
fearEffectTrait = makeStatusEffectTrait(StatusConditionNames.FEAR, 2, 5,
                                          lambda controller, user, target: 0.9,
                                          "{}% chance to attempt to apply FEAR (10% strength) on hit for {} turns.")

healthDrainTrait = EquipmentTrait(lambda r, c: f"Restore {r+1}% of the damage you deal as HP.",
                                  lambda r, c: PassiveSkillData("", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {},
    [SkillEffect([EFAfterNextAttack(
        lambda controller, user, _1, attackInfo, _2: void(controller.gainHealth(user, math.ceil(attackInfo.damageDealt * ((r+1) * 0.01))))
    )], None)], False))
manaGainTrait = EquipmentTrait(lambda r, c: f"When you hit the opponent, restore {(2*r)-3}% of your MP.",
                                  lambda r, c: PassiveSkillData("", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {},
    [SkillEffect([EFAfterNextAttack(
        lambda controller, user, _1, attackInfo, _2:
            void(controller.gainMana(user, math.ceil(controller.getMaxMana(user) * (((2*r)-3) * 0.01)))) if attackInfo.attackHit else None
    )], None)], False))

luckTrait = EquipmentTrait(lambda r, c: f"Become{','.join([' much' for i in range(math.floor(r*(1.5 if c else 1) / 2)-1)])} luckier!",
                          lambda r, c: PassiveSkillData("", BasePlayerClassNames.WARRIOR, 0, False, "",
                                                        {CombatStats.LUCK: math.floor(r*(1.5 if c else 1) / 2)}, {}, [], False))


healthCostCurse = EquipmentTrait(lambda r, c: f"When attacking, spend {r+1}% of your total HP. (Cannot kill you.)",
                                  lambda r, c: PassiveSkillData("", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {},
    [SkillEffect([EFBeforeNextAttack({}, {},
        lambda controller, user, _1: void(controller.applyDamage(user, user,
            min(math.ceil(controller.getMaxHealth(user) * ((r+1)*0.01)), controller.getCurrentHealth(user)-1))), None)], None)], False))
manaCostCurse = EquipmentTrait(lambda r, c: f"When attacking, spend {r+1}% of your total MP.",
                                  lambda r, c: PassiveSkillData("", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {},
    [SkillEffect([EFBeforeNextAttack({}, {},
        lambda controller, user, _1:
            void(controller.spendMana(user, math.ceil(controller.getMaxMana(user) * ((r+1)*0.01)))), None)], None)], False))

def makeStatusEffectCurse(statusName : StatusConditionNames, procScaling : float, duration : int, valMethod : Callable | None, description : str):
    statusClass = STATUS_CLASS_MAP[statusName]
    return EquipmentTrait(lambda r, c: description.format(abs(procScaling*(r+1)), duration),
                            lambda r, c: PassiveSkillData("", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {},
            [SkillEffect([EFAfterNextAttack(
                lambda controller, user, _1, attackInfo, _2: void(
                    controller.applyStatusCondition(user, statusClass(user, user, duration+1) if valMethod is None else
                                                    statusClass(user, user, duration+1, valMethod(controller, user)))
                        if controller._randomRoll(user, None) < (procScaling*(r+1)*0.01) else None
            ))], None)], False))

targetEffectCurse = makeStatusEffectCurse(StatusConditionNames.TARGET, 2, 3, None,
                                          "After attacking, {:.1f}% chance to attempt to self-inflict TARGET for {} turns.")
blindEffectCurse = makeStatusEffectCurse(StatusConditionNames.BLIND, 2, 3, None,
                                          "After attacking, {:.1f}% chance to attempt to self-inflict BLIND for {} turns.")
stunEffectCurse = makeStatusEffectCurse(StatusConditionNames.STUN, 1.5, 1, None,
                                          "After attacking, {:.1f}% chance to attempt to self-inflict STUN for {} turns.")
exhaustionEffectCurse = makeStatusEffectCurse(StatusConditionNames.EXHAUSTION, 2, 3,
                                              lambda controller, user: 1.3,
                                          "After attacking, {:.1f}% chance to attempt to self-inflict EXHAUSTION (30% strength) for {} turns.")
misfortuneEffectCurse = makeStatusEffectCurse(StatusConditionNames.MISFORTUNE, 2, 4, None,
                                          "After attacking, {:.1f}% chance to attempt to self-inflict MISFORTUNE for {} turns.")
restrictEffectCurse = makeStatusEffectCurse(StatusConditionNames.RESTRICT, 2, 2, None,
                                          "After attacking, {:.1f}% chance to attempt to self-inflict RESTRICT for {} turns.")
perplexityEffectCurse = makeStatusEffectCurse(StatusConditionNames.PERPLEXITY, 2, 3,
                                              lambda controller, user: 1.5,
                                          "After attacking, {:.1f}% chance to attempt to self-inflict PERPLEXITY (50% strength) for {} turns.")

def getCurseTraits(equipType : EquipmentSlot) -> list[EquipmentTrait]:
    curseTraits = [
        makeStatDownTrait(BaseStats.HP, 4),
        makeStatDownTrait(BaseStats.MP, 4),
        makeStatDownTrait(BaseStats.DEF, 5),
        makeStatDownTrait(BaseStats.RES, 5),
        makeStatDownTrait(BaseStats.ACC, 3),
        makeStatDownTrait(BaseStats.AVO, 3),
        makeStatDownTrait(BaseStats.SPD, 4),
        makeWeaknessTrait(PhysicalAttackAttribute.SLASHING),
        makeWeaknessTrait(PhysicalAttackAttribute.PIERCING),
        makeWeaknessTrait(PhysicalAttackAttribute.CRUSHING),
        makeWeaknessTrait(MagicalAttackAttribute.FIRE),
        makeWeaknessTrait(MagicalAttackAttribute.ICE),
        makeWeaknessTrait(MagicalAttackAttribute.WIND),
        makeWeaknessTrait(MagicalAttackAttribute.LIGHT),
        makeWeaknessTrait(MagicalAttackAttribute.DARK),
        healthCostCurse,
        manaCostCurse,
        targetEffectCurse,
        blindEffectCurse,
        stunEffectCurse,
        exhaustionEffectCurse,
        misfortuneEffectCurse,
        restrictEffectCurse,
        perplexityEffectCurse
    ]
    if equipType in [EquipmentSlot.HAT, EquipmentSlot.OVERALL, EquipmentSlot.SHOES]:
        curseTraits.append(makeFlatStatBonusTrait(CombatStats.HEALING_EFFECTIVENESS, -6, "Decrease healing effectiveness by {}%."))
    return curseTraits

def getEquipTraitWeights(equipType : EquipmentSlot, rarity : int, hasCurse : bool) -> dict[EquipmentTrait, int]: #TODO: put on correct piece of equipment
    return {
        statHpTrait: 8 if equipType in [EquipmentSlot.HAT, EquipmentSlot.OVERALL, EquipmentSlot.SHOES] else 0,
        statMpTrait: 8 if equipType in [EquipmentSlot.HAT, EquipmentSlot.OVERALL] else 0,
        statAtkTrait: 10 if equipType is EquipmentSlot.WEAPON else 0,
        statMagTrait: 10 if equipType is EquipmentSlot.WEAPON else 0,
        statDefTrait: 8 if equipType is EquipmentSlot.OVERALL else (3 if equipType is EquipmentSlot.WEAPON else 0),
        statResTrait: 8 if equipType is EquipmentSlot.OVERALL else (3 if equipType is EquipmentSlot.WEAPON else 0),
        statAccTrait: 8 if equipType is EquipmentSlot.HAT else (3 if equipType is EquipmentSlot.WEAPON else 0),
        statAvoTrait: 8 if equipType is EquipmentSlot.SHOES else (3 if equipType is EquipmentSlot.WEAPON else 0),
        statSpdTrait: 8 if equipType is EquipmentSlot.SHOES else (3 if equipType is EquipmentSlot.WEAPON else 0),
        resistSlashTrait: 2 if equipType is EquipmentSlot.OVERALL else 0,
        resistPierceTrait: 2 if equipType is EquipmentSlot.OVERALL else 0,
        resistCrushTrait: 2 if equipType is EquipmentSlot.OVERALL else 0,
        resistFireTrait: 1 if equipType is EquipmentSlot.OVERALL else 0,
        resistIceTrait: 1 if equipType is EquipmentSlot.OVERALL else 0,
        resistWindTrait: 1 if equipType is EquipmentSlot.OVERALL else 0,
        resistLightTrait: 1 if equipType is EquipmentSlot.OVERALL else 0,
        resistDarkTrait: 1 if equipType is EquipmentSlot.OVERALL else 0,
        bonusWeaknessTrait: 5,
        ignoreResistanceTrait: 5,
        critRateTrait: 6,
        critDamageTrait: 6,
        aggroIncreaseTrait: 4,
        aggroDecreaseTrait: 4,
        healthDrainTrait: 5 if (equipType is EquipmentSlot.WEAPON and hasCurse) else 0,
        manaGainTrait: 5 if (equipType is EquipmentSlot.WEAPON and hasCurse and rarity >= 2) else 0,
        statusResistanceTrait: 6,
        poisonEffectTrait: 1 if equipType is EquipmentSlot.WEAPON else 0,
        burnEffectTrait: 1 if equipType is EquipmentSlot.WEAPON else 0,
        targetEffectTrait: 1 if equipType is EquipmentSlot.WEAPON else 0,
        blindEffectTrait: 1 if equipType is EquipmentSlot.WEAPON else 0,
        stunEffectTrait: 1 if (equipType is EquipmentSlot.WEAPON and rarity >= 2) else 0,
        misfortuneEffectTrait: 1 if equipType is EquipmentSlot.WEAPON else 0,
        restrictEffectTrait: 1 if equipType is EquipmentSlot.WEAPON else 0,
        exhaustionEffectTrait: 1 if equipType is EquipmentSlot.WEAPON else 0,
        perplexityEffectTrait: 1 if equipType is EquipmentSlot.WEAPON else 0,
        fearEffectTrait: 1 if (equipType is EquipmentSlot.WEAPON and rarity >= 2) else 0,
        luckTrait: 2 if rarity >= 2 else 0
    }

def generateEquip(rarity : int, rank : int, equipClass : EquipClass) -> Equipment:
    equipClassAttributes = getEquipClassAttributes(equipClass)
    equipSlot = equipClassAttributes.equipSlot

    curseTrait : EquipmentTrait | None = None
    numTraits : int = math.ceil((rarity + 1)/2) if equipSlot is EquipmentSlot.WEAPON else math.ceil((rarity+1)/3)
    if equipClassAttributes.bonusTrait:
        numTraits += 1
    
    if random.random() <= EQUIP_CURSE_CHANCE:
        curseTrait = random.choice(getCurseTraits(equipSlot))
    traitMap = getEquipTraitWeights(equipSlot, rarity, curseTrait is not None)
    traitList = np.array(list(traitMap.keys()))
    traitWeights = np.array(list(traitMap.values()))
    traitWeights = traitWeights / sum(traitWeights)
    traits : list[EquipmentTrait] = list(np.random.choice(traitList, numTraits, False, traitWeights))

    adverbCount = math.floor(rarity/2)
    descriptors = random.sample(DESCRIPTIVE_ADVERBS, adverbCount)
    descriptors.append(random.choice(DESCRIPTIVE_ADJECTIVES))
    fullName = f"{' '.join(descriptors)} {equipClassAttributes.name}"
    if isinstance(equipClassAttributes, WeaponAttributes):
        return Weapon(fullName, equipClassAttributes.weaponType, equipClassAttributes.baseStats,
                      curseTrait, traits, rarity, rank)
    else:
        return Equipment(fullName, equipSlot, equipClassAttributes.baseStats,
                         curseTrait, traits, rarity, rank)

def generateWeapon(rarity : int, rank : int, weaponClass : None | WeaponClasses = None) -> Equipment:
    if weaponClass is None:
        weaponClass = random.choice([weaponClass for weaponClass in WeaponClasses])
    return generateEquip(rarity, rank, weaponClass)

def generateHat(rarity : int, rank : int, hatClass : None | HatClasses = None) -> Equipment:
    if hatClass is None:
        hatClass = random.choice([hatClass for hatClass in HatClasses])
    return generateEquip(rarity, rank, hatClass)

def generateOverall(rarity : int, rank : int, overallClass : None | OverallClasses = None) -> Equipment:
    if overallClass is None:
        overallClass = random.choice([overallClass for overallClass in OverallClasses])
    return generateEquip(rarity, rank, overallClass)

def generateShoes(rarity : int, rank : int, shoeClass : None | ShoeClasses = None) -> Equipment:
    if shoeClass is None:
        shoeClass = random.choice([shoeClass for shoeClass in ShoeClasses])
    return generateEquip(rarity, rank, shoeClass)
    

