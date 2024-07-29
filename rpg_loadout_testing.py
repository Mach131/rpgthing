from gameData.rpg_item_data import *
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

tp_wizard = Player("irae", BasePlayerClassNames.MAGE)
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

tp_striker = Player("fleet", BasePlayerClassNames.WARRIOR)
tp_striker.level = 3
tp_striker.freeStatPoints = 12
tp_striker.assignStatPoints([BaseStats.ATK, BaseStats.AVO, BaseStats.ACC, BaseStats.MP,
                        BaseStats.ATK, BaseStats.AVO, BaseStats.SPD, BaseStats.MP,
                        BaseStats.ATK, BaseStats.HP, BaseStats.SPD, BaseStats.HP])
tp_striker.classRanks[BasePlayerClassNames.WARRIOR] = 3
tp_striker.milestones.add(Milestones.CLASS_STRIKER_UNLOCKED)
tp_striker.changeClass(SecretPlayerClassNames.STRIKER)
[tp_striker._rankUp() for i in range(9-1)]
tp_striker.unequipItem(EquipmentSlot.WEAPON)
rerollOtherEquips(tp_striker, testRarity)

tp_alchefist = Player("eos", BasePlayerClassNames.RANGER)
tp_alchefist.level = 3
tp_alchefist.freeStatPoints = 12
tp_alchefist.assignStatPoints([BaseStats.ATK, BaseStats.MAG, BaseStats.ACC, BaseStats.MP,
                        BaseStats.ATK, BaseStats.MAG, BaseStats.ACC, BaseStats.MP,
                        BaseStats.ATK, BaseStats.MP, BaseStats.SPD, BaseStats.HP])
tp_alchefist.classRanks[BasePlayerClassNames.RANGER] = 3
tp_alchefist.milestones.add(Milestones.CLASS_ALCHEFIST_UNLOCKED)
tp_alchefist.changeClass(SecretPlayerClassNames.ALCHEFIST)
[tp_alchefist._rankUp() for i in range(9-1)]
rerollWeapon(tp_alchefist, testRarity)
rerollOtherEquips(tp_alchefist, testRarity)

tp_saboteur = Player("sienna", BasePlayerClassNames.ROGUE)
tp_saboteur.level = 3
tp_saboteur.freeStatPoints = 12
tp_saboteur.assignStatPoints([BaseStats.ATK, BaseStats.SPD, BaseStats.ACC, BaseStats.MP,
                        BaseStats.ATK, BaseStats.SPD, BaseStats.AVO, BaseStats.MP,
                        BaseStats.ATK, BaseStats.MP, BaseStats.SPD, BaseStats.AVO])
tp_saboteur.classRanks[BasePlayerClassNames.ROGUE] = 3
tp_saboteur.milestones.add(Milestones.CLASS_SABOTEUR_UNLOCKED)
tp_saboteur.changeClass(SecretPlayerClassNames.SABOTEUR)
[tp_saboteur._rankUp() for i in range(9-1)]
rerollWeapon(tp_saboteur, testRarity)
rerollOtherEquips(tp_saboteur, testRarity)

tp_summoner = Player("will", BasePlayerClassNames.MAGE)
tp_summoner.level = 3
tp_summoner.freeStatPoints = 12
tp_summoner.assignStatPoints([BaseStats.ATK, BaseStats.SPD, BaseStats.MAG, BaseStats.MP,
                        BaseStats.ATK, BaseStats.MAG, BaseStats.HP, BaseStats.MP,
                        BaseStats.ATK, BaseStats.MAG, BaseStats.SPD, BaseStats.ACC])
tp_summoner.classRanks[BasePlayerClassNames.MAGE] = 3
tp_summoner.milestones.add(Milestones.CLASS_SUMMONER_UNLOCKED)
tp_summoner.changeClass(SecretPlayerClassNames.SUMMONER)
[tp_summoner._rankUp() for i in range(9-1)]
rerollWeapon(tp_summoner, testRarity)
rerollOtherEquips(tp_summoner, testRarity)



### Beginner examples

def beginnerPlayer(name, baseClass):
    bgp = Player(name, baseClass)
    bgp.equipItem(makeBeginnerWeapon(baseClass))
    return bgp

bgp_warrior = beginnerPlayer("warrior", BasePlayerClassNames.WARRIOR)
bgp_ranger = beginnerPlayer("bowman", BasePlayerClassNames.RANGER)
bgp_rogue = beginnerPlayer("thief", BasePlayerClassNames.ROGUE)
bgp_mage = beginnerPlayer("magician", BasePlayerClassNames.MAGE)

def postTutorialPlayer(name, baseClass, advanceClass, statList):
    ptp = beginnerPlayer(name, baseClass)
    ptp.gainExp(EXP_TO_NEXT_PLAYER_LEVEL[0])
    ptp.assignStatPoints(statList)
    ptp.changeClass(advanceClass)
    return ptp

def basicLootPlayer(name, baseClass, advanceClass, statList):
    blp = beginnerPlayer(name, baseClass)
    blp.gainExp(EXP_TO_NEXT_PLAYER_LEVEL[0])
    blp.changeClass(advanceClass)

    blp.gainExp(50)
    blp.assignStatPoints(statList)
    blp.wup = 100
    for i in range(7): blp.increaseItemRank(blp.equipment[EquipmentSlot.WEAPON])
    
    blp.equipItem(generateHat(0, random.randint(1, 8), None, 0))
    blp.equipItem(generateOverall(0, random.randint(1, 8), None, 0))
    blp.equipItem(generateShoes(0, random.randint(1, 8), None, 0))
    print(advanceClass)
    # print(blp.getTotalStatString())
    return blp

def ratReadyPlayer(name, baseClass, advanceClass, statList):
    rrp = beginnerPlayer(name, baseClass)
    rrp.gainExp(EXP_TO_NEXT_PLAYER_LEVEL[0])
    rrp.changeClass(advanceClass)

    for i in range(1, 4):
        rrp.gainExp(EXP_TO_NEXT_PLAYER_LEVEL[i])
    rrp.assignStatPoints(statList)
    rrp.wup = 1000
    rrp.swup = 10
    for i in range(10): rrp.increaseItemRank(rrp.equipment[EquipmentSlot.WEAPON])
    rrp.increaseItemRarity(rrp.equipment[EquipmentSlot.WEAPON])
    
    rrp.equipItem(generateHat(0, 9, None, 0))
    rrp.equipItem(generateOverall(0, 9, None, 0))
    rrp.equipItem(generateShoes(0, 9, None, 0))
    # print(advanceClass)
    # print(rrp.getTotalStatString())
    return rrp

test_mercenary = ratReadyPlayer("mercenary", BasePlayerClassNames.WARRIOR, AdvancedPlayerClassNames.MERCENARY,
                              [BaseStats.ATK, BaseStats.SPD, BaseStats.ACC,
                               BaseStats.ATK, BaseStats.ACC, BaseStats.SPD,
                               BaseStats.ATK, BaseStats.SPD, BaseStats.HP,
                               BaseStats.ATK, BaseStats.SPD, BaseStats.MP,
                               BaseStats.ATK, BaseStats.SPD, BaseStats.ACC])
test_knight = ratReadyPlayer("knight", BasePlayerClassNames.WARRIOR, AdvancedPlayerClassNames.KNIGHT,
                              [BaseStats.ATK, BaseStats.DEF, BaseStats.HP,
                               BaseStats.ATK, BaseStats.HP, BaseStats.DEF,
                               BaseStats.ACC, BaseStats.DEF, BaseStats.HP,
                               BaseStats.ATK, BaseStats.DEF, BaseStats.HP,
                               BaseStats.MP, BaseStats.DEF, BaseStats.HP])
test_sniper = ratReadyPlayer("sniper", BasePlayerClassNames.RANGER, AdvancedPlayerClassNames.SNIPER,
                              [BaseStats.ATK, BaseStats.SPD, BaseStats.HP,
                               BaseStats.ATK, BaseStats.ACC, BaseStats.SPD,
                               BaseStats.ATK, BaseStats.SPD, BaseStats.MP,
                               BaseStats.ATK, BaseStats.SPD, BaseStats.HP,
                               BaseStats.ATK, BaseStats.SPD, BaseStats.HP])
test_hunter = ratReadyPlayer("hunter", BasePlayerClassNames.RANGER, AdvancedPlayerClassNames.HUNTER,
                              [BaseStats.ATK, BaseStats.SPD, BaseStats.ACC,
                               BaseStats.ATK, BaseStats.MP, BaseStats.SPD,
                               BaseStats.ATK, BaseStats.SPD, BaseStats.MP,
                               BaseStats.ATK, BaseStats.SPD, BaseStats.HP,
                               BaseStats.ATK, BaseStats.SPD, BaseStats.MP])
test_assassin = ratReadyPlayer("assassin", BasePlayerClassNames.ROGUE, AdvancedPlayerClassNames.ASSASSIN,
                              [BaseStats.ATK, BaseStats.SPD, BaseStats.ACC,
                               BaseStats.ATK, BaseStats.ACC, BaseStats.SPD,
                               BaseStats.ATK, BaseStats.SPD, BaseStats.HP,
                               BaseStats.ATK, BaseStats.SPD, BaseStats.MP,
                               BaseStats.ATK, BaseStats.SPD, BaseStats.ACC])
test_acrobat = ratReadyPlayer("acrobat", BasePlayerClassNames.ROGUE, AdvancedPlayerClassNames.ACROBAT,
                              [BaseStats.ATK, BaseStats.SPD, BaseStats.AVO,
                               BaseStats.ATK, BaseStats.ACC, BaseStats.AVO,
                               BaseStats.ATK, BaseStats.SPD, BaseStats.AVO,
                               BaseStats.ATK, BaseStats.SPD, BaseStats.AVO,
                               BaseStats.ATK, BaseStats.AVO, BaseStats.ACC])
test_wizard = ratReadyPlayer("wizard", BasePlayerClassNames.MAGE, AdvancedPlayerClassNames.WIZARD,
                              [BaseStats.MAG, BaseStats.SPD, BaseStats.MP,
                               BaseStats.MAG, BaseStats.ACC, BaseStats.MP,
                               BaseStats.MAG, BaseStats.SPD, BaseStats.MP,
                               BaseStats.MAG, BaseStats.SPD, BaseStats.MP,
                               BaseStats.MAG, BaseStats.ACC, BaseStats.MP])
test_saint = ratReadyPlayer("saint", BasePlayerClassNames.MAGE, AdvancedPlayerClassNames.SAINT,
                              [BaseStats.MAG, BaseStats.RES, BaseStats.MP,
                               BaseStats.MAG, BaseStats.RES, BaseStats.MP,
                               BaseStats.MAG, BaseStats.RES, BaseStats.MP,
                               BaseStats.MAG, BaseStats.HP, BaseStats.MP,
                               BaseStats.MAG, BaseStats.HP, BaseStats.MP])