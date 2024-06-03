from enum import Enum, auto

def void(x):
    return None

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
    REPOSITION_ACTION_TIME_MULT = auto()

class SpecialStats(Stats):
    CURRENT_HP = auto()
    CURRENT_MP = auto()

baseCombatStats : dict[CombatStats, float] = {
    CombatStats.CRIT_RATE: 0.1,
    CombatStats.CRIT_DAMAGE: 2.5,
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
    CombatStats.REPOSITION_ACTION_TIME_MULT: 1
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
    PARRY = auto()
    START_TURN = auto()
    END_TURN = auto()

class EffectStacks(Enum):
    STEADY_HAND = auto()
    SUPPRESSIVE_FIRE = auto()

EFFECT_STACK_NAMES : dict[EffectStacks, str] = {
    EffectStacks.STEADY_HAND: "Steady Hand",
    EffectStacks.SUPPRESSIVE_FIRE: "Suppressive Fire"
}

""" Combat """
MAX_ACTION_TIMER = 100
DEFAULT_ATTACK_TIMER_USAGE = 70
DEFAULT_APPROACH_TIMER_USAGE = 42.5
DEFAULT_RETREAT_TIMER_USAGE = 50
DEFAULT_MULTI_REPOSITION_TIMER_USAGE = 7.5

MAX_SINGLE_REPOSITION = 2
MAX_DISTANCE = 3
DEFAULT_STARTING_DISTANCE = 2

DEFEND_DAMAGE_MULTIPLIER = 0.75

BASIC_ATTACK_MP_GAIN = 4
REPOSITION_MP_GAIN = 2
DEFEND_MP_GAIN = 3
DEFEND_HIT_MP_GAIN = 2

DAMAGE_FORMULA_K = 0.5 # ratio when attack = defense
DAMAGE_FORMULA_C = 2.0 # scaling, higher means a steeper dropoff/alignment as ratio increases/decreases

ACCURACY_FORMULA_C = 1 # similar scaling factor; may not be needed

ACTION_TIME_DISPLAY_MULTIPLIER = 0.08

class ActionSuccessState(Enum):
    SUCCESS = auto()
    FAILURE_MANA = auto()
    FAILURE_TARGETS = auto()

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

BASE_DEFAULT_STATUS_TOLERANCE = 20
PER_LEVEL_DEFAULT_STATUS_TOLERANCE = 4

STATUS_TOLERANCE_RESIST_DECREASE = 15
STATUS_TOLERANCE_RECOVERY_INCREASE_FACTOR = 1.5
MAX_RESIST_STATUS_TOLERANCE = 100

DOT_STACK_SCALING = 0.75
BLIND_STACK_ACC_MULT = 0.9
EXHAUST_STACK_SCALING = 0.5
PERPLEXITY_STACK_SCALING = 0.5

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
MAX_ITEM_RANK = 10
MAX_RANK_STAT_SCALING = 0.75

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
            {BaseStats.ATK: 7, BaseStats.DEF: 2, BaseStats.RES: 2, BaseStats.ACC: 8, BaseStats.AVO: 2, BaseStats.SPD: 4}),
    WeaponClasses.SABRE: WeaponAttributes("Sabre", WeaponType.SWORD,
            {BaseStats.ATK: 8, BaseStats.ACC: 12, BaseStats.SPD: 6}),
    WeaponClasses.SPEAR: WeaponAttributes("Spear", WeaponType.SPEAR,
            {BaseStats.ATK: 7, BaseStats.ACC: 8, BaseStats.AVO: 5, BaseStats.SPD: 6}),
    WeaponClasses.NAGINATA: WeaponAttributes("Naginata", WeaponType.SPEAR,
            {BaseStats.ATK: 5, BaseStats.ACC: 8, BaseStats.AVO: 8, BaseStats.SPD: 7}),
    WeaponClasses.SCYTHE: WeaponAttributes("Scythe", WeaponType.SPEAR,
            {BaseStats.ATK: 8, BaseStats.ACC: 9, BaseStats.AVO: 4, BaseStats.SPD: 5}),
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
    WeaponClasses.RECURVEBOW: WeaponAttributes("Recurve Bow", WeaponType.BOW,
            {BaseStats.ATK: 6, BaseStats.ACC: 9, BaseStats.SPD: 10}),
    WeaponClasses.COMPOUNDBOW: WeaponAttributes("Compound Bow", WeaponType.BOW,
            {BaseStats.ATK: 8, BaseStats.ACC: 8, BaseStats.SPD: 8}),
    WeaponClasses.LONGBOW: WeaponAttributes("Longbow", WeaponType.BOW,
            {BaseStats.ATK: 6, BaseStats.ACC: 9, BaseStats.AVO: 3, BaseStats.SPD: 7}),
    WeaponClasses.RECURVECROSSBOW: WeaponAttributes("Recurve Crossbow", WeaponType.CROSSBOW,
            {BaseStats.ATK: 9, BaseStats.ACC: 12, BaseStats.SPD: 5}),
    WeaponClasses.COMPOUNDCROSSBOW: WeaponAttributes("Compound Crossbow", WeaponType.CROSSBOW,
            {BaseStats.ATK: 12, BaseStats.ACC: 12, BaseStats.SPD: 2}),
    WeaponClasses.PISTOLCROSSBOW: WeaponAttributes("Pistol Crossbow", WeaponType.CROSSBOW,
            {BaseStats.ATK: 8, BaseStats.ACC: 10, BaseStats.SPD: 6}),
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
            {BaseStats.DEF: 4, BaseStats.RES: 4, BaseStats.SPD: 2}, True)
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
            {BaseStats.AVO: 2, BaseStats.SPD: 2}, True)
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