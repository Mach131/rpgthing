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

def _makeBasicDrop(rng : random.Random, rarity : int, minRank : int, maxRank : int, weaponChance : float):
    possibleEquipSlots = [EquipmentSlot.HAT, EquipmentSlot.OVERALL, EquipmentSlot.SHOES]
    equipSlot = rng.choice(possibleEquipSlots)
    if weaponChance > 0 and rng.random() < weaponChance:
        equipSlot = EquipmentSlot.WEAPON

    generatorFn = {
        EquipmentSlot.WEAPON: generateWeapon,
        EquipmentSlot.HAT: generateHat,
        EquipmentSlot.OVERALL: generateOverall,
        EquipmentSlot.SHOES: generateShoes
    }[equipSlot]
    chosenRank = rng.randint(minRank, maxRank)
    return generatorFn(rarity, chosenRank, None, 0)

def makeBasicCommonDrop(rng : random.Random, minRank : int, maxRank : int, weaponChance : float):
    return _makeBasicDrop(rng, 0, minRank, maxRank, weaponChance)

def makeBasicUncommonDrop(rng : random.Random, minRank : int, maxRank : int, weaponChance : float):
    return _makeBasicDrop(rng, 1, minRank, maxRank, weaponChance)