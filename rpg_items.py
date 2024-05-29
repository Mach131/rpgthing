import math
import random
import numpy as np
from typing import Callable


from rpg_consts import *
from rpg_classes_skills import EffectFunction, PassiveSkillData, SkillEffect, \
    EFImmediate, EFBeforeNextAttack, EFAfterNextAttack, EFWhenAttacked

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
    "Carelessly", "Easily", "Awkwardly", "Nearby", "Cheerfully", "Abruptly", "Late", "Everyday", "Soon", "Coldly", "Angrily", "Curiously",
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
        super().__init__(name, EquipmentSlot.WEAPON, baseStats, curse, traits, rarity, rank)
        self.weaponType : WeaponType = weaponType

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

statHpTrait = makeStatUpTrait(BaseStats.HP, 2)
statMpTrait = makeStatUpTrait(BaseStats.MP, 3)
statAtkTrait = makeStatUpTrait(BaseStats.ATK, 5)
statMagTrait = makeStatUpTrait(BaseStats.MAG, 5)
statDefTrait = makeStatUpTrait(BaseStats.DEF, 6)
statResTrait = makeStatUpTrait(BaseStats.RES, 6)
statAccTrait = makeStatUpTrait(BaseStats.ACC, 3)
statAvoTrait = makeStatUpTrait(BaseStats.AVO, 3)
statSpdTrait = makeStatUpTrait(BaseStats.SPD, 5)

""" Use a formatting field in description to indicate the part to replace with the amount. """
def makeFlatStatBonusTrait(stat: Stats, scaling : int, description : str):
    return EquipmentTrait(lambda r, c: description.format(abs(scaling*(r+1)*(1.5 if c else 1))),
                          lambda r, c: PassiveSkillData("", BasePlayerClassNames.WARRIOR, 0, False, "",
                                                        {stat: scaling*(r+1)*(0.015 if c else 0.01)}, {}, [], False))

bonusWeaknessTrait = makeFlatStatBonusTrait(CombatStats.BONUS_WEAKNESS_DAMAGE, 4, "Increase damage by {}% when targeting a weakness.")
ignoreResistanceTrait = makeFlatStatBonusTrait(CombatStats.IGNORE_RESISTANCE, 5, "Ignore {}% of opponent resistances.")
critRateTrait = makeFlatStatBonusTrait(CombatStats.CRIT_RATE, 2, "Increase critical hit rate by {}%.")
critDamageTrait = makeFlatStatBonusTrait(CombatStats.CRIT_RATE, 3, "Increase critical hit damage by {}%.")
aggroIncreaseTrait = makeFlatStatBonusTrait(CombatStats.AGGRO_MULT, 5, "Increase aggro generated by {}%.")
aggroDecreaseTrait = makeFlatStatBonusTrait(CombatStats.AGGRO_MULT, -4, "Decrease aggro generated by {}%.")

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
curseTraits : list[EquipmentTrait] = [
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
    makeFlatStatBonusTrait(CombatStats.HEALING_EFFECTIVENESS, -6, "Decrease healing effectiveness by {}%."),
    healthCostCurse,
    manaCostCurse
]

# TODO: weakness/resistance traits, append to the maps in state as immediate
#   (may need to define a revert method for changing equips mid-fight; probably won't be used yet)

def getWeaponTraitWeights(rarity : int, hasCurse : bool) -> dict[EquipmentTrait, int]: #TODO: put on correct piece of equipment
    return {
        statHpTrait: 4,
        statMpTrait: 4,
        statAtkTrait: 4,
        statMagTrait: 4,
        statDefTrait: 4,
        statResTrait: 4,
        statAccTrait: 4,
        statAvoTrait: 4,
        statSpdTrait: 4,
        bonusWeaknessTrait: 3,
        ignoreResistanceTrait: 3,
        critRateTrait: 3,
        critDamageTrait: 3,
        aggroIncreaseTrait: 2,
        aggroDecreaseTrait: 2,
        healthDrainTrait: 3 if hasCurse else 0,
        manaGainTrait: 3 if (hasCurse and rarity >= 2) else 0
    }

def generateWeapon(rarity : int, rank : int, weapon : None | WeaponClasses = None) -> Weapon:
    weaponClass : WeaponClasses | None = weapon
    if weaponClass is None:
        weaponClass = random.choice([weaponClass for weaponClass in WeaponClasses])
    weaponAttributes : WeaponAttributes = weaponClassAttributeMap[weaponClass]

    curseTrait : EquipmentTrait | None = None
    numTraits : int = 4 # TODO: math.ceil((rarity + 1)/2)
    
    if random.random() <= EQUIP_CURSE_CHANCE:
        curseTrait = random.choice(curseTraits)
    traitMap = getWeaponTraitWeights(rarity, curseTrait is not None)
    traitList = np.array(list(traitMap.keys()))
    traitWeights = np.array(list(traitMap.values()))
    traitWeights = traitWeights / sum(traitWeights)
    traits : list[EquipmentTrait] = list(np.random.choice(traitList, numTraits, False, traitWeights))

    adverbCount = math.floor(rarity/2)
    descriptors = random.sample(DESCRIPTIVE_ADVERBS, adverbCount)
    descriptors.append(random.choice(DESCRIPTIVE_ADJECTIVES))
    fullName = f"{' '.join(descriptors)} {weaponAttributes.name}"
    return Weapon(fullName, weaponAttributes.weaponType, weaponAttributes.baseStats,
                  curseTrait, traits, rarity, rank)

