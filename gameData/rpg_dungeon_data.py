from __future__ import annotations
from functools import reduce
from typing import Callable, TYPE_CHECKING

from structures.rpg_combat_entity import EnemyReward
from rpg_consts import *
from structures.rpg_dungeons import DungeonData, DungeonRoomData
from gameData.rpg_enemy_data import *

trainingDungeon = DungeonData("Training Yard", "Training",
                              "A small yard outside an unassuming building, with some training dummies set up.\n" +
                              "You were pointed here when getting your dungeon license, but is there anyone else around...?",
                              "Clear Bonus: 2 EXP, 3 WUP",
                              set(),
                              1, 1, True, 1.0, 1.0,
                              [
                                  DungeonRoomData([([basicDummy], 1)], {}),
                                  DungeonRoomData([([skillfulDummy], 1)], {}),
                                  DungeonRoomData([([trainingBoss], 1)], {})
                              ],
                              lambda _1, player: (
                                  player.milestones.add(Milestones.TUTORIAL_COMPLETE),
                                  EnemyReward(2, 3, 0, None))[-1])

# TODO: for field, use 'roomNumber' param
fieldDungeon = DungeonData("Fresh Fields", "Field",
                           "",
                           "",
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
                           lambda _1, player: (
                               EnemyReward(5, 2,
                                           1 if random.random() < 0.15 else 0,
                                           None),)[-1])