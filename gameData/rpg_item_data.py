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

def makeBasicCommonDrop(rng : random.Random, minRank : int, maxRank : int, weaponPossible : bool):
    possibleEquipSlots = [EquipmentSlot.HAT, EquipmentSlot.OVERALL, EquipmentSlot.SHOES]
    if weaponPossible:
        possibleEquipSlots.append(EquipmentSlot.WEAPON)
    equipSlot = rng.choice(possibleEquipSlots)

    generatorFn = {
        EquipmentSlot.WEAPON: generateWeapon,
        EquipmentSlot.HAT: generateHat,
        EquipmentSlot.OVERALL: generateOverall,
        EquipmentSlot.SHOES: generateShoes
    }[equipSlot]
    chosenRank = rng.randint(minRank, maxRank)
    return generatorFn(0, chosenRank, None, 0)

def makeBasicUncommonDrop(rng : random.Random, minRank : int, maxRank : int, weaponPossible : bool):
    possibleEquipSlots = [EquipmentSlot.HAT, EquipmentSlot.OVERALL, EquipmentSlot.SHOES]
    if weaponPossible:
        possibleEquipSlots.append(EquipmentSlot.WEAPON)
    equipSlot = rng.choice(possibleEquipSlots)

    generatorFn = {
        EquipmentSlot.WEAPON: generateWeapon,
        EquipmentSlot.HAT: generateHat,
        EquipmentSlot.OVERALL: generateOverall,
        EquipmentSlot.SHOES: generateShoes
    }[equipSlot]
    chosenRank = rng.randint(minRank, maxRank)
    return generatorFn(1, chosenRank, None, 0)