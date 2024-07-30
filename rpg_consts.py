from enum import Enum, auto

def void(x):
    return None
def enumName(e : Enum):
    return e.name[0] + e.name[1:].lower()
EPSILON = 0.0001

""" Stats """
class Stats(Enum):
    pass

class BaseStats(Stats):
    HP = auto()
    MP = auto()
    ATK = auto()
    DEF = auto()
    MAG = auto()
    RES = auto()
    ACC = auto()
    AVO = auto()
    SPD = auto()

class CombatStats(Stats):
    CRIT_RATE = auto()
    CRIT_DAMAGE = auto()
    AGGRO_MULT = auto()
    RANGE = auto()
    IGNORE_RANGE_CHECK = auto()
    DAMAGE_REDUCTION = auto()
    WEAKNESS_MODIFIER = auto()
    RESISTANCE_MODIFIER = auto()
    BONUS_WEAKNESS_DAMAGE_MULT = auto()
    IGNORE_RESISTANCE_MULT = auto()
    HEALING_EFFECTIVENESS = auto()
    ACCURACY_DISTANCE_MOD = auto()
    ACC_EFFECTIVE_DISTANCE_MOD = auto()
    FIXED_ATTACK_POWER = auto()
    GUARANTEE_SELF_HIT = auto()
    STATUS_RESISTANCE_MULTIPLIER = auto()
    STATUS_APPLICATION_TOLERANCE_MULTIPLIER = auto()
    ACTION_GAUGE_USAGE_MULTIPLIER = auto()
    LUCK = auto()
    MANA_COST_MULT = auto()
    MANA_GAIN_MULT = auto()
    ATTACK_SKILL_MANA_COST_MULT = auto()
    REPOSITION_ACTION_TIME_MULT = auto()
    OPPORTUNISM = auto()
    INSTANTANEOUS_ETERNITY = auto()
    BASIC_MP_GAIN_MULT = auto()
    TIGER_INSTINCT = auto()
    INNER_PEACE = auto()
    ALCHEFY_MAX_PREPARED = auto()
    ALCHEFY_REPEAT_MEMORY = auto()
    DEFEND_ACTION_TIME_MULT = auto()
    DEFEND_ACTION_DAMAGE_MULT = auto()
    COOPERATION_BONUS_CRIT = auto()
    SNAPS_DELEGATOR = auto()
    UNWAVERING_TRUST = auto()
    SUPEREROGATOR_RESET = auto()
class SpecialStats(Stats):
    CURRENT_HP = auto()
    CURRENT_MP = auto()

baseCombatStats : dict[CombatStats, float] = {
    CombatStats.CRIT_RATE: 0.05,
    CombatStats.CRIT_DAMAGE: 2.0,
    CombatStats.AGGRO_MULT: 1,
    CombatStats.RANGE: 0,
    CombatStats.IGNORE_RANGE_CHECK: 0,
    CombatStats.DAMAGE_REDUCTION: 0,
    CombatStats.WEAKNESS_MODIFIER: 0.2,
    CombatStats.RESISTANCE_MODIFIER: 0.2,
    CombatStats.BONUS_WEAKNESS_DAMAGE_MULT: 1,
    CombatStats.IGNORE_RESISTANCE_MULT: 1,
    CombatStats.HEALING_EFFECTIVENESS: 1,
    CombatStats.ACCURACY_DISTANCE_MOD: 2,
    CombatStats.ACC_EFFECTIVE_DISTANCE_MOD: 0,
    CombatStats.FIXED_ATTACK_POWER: 0,
    CombatStats.GUARANTEE_SELF_HIT: 0,
    CombatStats.STATUS_RESISTANCE_MULTIPLIER: 1,
    CombatStats.STATUS_APPLICATION_TOLERANCE_MULTIPLIER: 1,
    CombatStats.ACTION_GAUGE_USAGE_MULTIPLIER: 1,
    CombatStats.LUCK: 0,
    CombatStats.MANA_COST_MULT: 1,
    CombatStats.MANA_GAIN_MULT: 1,
    CombatStats.ATTACK_SKILL_MANA_COST_MULT: 1,
    CombatStats.REPOSITION_ACTION_TIME_MULT: 1,
    CombatStats.OPPORTUNISM: 0,
    CombatStats.INSTANTANEOUS_ETERNITY: 0,
    CombatStats.BASIC_MP_GAIN_MULT: 1,
    CombatStats.TIGER_INSTINCT: 0,
    CombatStats.INNER_PEACE: 0,
    CombatStats.ALCHEFY_MAX_PREPARED: 2,
    CombatStats.ALCHEFY_REPEAT_MEMORY: 4,
    CombatStats.DEFEND_ACTION_TIME_MULT: 1,
    CombatStats.DEFEND_ACTION_DAMAGE_MULT: 1,
    CombatStats.COOPERATION_BONUS_CRIT: 0,
    CombatStats.SNAPS_DELEGATOR: 0,
    CombatStats.UNWAVERING_TRUST: 0,
    CombatStats.SUPEREROGATOR_RESET: 0
}

baseStatValues_base : dict[BaseStats, int] = {
  BaseStats.HP: 50,
  BaseStats.MP: 30,
  BaseStats.ATK: 10,
  BaseStats.DEF: 10,
  BaseStats.MAG: 10,
  BaseStats.RES: 10,
  BaseStats.ACC: 50, # was 50; changed based on low level testing
  BaseStats.AVO: 50, # was 50; changed based on low level testing
  BaseStats.SPD: 20
}

baseStatValues_perLevel : dict[BaseStats, int]  = {
  BaseStats.HP: 50,
  BaseStats.MP: 10,
  BaseStats.ATK: 10,
  BaseStats.DEF: 10,
  BaseStats.MAG: 10,
  BaseStats.RES: 10,
  BaseStats.ACC: 10,
  BaseStats.AVO: 10,
  BaseStats.SPD: 5
}

""" Classes """
class PlayerClassNames(Enum):
    pass

class BasePlayerClassNames(PlayerClassNames):
    WARRIOR = auto()
    RANGER = auto()
    ROGUE = auto()
    MAGE = auto()

class AdvancedPlayerClassNames(PlayerClassNames):
    MERCENARY = auto()
    KNIGHT = auto()
    SNIPER = auto()
    HUNTER = auto()
    ASSASSIN = auto()
    ACROBAT = auto()
    WIZARD = auto()
    SAINT = auto()

class SecretPlayerClassNames(PlayerClassNames):
    STRIKER = auto()
    ALCHEFIST = auto()
    SABOTEUR = auto()
    SUMMONER = auto()
    SNAPS = auto()

CLASS_DESCRIPTION : dict[PlayerClassNames, str] = {
    BasePlayerClassNames.WARRIOR: "Confront opponents face-on!",
    BasePlayerClassNames.RANGER: "Attack safely from afar!",
    BasePlayerClassNames.ROGUE: "Dance around enemy attacks!",
    BasePlayerClassNames.MAGE: "Provide arcane support!",

    AdvancedPlayerClassNames.MERCENARY: "Overwhelm enemies with pure physical power at any cost!",
    AdvancedPlayerClassNames.KNIGHT: "Protect your allies with an insurmountable defense!",
    AdvancedPlayerClassNames.SNIPER: "Wear down targets from afar to line up your perfect shot!",
    AdvancedPlayerClassNames.HUNTER: "Incapacitate enemies with status conditions before they can pose a threat!",
    AdvancedPlayerClassNames.ASSASSIN: "Use quick strikes to lower enemies' guards for a big finisher!",
    AdvancedPlayerClassNames.ACROBAT: "Become untouchable, dodging to draw attention while building momentum!",
    AdvancedPlayerClassNames.WIZARD: "Enchant your and your party's attacks to magically hammer weak points!",
    AdvancedPlayerClassNames.SAINT: "Provide allies with an arsenal of offensive and defensive support!",

    SecretPlayerClassNames.STRIKER: "Master unarmed combat to adapt to the needs of any battle!",
    SecretPlayerClassNames.ALCHEFIST: "Concoct a variety of additional attack effects by combining ingredients!",
    SecretPlayerClassNames.SABOTEUR: "Wear down your targets, growing stronger each time they falter!",
    SecretPlayerClassNames.SUMMONER: "Fight alongside a summoned creature, overwhelming opponents from two angles!",

    SecretPlayerClassNames.SNAPS: "[shouldn't be viewable]"
}

MAX_BASE_CLASS_RANK = 3
MAX_ADVANCED_CLASS_RANK = 9

MAX_FREE_SKILLS = 4

""" Effects """

class EffectTimings(Enum):
    IMMEDIATE = auto()
    BEFORE_ATTACK = auto()
    AFTER_ATTACK = auto()
    BEFORE_ATTACKED = auto()
    AFTER_ATTACKED = auto()
    ON_REPOSITION = auto()
    ON_STAT_CHANGE = auto()
    ON_APPLY_STATUS_SUCCESS = auto()
    ON_HEAL_SKILL = auto()
    PARRY = auto()
    START_TURN = auto()
    END_TURN = auto()
    ADVANCE_TURN = auto()
    ON_OPPONENT_DOT = auto()
    ON_DEFEND = auto()

class EffectStacks(Enum):
    STEADY_HAND = auto()
    SUPPRESSIVE_FIRE = auto()
    SHADOWING = auto()
    EYES_OF_THE_DARK = auto()
    EOTD_CONSUMED = auto()
    UNRELENTING_ASSAULT = auto()
    FIRE_BLESSING = auto()
    TELEGRAPH_RANGE = auto()
    TELEGRAPH_ATTACK = auto()
    RAT_MARK_IMPETUOUS = auto()
    RAT_MARK_RESOLUTE = auto()
    RAT_MARK_INTREPID = auto()
    CONSUMED_RAT_MARK_IMPETUOUS = auto()
    CONSUMED_RAT_MARK_RESOLUTE = auto()
    CONSUMED_RAT_MARK_INTREPID = auto()
    ENEMY_COUNTER_A = auto()
    ENEMY_COUNTER_B = auto()
    ENEMY_PHASE_COUNTER = auto()
    RPS_LEVEL = auto()
    BUTTERFLY_KI = auto()
    SALALI_CHARGE = auto()
    STRIKER_TIGER = auto()
    STRIKER_HORSE = auto()
    STRIKER_CRANE = auto()
    TIGER_BONUS = auto()
    HORSE_INSTINCTS = auto()
    HORSE_BONUS = auto()
    CRANE_BONUS = auto()
    SECRET_ART_TIGER = auto()
    SECRET_ART_HORSE = auto()
    SECRET_ART_CRANE = auto()
    ALCHEFY_ACTIVATED = auto()
    STEWING_SCHEMES = auto()
    SAVED_DISTANCE = auto()
    CONFRONTATION_BONUS = auto()
    CAMOUFLAGE_DISTANCE = auto()
    ALLOY_BRULEE = auto()
    SABOTEUR_INTERFERENCE = auto()
    SABOTEUR_INTERFERENCE_STORED = auto()
    SABOTEUR_SIPHON = auto()
    SABOTEUR_SIPHON_BONUS = auto()
    SABOTEUR_BLACKOUT = auto()
    SABOTEUR_BLACKOUT_STORED = auto()
    SABOTEUR_TRACELESS = auto()
    SABOTEUR_TRACELESS_STORED = auto()
    SABOTEUR_INFILTRATION = auto()
    SABOTEUR_INFILTRATION_STORED = auto()
    SNAPS_BEHAVIOR_MODE = auto()
    SUMMONER_SHARED_VISION = auto()
    SNAPS_PREPARE_CASTIGATOR = auto()
    COOPERATION = auto()
    COOPERATION_USED = auto()

EFFECT_STACK_NAMES : dict[EffectStacks, str] = {
    EffectStacks.STEADY_HAND: "Steady Hand",
    EffectStacks.SUPPRESSIVE_FIRE: "Suppressive Fire",
    EffectStacks.EYES_OF_THE_DARK: "Eyes of the Dark",
    EffectStacks.UNRELENTING_ASSAULT: "Unrelenting Assault",
    EffectStacks.RAT_MARK_IMPETUOUS: "Mark of Impetuous Rat",
    EffectStacks.RAT_MARK_RESOLUTE: "Mark of Resolute Rat",
    EffectStacks.RAT_MARK_INTREPID: "Mark of Intrepid Rat",
    EffectStacks.RPS_LEVEL: "Reactive Protection System Level",
    EffectStacks.BUTTERFLY_KI: "Floating Butterfly",
    EffectStacks.SALALI_CHARGE: "Voltage",
    EffectStacks.STRIKER_TIGER: "Tiger Stance",
    EffectStacks.STRIKER_HORSE: "Horse Stance",
    EffectStacks.STRIKER_CRANE: "Crane Stance",
    EffectStacks.HORSE_INSTINCTS: "Horse Instinct",
    EffectStacks.SECRET_ART_TIGER: "Secret Art T",
    EffectStacks.SECRET_ART_HORSE: "Secret Art H",
    EffectStacks.SECRET_ART_CRANE: "Secret Art C",
    EffectStacks.SABOTEUR_INTERFERENCE: "(Saboteur) Interference",
    EffectStacks.SABOTEUR_SIPHON: "(Saboteur) Siphon",
    EffectStacks.SABOTEUR_BLACKOUT: "(Saboteur) Blackout",
    EffectStacks.SABOTEUR_TRACELESS: "(Saboteur) Traceless",
    EffectStacks.SABOTEUR_INFILTRATION: "(Saboteur) Infiltration",
    EffectStacks.COOPERATION: "Cooperation Mark"
}

NO_COUNT_DISPLAY_STACKS : set[EffectStacks] = set((
    EffectStacks.STRIKER_TIGER,
    EffectStacks.STRIKER_HORSE,
    EffectStacks.STRIKER_CRANE,
    EffectStacks.SECRET_ART_TIGER,
    EffectStacks.SECRET_ART_HORSE,
    EffectStacks.SECRET_ART_CRANE,
    EffectStacks.COOPERATION
))

""" Combat """
MAX_ACTION_TIMER = 100
DEFAULT_ATTACK_TIMER_USAGE = 70
DEFAULT_APPROACH_TIMER_USAGE = 42.5
DEFAULT_RETREAT_TIMER_USAGE = 50
DEFAULT_MULTI_REPOSITION_TIMER_USAGE = 7.5
FORMATION_ACTION_TIMER_PENALTY = 30

MAX_SINGLE_REPOSITION = 2
MAX_DISTANCE = 3
DEFAULT_STARTING_DISTANCE = 2
DEFAULT_STARTING_DISTANCE = 2

DEFEND_DAMAGE_MULTIPLIER = 0.75

BASIC_ATTACK_MP_GAIN = 4
REPOSITION_MP_GAIN = 2
DEFEND_MP_GAIN = 4
DEFEND_HIT_MP_GAIN = 3

PROXIMITY_AGGRO_BOOST = 3
HEAL_AGGRO_FACTOR = 0.2

DAMAGE_FORMULA_K = 0.5 # ratio when attack = defense
DAMAGE_FORMULA_C = 2.0 # scaling, higher means a steeper dropoff/alignment as ratio increases/decreases

ACCURACY_FORMULA_C = 1 # similar scaling factor; may not be needed

ACTION_TIME_DISPLAY_MULTIPLIER = 0.1

class ActionSuccessState(Enum):
    SUCCESS = auto()
    FAILURE_MANA = auto()
    FAILURE_TARGETS = auto()


class CombatActions(Enum):
    ATTACK = auto()
    SKILL = auto()
    APPROACH = auto()
    RETREAT = auto()
    DEFEND = auto()

""" Status """

class StatusConditionNames(Enum):
    POISON = auto()
    BURN = auto()
    BLIND = auto()
    STUN = auto()
    EXHAUSTION = auto()
    TARGET = auto()
    MISFORTUNE = auto()
    RESTRICT = auto()
    PERPLEXITY = auto()
    FEAR = auto()

BASE_DEFAULT_STATUS_TOLERANCE = 15
PER_LEVEL_DEFAULT_STATUS_TOLERANCE = 3

STATUS_TOLERANCE_RESIST_DECREASE = 15
STATUS_TOLERANCE_RECOVERY_INCREASE_FACTOR = 1.5
MAX_RESIST_STATUS_TOLERANCE = 100

DOT_STACK_SCALING = 0.75
BLIND_STACK_ACC_MULT = 0.9
EXHAUST_STACK_SCALING = 0.5
PERPLEXITY_STACK_SCALING = 0.5

""" Alchefy """

class AlchefyElements(Enum):
    WOOD = auto()
    METAL = auto()
    EARTH = auto()
    FIRESUN = auto()
    WATERMOON = auto()

ALCHEFY_ELEMENT_NAMES = {
    AlchefyElements.WOOD: "Wood",
    AlchefyElements.METAL: "Metal",
    AlchefyElements.EARTH: "Earth",
    AlchefyElements.FIRESUN: "Fire/Sun",
    AlchefyElements.WATERMOON: "Water/Moon"
}

class AlchefyProducts(Enum):
    FLOUR_FLOWER = auto()
    POLLEN_DOUGH = auto()
    BUTTERY_SILVER = auto()
    MERCURY_DRESSING = auto()
    HATCHING_STONE = auto()
    QUICKSAND_OMELET = auto()
    BREAD_DOLL = auto()
    SYLPHID_NOODLES = auto()
    BEDROCK_QUICHE = auto()
    MOLTEN_MONOSACCHARIDE = auto()
    SOLAR_SUGAR = auto()
    BASIC_BROTH = auto()
    LUNAR_LEAVENER = auto()
    CONFECTIONERS_HAZE = auto()
    NIGHTBLOOM_TEA = auto()
    ALLOY_BRULEE = auto()
    CREAM_OF_BISMUTH = auto()
    SCRAMBLED_SUNLIGHT = auto()
    POACHED_JADE = auto()
    ELIXIR_TEA = auto()

ALCHEFY_PRODUCT_NAMES = {
    AlchefyProducts.FLOUR_FLOWER: "Flour Flower",
    AlchefyProducts.POLLEN_DOUGH: "Pollen Dough",
    AlchefyProducts.BUTTERY_SILVER: "Buttery Silver",
    AlchefyProducts.MERCURY_DRESSING: "Mercury Dressing",
    AlchefyProducts.HATCHING_STONE: "Hatching Stone",
    AlchefyProducts.QUICKSAND_OMELET: "Quicksand Omelet",
    AlchefyProducts.BREAD_DOLL: "Bread Doll",
    AlchefyProducts.SYLPHID_NOODLES: "Sylphid Noodles",
    AlchefyProducts.BEDROCK_QUICHE: "Bedrock Quiche",
    AlchefyProducts.MOLTEN_MONOSACCHARIDE: "Molten Monosaccharide",
    AlchefyProducts.SOLAR_SUGAR: "Solar Sugar",
    AlchefyProducts.BASIC_BROTH: "Basic Broth",
    AlchefyProducts.LUNAR_LEAVENER: "Lunar Leavener",
    AlchefyProducts.CONFECTIONERS_HAZE: "Confectioner's Haze",
    AlchefyProducts.NIGHTBLOOM_TEA: "Night-Bloom Tea",
    AlchefyProducts.ALLOY_BRULEE: "Alloy Brûlée",
    AlchefyProducts.CREAM_OF_BISMUTH: "Cream of Bismuth",
    AlchefyProducts.SCRAMBLED_SUNLIGHT: "Scrambled Sunlight",
    AlchefyProducts.POACHED_JADE: "Poached Jade",
    AlchefyProducts.ELIXIR_TEA: "Elixir Tea of Life"
}

ALCHEFY_PRODUCT_MAP : dict[tuple[AlchefyElements] | tuple[AlchefyElements, AlchefyElements], AlchefyProducts] = {
    (AlchefyElements.WOOD,): AlchefyProducts.FLOUR_FLOWER,
    (AlchefyElements.METAL,): AlchefyProducts.BUTTERY_SILVER,
    (AlchefyElements.EARTH,): AlchefyProducts.HATCHING_STONE,
    (AlchefyElements.FIRESUN,): AlchefyProducts.MOLTEN_MONOSACCHARIDE,
    (AlchefyElements.WATERMOON,): AlchefyProducts.BASIC_BROTH,

    (AlchefyElements.WOOD, AlchefyElements.WOOD): AlchefyProducts.POLLEN_DOUGH,
    (AlchefyElements.METAL, AlchefyElements.METAL): AlchefyProducts.MERCURY_DRESSING,
    (AlchefyElements.EARTH, AlchefyElements.EARTH): AlchefyProducts.QUICKSAND_OMELET,
    (AlchefyElements.FIRESUN, AlchefyElements.FIRESUN): AlchefyProducts.SOLAR_SUGAR,
    (AlchefyElements.WATERMOON, AlchefyElements.WATERMOON): AlchefyProducts.LUNAR_LEAVENER,

    (AlchefyElements.WOOD, AlchefyElements.METAL): AlchefyProducts.BREAD_DOLL,
    (AlchefyElements.WOOD, AlchefyElements.EARTH): AlchefyProducts.SYLPHID_NOODLES,
    (AlchefyElements.WOOD, AlchefyElements.FIRESUN): AlchefyProducts.CONFECTIONERS_HAZE,
    (AlchefyElements.WOOD, AlchefyElements.WATERMOON): AlchefyProducts.NIGHTBLOOM_TEA,
    (AlchefyElements.METAL, AlchefyElements.EARTH): AlchefyProducts.BEDROCK_QUICHE,
    (AlchefyElements.METAL, AlchefyElements.FIRESUN): AlchefyProducts.ALLOY_BRULEE,
    (AlchefyElements.METAL, AlchefyElements.WATERMOON): AlchefyProducts.CREAM_OF_BISMUTH,
    (AlchefyElements.EARTH, AlchefyElements.FIRESUN): AlchefyProducts.SCRAMBLED_SUNLIGHT,
    (AlchefyElements.EARTH, AlchefyElements.WATERMOON): AlchefyProducts.POACHED_JADE,
    (AlchefyElements.FIRESUN, AlchefyElements.WATERMOON): AlchefyProducts.ELIXIR_TEA
}
apmReverseMap = {}
ALCHEFY_PRODUCT_MAP_REV : dict[AlchefyProducts, tuple[AlchefyElements] | tuple[AlchefyElements, AlchefyElements]] = {}

for combo in ALCHEFY_PRODUCT_MAP: # add reverse combinations
    ALCHEFY_PRODUCT_MAP_REV[ALCHEFY_PRODUCT_MAP[combo]] = combo
    if len(combo) == 2 and combo[0] != combo[1]:
        apmReverseMap[(combo[1], combo[0])] = ALCHEFY_PRODUCT_MAP[combo]
ALCHEFY_PRODUCT_MAP.update(apmReverseMap)


ALCHEFY_DESCRIPTIONS_BASIC = {
    AlchefyProducts.FLOUR_FLOWER: "Neutral Magic, 1.2x MAG.",
    AlchefyProducts.POLLEN_DOUGH: "Neutral Magic, 1.5x MAG. Decreases target's ACC.",
    AlchefyProducts.BUTTERY_SILVER: "Physical, 0.8x ATK. Fast attack speed.",
    AlchefyProducts.MERCURY_DRESSING: "Slashing Physical, 1.2x ATK. Fast attack speed. Decreases target's DEF/RES.",
    AlchefyProducts.HATCHING_STONE: "Physical, 1.2x ATK.",
    AlchefyProducts.QUICKSAND_OMELET: "Crushing Physical, 1.5x ATK. Decrease target's SPD.",
    AlchefyProducts.BREAD_DOLL: "Piercing Physical, 1x ATK. Attacks a random additional target with 0.9x ATK.",
    AlchefyProducts.SYLPHID_NOODLES: "Wind Magic, 1.3x MAG. Increases a random stat for all allies.",
    AlchefyProducts.BEDROCK_QUICHE: "Physical, 1.2x ATK. For 5 turns, reduces ATK/MAG/ACC of target's attacks based on distance."
}
ALCHEFY_DESCRIPTIONS_ADVANCED = {
    AlchefyProducts.MOLTEN_MONOSACCHARIDE: "Fire Magic, 1.2x MAG.",
    AlchefyProducts.SOLAR_SUGAR: "Light Magic, 1.5x MAG. Increase ACC of all allies.",
    AlchefyProducts.BASIC_BROTH: "Ice Magic, 1.2x MAG.",
    AlchefyProducts.LUNAR_LEAVENER: "Dark Magic, 1.5x MAG. Increase AVO of all allies.",
    AlchefyProducts.CONFECTIONERS_HAZE: "Neutral Magic, 1.2x MAG. Lowers a random stat of the target.",
    AlchefyProducts.NIGHTBLOOM_TEA: "Neutral Magic, 1.2x MAG. Attempts to apply a random debuff.",
    AlchefyProducts.ALLOY_BRULEE: "Physical, 1x ATK + 0.6x MAG.",
    AlchefyProducts.CREAM_OF_BISMUTH: "Physical, 1.1x ATK, 30% additional Critical Hit Rate. On crit, attack repeats once.",
    AlchefyProducts.SCRAMBLED_SUNLIGHT: "Light Magic, 0.8x MAG. For 4 turns, all allies have 25% less time between actions.",
    AlchefyProducts.POACHED_JADE: "Dark Magic, 0.6x MAG. For 4 turns, all allies have 30% reduced MP costs.",
    AlchefyProducts.ELIXIR_TEA: "Neutral Magic, 1x ATK. Heals all allies with 1.7x strength."
}

""" Summoner """

DEFAULT_SUMMON_NAMES = [
    "Snaps",
    "Mirtu",
    "Ferali",
    "Brock",
    "Allison",
    "Irwin",
    "Susie",
    "Ade",
    "Bea",
    "Later",
    "Gummy",
    "Bratty"
]

""" Equips """

class EquipmentSlot(Enum):
    WEAPON = auto()
    HAT = auto()
    OVERALL = auto()
    SHOES = auto()

class WeaponType(Enum):
    SWORD = auto()
    SPEAR = auto()
    FLAIL = auto()
    HAMMER = auto()
    SWORDSHIELD = auto()
    DAGGER = auto()
    THROWING = auto()
    ROCKS = auto()
    BOW = auto()
    CROSSBOW = auto()
    FIREARM = auto()
    WAND = auto()
    STAFF = auto()
    FOCUS = auto()

class AttackType(Enum):
    MELEE = auto()
    RANGED = auto()
    MAGIC = auto()

class AttackAttribute(Enum):
    pass

class PhysicalAttackAttribute(AttackAttribute):
    PIERCING = auto()
    SLASHING = auto()
    CRUSHING = auto()

class MagicalAttackAttribute(AttackAttribute):
    NEUTRAL = auto()
    FIRE = auto()
    ICE = auto()
    WIND = auto()
    LIGHT = auto()
    DARK = auto()

DEFAULT_ATTACK_TYPE = AttackType.MELEE
DEFAULT_ATTACK_ATTRIBUTE = PhysicalAttackAttribute.CRUSHING

itemRarityStrings = [
    "Common",
    "Uncommon",
    "Rare",
    "Epic",
    "Legendary"
]
MAX_ITEM_RARITY = 4
MAX_ITEM_RANK = 9
MAX_RANK_STAT_SCALING = 0.75

MELEE_WEAPON_TYPES : list[WeaponType] = [
    WeaponType.SWORD, WeaponType.SPEAR, WeaponType.FLAIL,
    WeaponType.SWORDSHIELD, WeaponType.HAMMER, WeaponType.DAGGER
]
RANGED_WEAPON_TYPES : list[WeaponType] = [
    WeaponType.ROCKS, WeaponType.THROWING,
    WeaponType.BOW, WeaponType.CROSSBOW, WeaponType.FIREARM
]
MAGIC_WEAPON_TYPES : list[WeaponType] = [
    WeaponType.WAND, WeaponType.STAFF, WeaponType.FOCUS
]

class WeaponTypeAttributes(object):
    def __init__(self, basicAttackType : AttackType, basicAttackAttribute : AttackAttribute, maxRange : int,
                permittedClasses : list[BasePlayerClassNames]):
        self.basicAttackType : AttackType = basicAttackType
        self.basicAttackAttribute : AttackAttribute = basicAttackAttribute
        self.maxRange : int = maxRange
        self.permittedClasses : list[BasePlayerClassNames] = permittedClasses

weaponTypeAttributeMap = {
    WeaponType.SWORD: WeaponTypeAttributes(AttackType.MELEE, PhysicalAttackAttribute.SLASHING, 1,
                                           [BasePlayerClassNames.WARRIOR]),
    WeaponType.SPEAR: WeaponTypeAttributes(AttackType.MELEE, PhysicalAttackAttribute.PIERCING, 1,
                                           [BasePlayerClassNames.WARRIOR, BasePlayerClassNames.ROGUE]),
    WeaponType.FLAIL: WeaponTypeAttributes(AttackType.MELEE, PhysicalAttackAttribute.CRUSHING, 1,
                                           [BasePlayerClassNames.WARRIOR]),
    WeaponType.HAMMER: WeaponTypeAttributes(AttackType.MELEE, PhysicalAttackAttribute.CRUSHING, 0,
                                           [BasePlayerClassNames.WARRIOR]),
    WeaponType.SWORDSHIELD: WeaponTypeAttributes(AttackType.MELEE, PhysicalAttackAttribute.SLASHING, 0,
                                           [BasePlayerClassNames.WARRIOR]),
    WeaponType.DAGGER: WeaponTypeAttributes(AttackType.MELEE, PhysicalAttackAttribute.PIERCING, 0,
                                           [BasePlayerClassNames.WARRIOR, BasePlayerClassNames.ROGUE]),
    WeaponType.THROWING: WeaponTypeAttributes(AttackType.RANGED, PhysicalAttackAttribute.SLASHING, 2,
                                           [BasePlayerClassNames.ROGUE]),
    WeaponType.ROCKS: WeaponTypeAttributes(AttackType.RANGED, PhysicalAttackAttribute.CRUSHING, 2,
                                           [BasePlayerClassNames.RANGER, BasePlayerClassNames.ROGUE]),
    WeaponType.BOW: WeaponTypeAttributes(AttackType.RANGED, PhysicalAttackAttribute.PIERCING, 2,
                                           [BasePlayerClassNames.RANGER, BasePlayerClassNames.ROGUE]),
    WeaponType.CROSSBOW: WeaponTypeAttributes(AttackType.RANGED, PhysicalAttackAttribute.PIERCING, 3,
                                           [BasePlayerClassNames.RANGER, BasePlayerClassNames.ROGUE]),
    WeaponType.FIREARM: WeaponTypeAttributes(AttackType.RANGED, PhysicalAttackAttribute.PIERCING, 3,
                                           [BasePlayerClassNames.RANGER]),
    WeaponType.WAND: WeaponTypeAttributes(AttackType.MELEE, PhysicalAttackAttribute.CRUSHING, 0,
                                           [BasePlayerClassNames.MAGE]),
    WeaponType.STAFF: WeaponTypeAttributes(AttackType.MELEE, PhysicalAttackAttribute.CRUSHING, 1,
                                           [BasePlayerClassNames.MAGE]),
    WeaponType.FOCUS: WeaponTypeAttributes(AttackType.MAGIC, MagicalAttackAttribute.NEUTRAL, 1,
                                           [BasePlayerClassNames.MAGE]),
}

class EquipAttributes(object):
    def __init__(self, name : str, equipSlot : EquipmentSlot, baseStats: dict[BaseStats, int], bonusTrait : bool) -> None:
        self.name : str = name
        self.equipSlot : EquipmentSlot = equipSlot
        self.baseStats : dict[BaseStats, int] = baseStats.copy()
        self.bonusTrait : bool = bonusTrait

class WeaponAttributes(EquipAttributes):
    def __init__(self, name : str, weaponType: WeaponType, baseStats: dict[BaseStats, int]) -> None:
        super().__init__(name, EquipmentSlot.WEAPON, baseStats, False)
        self.weaponType : WeaponType = weaponType

class EquipClass(Enum):
    pass

class WeaponClasses(EquipClass):
    BROADSWORD = auto(),
    KATANA = auto(),
    SABRE = auto(),
    SPEAR = auto(),
    NAGINATA = auto(),
    SCYTHE = auto(),
    MACE = auto(),
    MORNINGSTAR = auto(),
    FLAIL = auto(),
    OTSUCHI = auto(),
    WARHAMMER = auto(),
    DIVINEHAMMER = auto(),
    KITESHIELDSWORD = auto(),
    TOWERSHIELDSWORD = auto(),
    BUCKLERSWORD = auto(),
    DAGGER = auto(),
    STILETTO = auto(),
    DIRK = auto(),
    THROWINGKNIVES = auto(),
    SHURIKENS = auto(),
    SLINGSHOT = auto(),
    SHOTPUTS = auto(),
    BOLAS = auto(),
    BOOMERANG = auto(),
    RECURVEBOW = auto(),
    COMPOUNDBOW = auto(),
    LONGBOW = auto(),
    RECURVECROSSBOW = auto(),
    COMPOUNDCROSSBOW = auto(),
    PISTOLCROSSBOW = auto(),
    RIFLE = auto(),
    HANDGUN = auto(),
    LAUNCHER = auto(),
    EMBEDDEDWAND = auto(),
    WOODENWAND = auto(),
    STEELWAND = auto(),
    GEMSTONESTAFF = auto(),
    WOODENSTAFF = auto(),
    HYBRIDSTAFF = auto(),
    AMULET = auto(),
    CRYSTAL = auto(),
    TOME = auto()
    
weaponClassAttributeMap : dict[WeaponClasses, WeaponAttributes] = {
    WeaponClasses.BROADSWORD: WeaponAttributes("Broadsword", WeaponType.SWORD,
            {BaseStats.ATK: 10, BaseStats.ACC: 10, BaseStats.SPD: 5}),
    WeaponClasses.KATANA: WeaponAttributes("Katana", WeaponType.SWORD,
            {BaseStats.ATK: 7, BaseStats.MAG: 3, BaseStats.DEF: 2, BaseStats.RES: 2, BaseStats.ACC: 8, BaseStats.AVO: 2, BaseStats.SPD: 4}),
    WeaponClasses.SABRE: WeaponAttributes("Sabre", WeaponType.SWORD,
            {BaseStats.ATK: 8, BaseStats.ACC: 12, BaseStats.SPD: 6}),
    WeaponClasses.SPEAR: WeaponAttributes("Spear", WeaponType.SPEAR,
            {BaseStats.ATK: 7, BaseStats.ACC: 8, BaseStats.AVO: 5, BaseStats.SPD: 6}),
    WeaponClasses.NAGINATA: WeaponAttributes("Naginata", WeaponType.SPEAR,
            {BaseStats.ATK: 5, BaseStats.ACC: 8, BaseStats.AVO: 8, BaseStats.SPD: 7}),
    WeaponClasses.SCYTHE: WeaponAttributes("Scythe", WeaponType.SPEAR,
            {BaseStats.ATK: 8, BaseStats.MAG: 3, BaseStats.ACC: 9, BaseStats.AVO: 4, BaseStats.SPD: 5}),
    WeaponClasses.MORNINGSTAR: WeaponAttributes("Morning Star", WeaponType.FLAIL,
            {BaseStats.ATK: 13, BaseStats.ACC: 8, BaseStats.SPD: 2}),
    WeaponClasses.FLAIL: WeaponAttributes("Flail", WeaponType.FLAIL,
            {BaseStats.ATK: 16, BaseStats.ACC: 3, BaseStats.SPD: 2}),
    WeaponClasses.MACE: WeaponAttributes("Mace", WeaponType.FLAIL,
            {BaseStats.ATK: 12, BaseStats.ACC: 6, BaseStats.SPD: 3}),
    WeaponClasses.OTSUCHI: WeaponAttributes("Otsuchi", WeaponType.HAMMER,
            {BaseStats.ATK: 15, BaseStats.ACC: 12, BaseStats.SPD: 4}),
    WeaponClasses.WARHAMMER: WeaponAttributes("War Hammer", WeaponType.HAMMER,
            {BaseStats.ATK: 18, BaseStats.ACC: 9, BaseStats.SPD: 2}),
    WeaponClasses.DIVINEHAMMER: WeaponAttributes("Divine Hammer", WeaponType.HAMMER,
            {BaseStats.ATK: 12, BaseStats.MAG: 6, BaseStats.RES: 5, BaseStats.ACC: 10, BaseStats.SPD: 3}),
    WeaponClasses.KITESHIELDSWORD: WeaponAttributes("Kite Shield & Sword", WeaponType.SWORDSHIELD,
            {BaseStats.ATK: 10, BaseStats.DEF: 5, BaseStats.ACC: 10, BaseStats.SPD: 4}),
    WeaponClasses.TOWERSHIELDSWORD: WeaponAttributes("Tower Shield & Sword", WeaponType.SWORDSHIELD,
            {BaseStats.ATK: 8, BaseStats.DEF: 8, BaseStats.ACC: 10, BaseStats.SPD: 2}),
    WeaponClasses.BUCKLERSWORD: WeaponAttributes("Buckler & Sword", WeaponType.SWORDSHIELD,
            {BaseStats.ATK: 7, BaseStats.DEF: 4, BaseStats.ACC: 10, BaseStats.SPD: 7}),
    WeaponClasses.DAGGER: WeaponAttributes("Dagger", WeaponType.DAGGER,
            {BaseStats.ATK: 6, BaseStats.ACC: 13, BaseStats.SPD: 10}),
    WeaponClasses.STILETTO: WeaponAttributes("Stiletto", WeaponType.DAGGER,
            {BaseStats.ATK: 4, BaseStats.ACC: 15, BaseStats.SPD: 15}),
    WeaponClasses.DIRK: WeaponAttributes("Dirk", WeaponType.DAGGER,
            {BaseStats.ATK: 5, BaseStats.ACC: 13, BaseStats.AVO: 4, BaseStats.SPD: 8}),
    WeaponClasses.THROWINGKNIVES: WeaponAttributes("Throwing Knives", WeaponType.THROWING,
            {BaseStats.ATK: 5, BaseStats.ACC: 8, BaseStats.SPD: 12}),
    WeaponClasses.SHURIKENS: WeaponAttributes("Shurikens", WeaponType.THROWING,
            {BaseStats.ATK: 3, BaseStats.ACC: 8, BaseStats.SPD: 15}),
    WeaponClasses.BOOMERANG: WeaponAttributes("Boomerang", WeaponType.THROWING,
            {BaseStats.MP: 2, BaseStats.ATK: 5, BaseStats.ACC: 9, BaseStats.SPD: 8}),
    WeaponClasses.SLINGSHOT: WeaponAttributes("Slingshot", WeaponType.ROCKS,
            {BaseStats.ATK: 6, BaseStats.ACC: 9, BaseStats.SPD: 10}),
    WeaponClasses.SHOTPUTS: WeaponAttributes("Shotputs", WeaponType.ROCKS,
            {BaseStats.ATK: 9, BaseStats.ACC: 7, BaseStats.SPD: 7}),
    WeaponClasses.BOLAS: WeaponAttributes("Bolas", WeaponType.ROCKS,
            {BaseStats.ATK: 5, BaseStats.MAG: 4, BaseStats.ACC: 9, BaseStats.AVO: 3, BaseStats.SPD: 8}),
    WeaponClasses.RECURVEBOW: WeaponAttributes("Recurve Bow", WeaponType.BOW,
            {BaseStats.ATK: 6, BaseStats.ACC: 9, BaseStats.SPD: 10}),
    WeaponClasses.COMPOUNDBOW: WeaponAttributes("Compound Bow", WeaponType.BOW,
            {BaseStats.ATK: 8, BaseStats.ACC: 8, BaseStats.SPD: 8}),
    WeaponClasses.LONGBOW: WeaponAttributes("Longbow", WeaponType.BOW,
            {BaseStats.ATK: 6, BaseStats.MAG: 3, BaseStats.ACC: 9, BaseStats.AVO: 3, BaseStats.SPD: 7}),
    WeaponClasses.RECURVECROSSBOW: WeaponAttributes("Recurve Crossbow", WeaponType.CROSSBOW,
            {BaseStats.ATK: 9, BaseStats.ACC: 12, BaseStats.SPD: 5}),
    WeaponClasses.COMPOUNDCROSSBOW: WeaponAttributes("Compound Crossbow", WeaponType.CROSSBOW,
            {BaseStats.ATK: 12, BaseStats.ACC: 12, BaseStats.SPD: 2}),
    WeaponClasses.PISTOLCROSSBOW: WeaponAttributes("Pistol Crossbow", WeaponType.CROSSBOW,
            {BaseStats.ATK: 8, BaseStats.MAG: 4, BaseStats.ACC: 10, BaseStats.SPD: 6}),
    WeaponClasses.RIFLE: WeaponAttributes("Rifle", WeaponType.FIREARM,
            {BaseStats.ATK: 14, BaseStats.ACC: 6, BaseStats.SPD: 2}),
    WeaponClasses.HANDGUN: WeaponAttributes("Handgun", WeaponType.FIREARM,
            {BaseStats.ATK: 10, BaseStats.ACC: 5, BaseStats.SPD: 5}),
    WeaponClasses.LAUNCHER: WeaponAttributes("Launcher", WeaponType.FIREARM,
            {BaseStats.ATK: 16, BaseStats.ACC: 10}),
    WeaponClasses.EMBEDDEDWAND: WeaponAttributes("Embedded Wand", WeaponType.WAND,
            {BaseStats.ATK: 2, BaseStats.MAG: 10, BaseStats.ACC: 10, BaseStats.SPD: 7}),
    WeaponClasses.WOODENWAND: WeaponAttributes("Wooden Wand", WeaponType.WAND,
            {BaseStats.ATK: 2, BaseStats.MAG: 8, BaseStats.ACC: 7, BaseStats.SPD: 10}),
    WeaponClasses.STEELWAND: WeaponAttributes("Steel Wand", WeaponType.WAND,
            {BaseStats.ATK: 2, BaseStats.MAG: 8, BaseStats.ACC: 13, BaseStats.SPD: 7}),
    WeaponClasses.GEMSTONESTAFF: WeaponAttributes("Gemstone Staff", WeaponType.STAFF,
            {BaseStats.ATK: 4, BaseStats.MAG: 15, BaseStats.ACC: 10, BaseStats.SPD: 3}),
    WeaponClasses.WOODENSTAFF: WeaponAttributes("Wooden Staff", WeaponType.STAFF,
            {BaseStats.ATK: 4, BaseStats.MAG: 10, BaseStats.DEF: 3, BaseStats.RES: 3, BaseStats.ACC: 9, BaseStats.SPD: 2}),
    WeaponClasses.HYBRIDSTAFF: WeaponAttributes("Hybrid Staff", WeaponType.STAFF,
            {BaseStats.ATK: 8, BaseStats.MAG: 9, BaseStats.ACC: 10, BaseStats.SPD: 5}),
    WeaponClasses.AMULET: WeaponAttributes("Amulet", WeaponType.FOCUS,
            {BaseStats.MAG: 6, BaseStats.RES: 4, BaseStats.ACC: 7, BaseStats.SPD: 6}),
    WeaponClasses.CRYSTAL: WeaponAttributes("Crystal", WeaponType.FOCUS,
            {BaseStats.MAG: 5, BaseStats.RES: 5, BaseStats.ACC: 5, BaseStats.SPD: 7}),
    WeaponClasses.TOME: WeaponAttributes("Tome", WeaponType.FOCUS,
            {BaseStats.MAG: 9, BaseStats.ACC: 8, BaseStats.SPD: 6}),
}

class HatClasses(EquipClass):
    ARMET = auto(),
    KETTLEHELM = auto(),
    GREATHELM = auto(),
    CIRCLET = auto(),
    TOPHAT = auto(),
    WIZARDHAT = auto(),
    VISORHELMET = auto(),
    GLASSES = auto(),
    PARTEDVEIL = auto(),
    HELMET = auto(),
    SLEEPINGCAP = auto()

hatClassAttributeMap : dict[HatClasses, EquipAttributes] = {
    HatClasses.ARMET: EquipAttributes("Armet", EquipmentSlot.HAT,
            {BaseStats.HP: 50, BaseStats.DEF: 8}, False),
    HatClasses.KETTLEHELM: EquipAttributes("Kettle Helm", EquipmentSlot.HAT,
            {BaseStats.HP: 80, BaseStats.DEF: 2}, False),
    HatClasses.GREATHELM: EquipAttributes("Great Helm", EquipmentSlot.HAT,
            {BaseStats.DEF: 12}, False),
    HatClasses.CIRCLET: EquipAttributes("Circlet", EquipmentSlot.HAT,
            {BaseStats.MP: 5, BaseStats.RES: 8}, False),
    HatClasses.TOPHAT: EquipAttributes("Top Hat", EquipmentSlot.HAT,
            {BaseStats.HP: 20, BaseStats.MP: 5}, False),
    HatClasses.WIZARDHAT: EquipAttributes("Wizard Hat", EquipmentSlot.HAT,
            {BaseStats.DEF: 2, BaseStats.RES: 10}, False),
    HatClasses.VISORHELMET: EquipAttributes("Visor Helmet", EquipmentSlot.HAT,
            {BaseStats.DEF: 2, BaseStats.ACC: 10}, False),
    HatClasses.GLASSES: EquipAttributes("Glasses", EquipmentSlot.HAT,
            {BaseStats.HP: 20, BaseStats.ACC: 8}, False),
    HatClasses.PARTEDVEIL: EquipAttributes("Parted Veil", EquipmentSlot.HAT,
            {BaseStats.RES: 2, BaseStats.ACC: 10}, False),
    HatClasses.HELMET: EquipAttributes("Helmet", EquipmentSlot.HAT,
            {BaseStats.HP: 10, BaseStats.DEF: 4, BaseStats.RES: 4, BaseStats.ACC: 5}, False),
    HatClasses.SLEEPINGCAP: EquipAttributes("Sleeping Cap", EquipmentSlot.HAT,
            {BaseStats.DEF: 4, BaseStats.RES: 4, BaseStats.ACC: 3}, True)
}

class OverallClasses(EquipClass):
    PLATEARMOR = auto(),
    SCALEMAIL = auto(),
    LEATHERARMOR = auto(),
    SORCERERCOAT = auto(),
    LEATHERROBES = auto(),
    SILKCLOAK = auto(),
    OUTFIT = auto(),
    COSTUME = auto()

overallClassAttributeMap : dict[OverallClasses, EquipAttributes] = {
    OverallClasses.PLATEARMOR: EquipAttributes("Plate Armor", EquipmentSlot.OVERALL,
            {BaseStats.DEF: 10}, False),
    OverallClasses.SCALEMAIL: EquipAttributes("Scale Mail", EquipmentSlot.OVERALL,
            {BaseStats.DEF: 8, BaseStats.SPD: 2}, False),
    OverallClasses.LEATHERARMOR: EquipAttributes("Leather Armor", EquipmentSlot.OVERALL,
            {BaseStats.HP: 15, BaseStats.DEF: 6, BaseStats.SPD: 2}, False),
    OverallClasses.SORCERERCOAT: EquipAttributes("Sorcerer's Coat", EquipmentSlot.OVERALL,
            {BaseStats.RES: 12}, False),
    OverallClasses.LEATHERROBES: EquipAttributes("Leather Robes", EquipmentSlot.OVERALL,
            {BaseStats.MP: 5, BaseStats.RES: 8, BaseStats.SPD: 2}, False),
    OverallClasses.SILKCLOAK: EquipAttributes("Silk Cloak", EquipmentSlot.OVERALL,
            {BaseStats.RES: 6, BaseStats.SPD: 4}, False),
    OverallClasses.OUTFIT: EquipAttributes("Outfit", EquipmentSlot.OVERALL,
            {BaseStats.DEF: 4, BaseStats.RES: 4, BaseStats.AVO: 3, BaseStats.SPD: 3}, False),
    OverallClasses.COSTUME: EquipAttributes("Costume", EquipmentSlot.OVERALL,
            {BaseStats.DEF: 3, BaseStats.RES: 3, BaseStats.SPD: 2}, True)
}

class ShoeClasses(EquipClass):
    BALLETSHOES = auto(),
    MOCCASINS = auto(),
    SANDALS = auto(),
    BAREFOOTSHOES = auto(),
    CUSHIONEDSHOES = auto(),
    SNEAKERS = auto(),
    BOOTS = auto(),
    SLIPPERS = auto()

shoeClassAttributeMap : dict[ShoeClasses, EquipAttributes] = {
    ShoeClasses.BALLETSHOES: EquipAttributes("Ballet Shoes", EquipmentSlot.SHOES,
            {BaseStats.AVO: 10}, False),
    ShoeClasses.MOCCASINS: EquipAttributes("Moccasins", EquipmentSlot.SHOES,
            {BaseStats.AVO: 6, BaseStats.SPD: 3}, False),
    ShoeClasses.SANDALS: EquipAttributes("Sandals", EquipmentSlot.SHOES,
            {BaseStats.AVO: 5, BaseStats.RES: 2, BaseStats.SPD: 2}, False),
    ShoeClasses.BAREFOOTSHOES: EquipAttributes("Barefoot Shoes", EquipmentSlot.SHOES,
            {BaseStats.SPD: 6}, False),
    ShoeClasses.CUSHIONEDSHOES: EquipAttributes("Cushioned Shoes", EquipmentSlot.SHOES,
            {BaseStats.HP: 15, BaseStats.SPD: 3}, False),
    ShoeClasses.SNEAKERS: EquipAttributes("Sneakers", EquipmentSlot.SHOES,
            {BaseStats.ACC: 2, BaseStats.AVO: 2, BaseStats.SPD: 4}, False),
    ShoeClasses.BOOTS: EquipAttributes("Boots", EquipmentSlot.SHOES,
            {BaseStats.DEF: 2, BaseStats.RES: 2, BaseStats.AVO: 2, BaseStats.SPD: 2}, False),
    ShoeClasses.SLIPPERS: EquipAttributes("Slippers", EquipmentSlot.SHOES,
            {BaseStats.AVO: 2, BaseStats.SPD: 1}, True)
}

def getEquipClassAttributes(equipClass: EquipClass) -> EquipAttributes:
    if isinstance(equipClass, WeaponClasses):
        return weaponClassAttributeMap[equipClass]
    elif isinstance(equipClass, HatClasses):
        return hatClassAttributeMap[equipClass]
    elif isinstance(equipClass, OverallClasses):
        return overallClassAttributeMap[equipClass]
    elif isinstance(equipClass, ShoeClasses):
        return shoeClassAttributeMap[equipClass]
    assert(False)

EQUIP_CURSE_CHANCE = 0.15

MAX_INVENTORY = 16

""" Progression """

MAX_PLAYER_LEVEL = 20
EXP_TO_NEXT_PLAYER_LEVEL = [
    5, 45, 120, 160, 310,
    330, 350, 380, 430, 600,
    640, 690, 760, 850, 1000,
    1100, 1250, 1400, 1600
]

EXP_TO_NEXT_BASE_CLASS_RANK = [1, 4]
EXP_TO_NEXT_ADVANCED_CLASS_RANK = [
    10, 15, 45, 70, 100,
    300, 500, 1000
]

STAT_POINTS_PER_LEVEL = 3

class Milestones(Enum):
    TUTORIAL_COMPLETE = auto()
    FRESH_FIELDS_COMPLETE = auto()
    SKYLIGHT_CAVE_COMPLETE = auto()
    SAFFRON_FOREST_COMPLTE = auto()
    ABANDONED_STOREHOUSE_COMPLETE = auto()
    CLASS_STRIKER_UNLOCKED = auto()
    CLASS_ALCHEFIST_UNLOCKED = auto()
    CLASS_SABOTEUR_UNLOCKED = auto()
    CLASS_SUMMONER_UNLOCKED = auto()
    NULL = auto()

MAX_USER_CHARACTERS = 4
MAX_NAME_LENGTH = 15

ITEM_RANK_INCREASE_COST = [
    [(1, 0), (1, 0), (1, 0), (2, 0), (2, 0), (2, 0), (3, 0), (3, 0), (3, 0)],
    [(3, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0), (8, 0), (9, 0), (10, 0)],
    [(10, 0), (12, 0), (14, 0), (16, 0), (18, 0), (20, 0), (22, 0), (24, 0), (26, 0)],
    [(30, 0), (35, 0), (40, 0), (45, 0), (50, 0), (55, 0), (60, 0), (65, 0), (70, 0)],
    [(100, 5), (125, 5), (150, 10), (200, 10), (250, 15), (300, 15), (400, 20), (500, 20), (600, 25)]
]
ITEM_RARITY_INCREASE_COST = [(10, 1), (40, 5), (100, 10), (300, 30)]
BASE_TRAIT_CHANGE_SWUP_COST = 8
TRAIT_CHANGE_COST_MULT = 1.6
BASE_RARITY_SALE_PRICE = [(1, 0), (5, 1), (20, 3), (50, 6), (200, 18)]
CURSE_SALE_BONUS_MULT = 1.25
ADAPTABLE_SALE_BONUS_MULT = 1.1

WEAPON_BONUS_TRAIT_LEVELS = [0, 2, 4]
NONWEAPON_BONUS_TRAIT_LEVELS = [0, 3]

""" Logging """

class MessageType(Enum):
    DEBUG = auto()
    BASIC = auto()
    DIALOGUE = auto()
    TELEGRAPH = auto()
    ACTION = auto()
    DAMAGE = auto()
    MANA = auto()
    POSITIONING = auto()
    EXPIRATION = auto()
    EFFECT = auto()
    PROBABILITY = auto()

TOGGLE_LOG_FILTER_DEFAULTS : dict[MessageType, bool] = {
    MessageType.DEBUG: False,
    MessageType.DIALOGUE: True,
    MessageType.ACTION: True,
    MessageType.DAMAGE: True,
    MessageType.MANA: False,
    MessageType.POSITIONING: True,
    MessageType.EXPIRATION: True,
    MessageType.EFFECT: True,
    MessageType.PROBABILITY: True
}

DISPLAY_LOG_THRESHOLD = 1024

""" Data and Persistence """

TMP_FOLDER = "./tmp/"
COMBAT_LOG_FILE_PREFIX = TMP_FOLDER + "combat_log_"
STATE_FILE_FOLDER = "./saves/"
STATE_FILE_NAME = "saveState_"
STATE_FILE_PREFIX = STATE_FILE_FOLDER + STATE_FILE_NAME
BACKUP_INTERVAL_SECONDS = 600
STATE_ARCHIVE_FOLDER = STATE_FILE_FOLDER + "recent/"
ARCHIVE_SIZE = 60