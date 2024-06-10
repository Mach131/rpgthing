from gameData.rpg_item_data import makeBeginnerWeapon
from rpg_consts import *
from structures.rpg_combat_entity import *
from structures.rpg_items import *

### randomly generated classes

def rerollWeapon(player : Player, testRarity : int = 0):
    weaponClass = random.choice(list(filter(
        lambda wc: any([baseClass in weaponTypeAttributeMap[weaponClassAttributeMap[wc].weaponType].permittedClasses
                        for baseClass in PlayerClassData.getBaseClasses(player.currentPlayerClass)]),
        [weaponClass for weaponClass in WeaponClasses])))
    newWeapon = generateWeapon(testRarity, 10, weaponClass)
    # print(newWeapon.getDescription())
    player.equipItem(newWeapon)

def rerollOtherEquips(player : Player, testRarity : int = 0):
    for drip in [generateHat(testRarity, 10), generateOverall(testRarity, 10), generateShoes(testRarity, 10)]:
        # print(drip.getDescription())
        player.equipItem(drip)

testRarity = 0

tp_mercenary = Player("vulcan", BasePlayerClassNames.WARRIOR)
tp_mercenary.level = 3
tp_mercenary.freeStatPoints = 12
tp_mercenary.assignStatPoints([BaseStats.ATK, BaseStats.DEF, BaseStats.HP, BaseStats.SPD,
                        BaseStats.ATK, BaseStats.DEF, BaseStats.HP, BaseStats.SPD,
                        BaseStats.ATK, BaseStats.DEF, BaseStats.HP, BaseStats.SPD,])
tp_mercenary.classRanks[BasePlayerClassNames.WARRIOR] = 3
tp_mercenary.changeClass(AdvancedPlayerClassNames.MERCENARY)
[tp_mercenary._rankUp() for i in range(9-1)]
rerollWeapon(tp_mercenary, testRarity)
rerollOtherEquips(tp_mercenary, testRarity)
print()

tp_assassin = Player("shubi", BasePlayerClassNames.ROGUE)
tp_assassin.level = 3
tp_assassin.freeStatPoints = 12
tp_assassin.assignStatPoints([BaseStats.ATK, BaseStats.AVO, BaseStats.SPD, BaseStats.MP,
                        BaseStats.ATK, BaseStats.AVO, BaseStats.SPD, BaseStats.MP,
                        BaseStats.ATK, BaseStats.AVO, BaseStats.SPD, BaseStats.HP])
tp_assassin.classRanks[BasePlayerClassNames.ROGUE] = 3
tp_assassin.changeClass(AdvancedPlayerClassNames.ASSASSIN)
[tp_assassin._rankUp() for i in range(9-1)]
rerollWeapon(tp_assassin, testRarity)
rerollOtherEquips(tp_assassin, testRarity)
print()

tp_sniper = Player("haihaya", BasePlayerClassNames.RANGER)
tp_sniper.level = 3
tp_sniper.freeStatPoints = 12
tp_sniper.assignStatPoints([BaseStats.ATK, BaseStats.ACC, BaseStats.SPD, BaseStats.HP,
                        BaseStats.ATK, BaseStats.ACC, BaseStats.SPD, BaseStats.HP,
                        BaseStats.ATK, BaseStats.ACC, BaseStats.SPD, BaseStats.HP])
tp_sniper.classRanks[BasePlayerClassNames.RANGER] = 3
tp_sniper.changeClass(AdvancedPlayerClassNames.SNIPER)
[tp_sniper._rankUp() for i in range(9-1)]
rerollWeapon(tp_sniper, testRarity)
rerollOtherEquips(tp_sniper, testRarity)
print()

tp_wizard = Player("sienna", BasePlayerClassNames.MAGE)
tp_wizard.level = 3
tp_wizard.freeStatPoints = 12
tp_wizard.assignStatPoints([BaseStats.MAG, BaseStats.MP, BaseStats.ACC, BaseStats.HP,
                        BaseStats.MAG, BaseStats.MP, BaseStats.ACC, BaseStats.HP,
                        BaseStats.MAG, BaseStats.MP, BaseStats.ACC, BaseStats.HP])
tp_wizard.classRanks[BasePlayerClassNames.MAGE] = 3
tp_wizard.changeClass(AdvancedPlayerClassNames.WIZARD)
[tp_wizard._rankUp() for i in range(9-1)]
rerollWeapon(tp_wizard, testRarity)
rerollOtherEquips(tp_wizard, testRarity)
print()

tp_knight = Player("kenelm", BasePlayerClassNames.WARRIOR)
tp_knight.level = 3
tp_knight.freeStatPoints = 12
tp_knight.assignStatPoints([BaseStats.ATK, BaseStats.DEF, BaseStats.HP, BaseStats.RES,
                        BaseStats.ATK, BaseStats.DEF, BaseStats.HP, BaseStats.RES,
                        BaseStats.ATK, BaseStats.DEF, BaseStats.HP, BaseStats.RES,])
tp_knight.classRanks[BasePlayerClassNames.WARRIOR] = 3
tp_knight.changeClass(AdvancedPlayerClassNames.KNIGHT)
[tp_knight._rankUp() for i in range(9-1)]
rerollWeapon(tp_knight, testRarity)
rerollOtherEquips(tp_knight, testRarity)
print()

tp_hunter = Player("azalea", BasePlayerClassNames.RANGER)
tp_hunter.level = 3
tp_hunter.freeStatPoints = 12
tp_hunter.assignStatPoints([BaseStats.ATK, BaseStats.ACC, BaseStats.SPD, BaseStats.HP,
                        BaseStats.ATK, BaseStats.ACC, BaseStats.SPD, BaseStats.HP,
                        BaseStats.ATK, BaseStats.ACC, BaseStats.SPD, BaseStats.MP])
tp_hunter.classRanks[BasePlayerClassNames.RANGER] = 3
tp_hunter.changeClass(AdvancedPlayerClassNames.HUNTER)
[tp_hunter._rankUp() for i in range(9-1)]
rerollWeapon(tp_hunter, testRarity)
rerollOtherEquips(tp_hunter, testRarity)
print()

tp_acrobat = Player("mimosa", BasePlayerClassNames.ROGUE)
tp_acrobat.level = 3
tp_acrobat.freeStatPoints = 12
tp_acrobat.assignStatPoints([BaseStats.ATK, BaseStats.AVO, BaseStats.SPD, BaseStats.MP,
                        BaseStats.ATK, BaseStats.AVO, BaseStats.SPD, BaseStats.MP,
                        BaseStats.ATK, BaseStats.AVO, BaseStats.SPD, BaseStats.HP])
tp_acrobat.classRanks[BasePlayerClassNames.ROGUE] = 3
tp_acrobat.changeClass(AdvancedPlayerClassNames.ACROBAT)
[tp_acrobat._rankUp() for i in range(9-1)]
rerollWeapon(tp_acrobat, testRarity)
rerollOtherEquips(tp_acrobat, testRarity)
print()

tp_saint = Player("avalie", BasePlayerClassNames.MAGE)
tp_saint.level = 3
tp_saint.freeStatPoints = 12
tp_saint.assignStatPoints([BaseStats.MAG, BaseStats.MP, BaseStats.RES, BaseStats.HP,
                        BaseStats.MAG, BaseStats.MP, BaseStats.RES, BaseStats.HP,
                        BaseStats.MAG, BaseStats.MP, BaseStats.RES, BaseStats.HP])
tp_saint.classRanks[BasePlayerClassNames.MAGE] = 3
tp_saint.changeClass(AdvancedPlayerClassNames.SAINT)
[tp_saint._rankUp() for i in range(9-1)]
rerollWeapon(tp_saint, testRarity)
rerollOtherEquips(tp_saint, testRarity)
print()


### Beginner examples

def beginnerPlayer(name, baseClass):
    bgp = Player(name, baseClass)
    bgp.equipItem(makeBeginnerWeapon(baseClass))
    return bgp

bgp_warrior = beginnerPlayer("warrior", BasePlayerClassNames.WARRIOR)
bgp_ranger = beginnerPlayer("bowman", BasePlayerClassNames.RANGER)
bgp_rogue = beginnerPlayer("thief", BasePlayerClassNames.ROGUE)
bgp_mage = beginnerPlayer("magician", BasePlayerClassNames.MAGE)