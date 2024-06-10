from rpg_consts import *
from structures.rpg_items import Weapon, luckTrait

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
                  [luckTrait], 0, 0)