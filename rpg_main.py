import asyncio
import traceback
import random

from structures.rpg_combat_interface import *
from rpg_consts import *
from structures.rpg_combat_entity import CombatEntity, Player
from structures.rpg_classes_skills import ActiveSkillDataSelector, AttackSkillData, PlayerClassData, SkillData
from structures.rpg_combat_state import CombatController, ActionResultInfo, AttackResultInfo
from structures.rpg_dungeons import *
from gameData.rpg_dungeon_data import *
from structures.rpg_items import *
from structures.rpg_messages import LocalMessageCollector, MessageCollector
from rpg_loadout_testing import *
from gameData.rpg_enemy_data import *

async def simpleCombatSimulation(team1 : list[Player], team2 : list[Player], bothRandom : bool, sleepTime : int) -> None:
    mainLogger = LocalMessageCollector()
    loggers : dict[CombatEntity, MessageCollector] = {player : MessageCollector() for player in team1}
    loggers[team1[0]] = mainLogger
    ci = CombatInterface({player: RandomEntityInputHandler(player, sleepTime) if bothRandom else LocalPlayerInputHandler(player) for player in team1},
                         {opponent: RandomEntityInputHandler(opponent, sleepTime) for opponent in team2}, loggers, {}, {},
                         {player : 2 for player in team1})

    await ci.runCombat()

async def betterCombatSimulation(players : list[Player], enemies : list[Enemy]) -> None:
    mainLogger = LocalMessageCollector()
    loggers : dict[CombatEntity, MessageCollector] = {player : MessageCollector() for player in players}
    loggers[players[0]] = mainLogger
    ci = CombatInterface({player: LocalPlayerInputHandler(player) for player in players},
                         {opponent: EnemyInputHandler(opponent) for opponent in enemies}, loggers, {}, {},
                         {player : 2 for player in players})

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
    # asyncio.run(betterCombatSimulation([bgp_warrior], [trainingBoss()]))
    player = test_acrobat
    dungeonController = DungeonController(fieldDungeon,
                                          {player: DungeonInputHandler(player, LocalPlayerInputHandler)},
                                          {player: DEFAULT_STARTING_DISTANCE},
                                          {player: LocalMessageCollector()})
    # asyncio.run(dungeonController.runDungeon(False))

    while True:
        inp = input("> ")
        if inp == "exit":
            break
        try:
            if len(inp) > 0:
                print(eval(inp))
        except Exception:
            print(traceback.format_exc())