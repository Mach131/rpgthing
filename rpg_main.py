import asyncio
import traceback
import random

from rpg_combat_interface import CombatInterface, LocalPlayerInputHandler, RandomEntityInputHandler
from rpg_consts import *
from rpg_combat_entity import CombatEntity, Player
from rpg_classes_skills import ActiveSkillDataSelector, AttackSkillData, PlayerClassData, SkillData
from rpg_combat_state import CombatController, ActionResultInfo, AttackResultInfo
from rpg_items import *
from rpg_messages import LocalMessageCollector, MessageCollector # TODO

async def simpleCombatSimulation(team1 : list[Player], team2 : list[Player], bothRandom : bool) -> None:
    logger = LocalMessageCollector()
    playerInputClass = RandomEntityInputHandler if bothRandom else LocalPlayerInputHandler
    ci = CombatInterface({player: playerInputClass(player) for player in team1},
                         {opponent: RandomEntityInputHandler(opponent) for opponent in team2}, [logger])

    await ci.runCombat()

def rerollWeapon(player : Player, testRarity : int = 0):
    weaponClass = random.choice(list(filter(
        lambda wc: any([baseClass in weaponTypeAttributeMap[weaponClassAttributeMap[wc].weaponType].permittedClasses
                        for baseClass in PlayerClassData.getBaseClasses(player.currentPlayerClass)]),
        [weaponClass for weaponClass in WeaponClasses])))
    newWeapon = generateWeapon(testRarity, 10, weaponClass)
    print(newWeapon.getDescription())
    player.equipItem(newWeapon)

def rerollOtherEquips(player : Player, testRarity : int = 0):
    for drip in [generateHat(testRarity, 10), generateOverall(testRarity, 10), generateShoes(testRarity, 10)]:
        print(drip.getDescription())
        player.equipItem(drip)

if __name__ == '__main__':
    testRarity = 0

    p1 = Player("vulcan", BasePlayerClassNames.WARRIOR)
    p1.level = 3
    p1.freeStatPoints = 12
    p1.assignStatPoints([BaseStats.ATK, BaseStats.DEF, BaseStats.HP, BaseStats.SPD,
                         BaseStats.ATK, BaseStats.DEF, BaseStats.HP, BaseStats.SPD,
                         BaseStats.ATK, BaseStats.DEF, BaseStats.HP, BaseStats.SPD,])
    p1.classRanks[BasePlayerClassNames.WARRIOR] = 3
    p1.changeClass(AdvancedPlayerClassNames.MERCENARY)
    [p1.rankUp() for i in range(9-1)]
    rerollWeapon(p1, testRarity)
    rerollOtherEquips(p1, testRarity)
    print()

    p2 = Player("shubi", BasePlayerClassNames.ROGUE)
    p2.level = 3
    p2.freeStatPoints = 12
    p2.assignStatPoints([BaseStats.ATK, BaseStats.AVO, BaseStats.SPD, BaseStats.MP,
                         BaseStats.ATK, BaseStats.AVO, BaseStats.SPD, BaseStats.MP,
                         BaseStats.ATK, BaseStats.AVO, BaseStats.SPD, BaseStats.HP])
    p2.classRanks[BasePlayerClassNames.ROGUE] = 3
    p2.changeClass(AdvancedPlayerClassNames.ASSASSIN)
    [p2.rankUp() for i in range(9-1)]
    rerollWeapon(p2, testRarity)
    rerollOtherEquips(p2, testRarity)
    print()

    p3 = Player("haihaya", BasePlayerClassNames.RANGER)
    p3.level = 3
    p3.freeStatPoints = 12
    p3.assignStatPoints([BaseStats.ATK, BaseStats.ACC, BaseStats.SPD, BaseStats.HP,
                         BaseStats.ATK, BaseStats.ACC, BaseStats.SPD, BaseStats.HP,
                         BaseStats.ATK, BaseStats.ACC, BaseStats.SPD, BaseStats.HP])
    p3.classRanks[BasePlayerClassNames.RANGER] = 3
    p3.changeClass(AdvancedPlayerClassNames.SNIPER)
    [p3.rankUp() for i in range(9-1)]
    rerollWeapon(p3, testRarity)
    rerollOtherEquips(p3, testRarity)
    print()

    p4 = Player("sienna", BasePlayerClassNames.MAGE)
    p4.level = 3
    p4.freeStatPoints = 12
    p4.assignStatPoints([BaseStats.MAG, BaseStats.MP, BaseStats.ACC, BaseStats.HP,
                         BaseStats.MAG, BaseStats.MP, BaseStats.ACC, BaseStats.HP,
                         BaseStats.MAG, BaseStats.MP, BaseStats.ACC, BaseStats.HP])
    p4.classRanks[BasePlayerClassNames.MAGE] = 3
    p4.changeClass(AdvancedPlayerClassNames.WIZARD)
    [p4.rankUp() for i in range(9-1)]
    rerollWeapon(p4, testRarity)
    rerollOtherEquips(p4, testRarity)
    print()

    p5 = Player("kenelm", BasePlayerClassNames.WARRIOR)
    p5.level = 3
    p5.freeStatPoints = 12
    p5.assignStatPoints([BaseStats.ATK, BaseStats.DEF, BaseStats.HP, BaseStats.RES,
                         BaseStats.ATK, BaseStats.DEF, BaseStats.HP, BaseStats.RES,
                         BaseStats.ATK, BaseStats.DEF, BaseStats.HP, BaseStats.RES,])
    p5.classRanks[BasePlayerClassNames.WARRIOR] = 3
    p5.changeClass(AdvancedPlayerClassNames.KNIGHT)
    [p5.rankUp() for i in range(9-1)]
    rerollWeapon(p5, testRarity)
    rerollOtherEquips(p5, testRarity)
    print()

    p6 = Player("azalea", BasePlayerClassNames.RANGER)
    p6.level = 3
    p6.freeStatPoints = 12
    p6.assignStatPoints([BaseStats.ATK, BaseStats.ACC, BaseStats.SPD, BaseStats.HP,
                         BaseStats.ATK, BaseStats.ACC, BaseStats.SPD, BaseStats.HP,
                         BaseStats.ATK, BaseStats.ACC, BaseStats.SPD, BaseStats.MP])
    p6.classRanks[BasePlayerClassNames.RANGER] = 3
    p6.changeClass(AdvancedPlayerClassNames.HUNTER)
    [p6.rankUp() for i in range(9-1)]
    rerollWeapon(p6, testRarity)
    rerollOtherEquips(p6, testRarity)
    print()

    p7 = Player("mimosa", BasePlayerClassNames.ROGUE)
    p7.level = 3
    p7.freeStatPoints = 12
    p7.assignStatPoints([BaseStats.ATK, BaseStats.AVO, BaseStats.SPD, BaseStats.MP,
                         BaseStats.ATK, BaseStats.AVO, BaseStats.SPD, BaseStats.MP,
                         BaseStats.ATK, BaseStats.AVO, BaseStats.SPD, BaseStats.HP])
    p7.classRanks[BasePlayerClassNames.ROGUE] = 3
    p7.changeClass(AdvancedPlayerClassNames.ACROBAT)
    [p7.rankUp() for i in range(9-1)]
    rerollWeapon(p7, testRarity)
    rerollOtherEquips(p7, testRarity)
    print()

    p8 = Player("avalie", BasePlayerClassNames.MAGE)
    p8.level = 3
    p8.freeStatPoints = 12
    p8.assignStatPoints([BaseStats.MAG, BaseStats.MP, BaseStats.RES, BaseStats.HP,
                         BaseStats.MAG, BaseStats.MP, BaseStats.RES, BaseStats.HP,
                         BaseStats.MAG, BaseStats.MP, BaseStats.RES, BaseStats.HP])
    p8.classRanks[BasePlayerClassNames.MAGE] = 3
    p8.changeClass(AdvancedPlayerClassNames.SAINT)
    [p8.rankUp() for i in range(9-1)]
    rerollWeapon(p8, testRarity)
    rerollOtherEquips(p8, testRarity)
    print()

    asyncio.run(simpleCombatSimulation([p1, p5, p4, p8], [p2, p3, p6, p7], True))
    # simpleCombatSimulation([p1, p2], [p3, p4], 2)

    while True:
        inp = input("> ")
        if inp == "exit":
            break
        try:
            if len(inp) > 0:
                print(eval(inp))
        except Exception:
            print(traceback.format_exc())