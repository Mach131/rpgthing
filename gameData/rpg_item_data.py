import random
from rpg_consts import *
from structures.rpg_items import *

## Special item generators definitions
def makeBeginnerWeapon(playerClass : BasePlayerClassNames):
    weaponName, weaponClass = {
        BasePlayerClassNames.WARRIOR: ("Training Sword", WeaponClasses.BROADSWORD),
        BasePlayerClassNames.RANGER: ("Training Bow", WeaponClasses.LONGBOW),
        BasePlayerClassNames.ROGUE: ("Training Knife", WeaponClasses.DAGGER),
        BasePlayerClassNames.MAGE: ("Training Wand", WeaponClasses.WOODENWAND)
    }[playerClass]
    weaponClassAttributes = weaponClassAttributeMap[weaponClass]
    return Weapon(weaponName, weaponClassAttributes.weaponType, weaponClassAttributes.baseStats, None,
                  [], 0, 0, True, (0, 0))

for weaponType in WeaponType:
    assert(weaponType in MELEE_WEAPON_TYPES or weaponType in RANGED_WEAPON_TYPES or weaponType in MAGIC_WEAPON_TYPES)
def getWeaponClasses(weaponTypes : list[WeaponType]) -> list[WeaponClasses]:
    return [weaponClass for weaponClass in WeaponClasses
                if weaponClassAttributeMap[weaponClass].weaponType in weaponTypes]

def _makeBasicDrop(rng : random.Random, rarity : int, minRank : int, maxRank : int, weaponChance : float,
                    possibleWeaponClasses : list[WeaponClasses] | None = None) -> Equipment:
    possibleEquipSlots = [EquipmentSlot.HAT, EquipmentSlot.OVERALL, EquipmentSlot.SHOES]
    chosenRank = rng.randint(minRank, maxRank)
    equipSlot = rng.choice(possibleEquipSlots)

    if weaponChance > 0 and rng.random() < weaponChance:
        weaponClass = None
        if possibleWeaponClasses is not None:
            weaponClass = rng.choice(possibleWeaponClasses)
        return generateWeapon(rarity, chosenRank, weaponClass, 0)
    else:
        generatorFn = {
            EquipmentSlot.HAT: generateHat,
            EquipmentSlot.OVERALL: generateOverall,
            EquipmentSlot.SHOES: generateShoes
        }[equipSlot]
        return generatorFn(rarity, chosenRank, None, 0)

def makeBasicCommonDrop(rng : random.Random, minRank : int, maxRank : int, weaponChance : float,
                    possibleWeaponClasses : list[WeaponClasses] | None = None):
    return _makeBasicDrop(rng, 0, minRank, maxRank, weaponChance, possibleWeaponClasses)

def makeBasicUncommonDrop(rng : random.Random, minRank : int, maxRank : int, weaponChance : float,
                    possibleWeaponClasses : list[WeaponClasses] | None = None):
    return _makeBasicDrop(rng, 1, minRank, maxRank, weaponChance, possibleWeaponClasses)