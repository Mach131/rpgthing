from __future__ import annotations
from functools import reduce
from typing import Callable, TYPE_CHECKING

from structures.rpg_combat_entity import EnemyReward
from rpg_consts import *
from structures.rpg_dungeons import DungeonData, DungeonRoomData
from gameData.rpg_enemy_data import *

def enemyCombosIter(enemyList : list, numEnemies : int, prev : tuple = ()):
    for enemy in enemyList:
        result = list(prev) + [enemy]
        while len(result) < numEnemies:
            yield from enemyCombosIter(enemyList[1:], numEnemies, tuple(result))
            result = result + [enemy]
        yield result

trainingDungeon = DungeonData("Training Yard", "Training",
                              "A small yard outside an unassuming building, with some training dummies set up.\n" +
                              "You were pointed here when getting your dungeon license, but is there anyone else around...?",
                              "Enough EXP to learn a Base Class",
                              set(),
                              1, 1, True, 1.0, 1.0,
                              [
                                  DungeonRoomData([([basicDummy], 1)], {}),
                                  DungeonRoomData([([skillfulDummy], 1)], {}),
                                  DungeonRoomData([([trainingBoss], 1)], {})
                              ],
                              lambda _1, player: EnemyReward(2, 1, 0, None, set([Milestones.TUTORIAL_COMPLETE])))

fieldDungeon = DungeonData("Fresh Fields", "Field",
                           "An easily-accessed open field, suitable for any new party.\n" +
                           "Despite the name, it's not uncommon for allergies to act up as you get further in.",
                           "30~40 EXP, 4~6 WUP, Common Equipment",
                           set([Milestones.TUTORIAL_COMPLETE]),
                           3, 2, False, 0.5, 0.65,
                           [
                               DungeonRoomData([
                                   ([ffSlime, ffSlime], 1),
                                   ([ffSlime, ffRat], 1),
                                   ([ffRat, ffRat], 1)], {'roomNumber': 0}),
                               DungeonRoomData([
                                   ([ffSlime, ffSlime, ffSlime], 1),
                                   ([ffSlime, ffSlime, ffRat], 1),
                                   ([ffSlime, ffRat, ffRat], 1),
                                   ([ffRat, ffRat, ffRat], 1),
                                   ([ffPlant, ffRat], 1),
                                   ([ffPlant, ffSlime], 1)], {'roomNumber': 1}),
                               DungeonRoomData([
                                   ([ffSlime, ffSlime, ffSlime], 2),
                                   ([ffSlime, ffSlime, ffRat], 2),
                                   ([ffSlime, ffRat, ffRat], 2),
                                   ([ffRat, ffRat, ffRat], 2),
                                   ([ffPlant, ffRat, ffRat], 3),
                                   ([ffPlant, ffSlime, ffRat], 3),
                                   ([ffPlant, ffSlime, ffSlime], 3)], {'roomNumber': 2}),
                               DungeonRoomData([
                                   ([ffSlimeBoss], 1),
                                   ([ffPlantBoss, ffPlant, ffPlant], 1)], {'roomNumber': 3})
                           ],
                           lambda _1, player: EnemyReward(10, 3,
                                                          1 if random.random() < 0.3 else 0,
                                                          None, set([Milestones.FRESH_FIELDS_COMPLETE])))

caveDungeon = DungeonData("Skylight Cave", "Cave",
                           "A cave with a ceiling lightly dotted by holes, letting in scatterings of daylight.\n" +
                           "It still has a claustrophobic feeling at times, as some corners remain largely shrouded in darkness..",
                           "45~50 EXP, 5~10 WUP, Melee-focused Weapons",
                           set([Milestones.TUTORIAL_COMPLETE]),
                           3, 3, False, 0.5, 0.65,
                           [
                               DungeonRoomData([
                                   (combo, 1) for combo in enemyCombosIter([scRock, scBat, scFairy, scRat], 2)
                                        if combo.count(scRat) < 2
                                   ], {'roomNumber': 0}),
                               DungeonRoomData([
                                   (combo + [scRat], 1) for combo in enemyCombosIter([scRock, scBat, scFairy, scRat], 2)
                                        if combo.count(scRat) < 2], {'roomNumber': 1}),
                               DungeonRoomData([
                                   (combo, 1) for combo in enemyCombosIter([scRock, scBat, scFairy, scRat], 3)
                                        if combo.count(scRat) < 3], {'roomNumber': 2}),
                               DungeonRoomData([
                                   ([scRpsBoss], 1),
                                   ([scSpiritBoss, scRock, scBat, scFairy], 1)], {'roomNumber': 3, 'boss': True})
                           ],
                           lambda _1, player: EnemyReward(10, 3,
                                                          1 if random.random() < 0.4 else 0,
                                                          None, set([Milestones.SKYLIGHT_CAVE_COMPLETE])))