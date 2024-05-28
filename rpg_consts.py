from enum import Enum, auto

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
    DAMAGE_REDUCTION = auto()

baseCombatStats : dict[CombatStats, float] = {
    CombatStats.CRIT_RATE: 0.1,
    CombatStats.CRIT_DAMAGE: 2.5,
    CombatStats.AGGRO_MULT: 1,
    CombatStats.RANGE: 0,
    CombatStats.DAMAGE_REDUCTION: 0
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

""" Effects """

class EffectTimings(Enum):
    IMMEDIATE = auto()
    BEFORE_ATTACK = auto()
    AFTER_ATTACK = auto()
    WHEN_ATTACKED = auto()

""" Combat """
MAX_ACTION_TIMER = 100
DEFAULT_ATTACK_TIMER_USAGE = 70

BASIC_ATTACK_MP_GAIN = 4

DAMAGE_FORMULA_K = 0.5 # ratio when attack = defense
DAMAGE_FORMULA_C = 2 # scaling, higher means a steeper dropoff/alignment as ratio increases/decreases

ACCURACY_FORMULA_C = 1 # similar scaling factor; may not be needed

ACTION_TIME_DISPLAY_MULTIPLIER = 0.08

class ActionSuccessState(Enum):
    SUCCESS = auto()
    FAILURE_MANA = auto()
    FAILURE_RANGE = auto()