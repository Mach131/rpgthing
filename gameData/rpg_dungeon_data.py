from __future__ import annotations
from functools import reduce
from typing import Callable, TYPE_CHECKING

from structures.rpg_combat_entity import EnemyReward
from rpg_consts import *
from structures.rpg_dungeons import DungeonData, DungeonRoomData
from gameData.rpg_enemy_data import *

trainingDungeon = DungeonData("Training Courtyard", "Training",
                              "\"Can't have you divin' in without a quick warm-up!\"",
                              "2 EXP, 3 WUP",
                              set(),
                              1, 1, True, 1.0, 1.0,
                              [
                                  DungeonRoomData([([basicDummy], 1)]),
                                  DungeonRoomData([([skillfulDummy], 1)]),
                                  DungeonRoomData([([trainingBoss], 1)])
                              ],
                              lambda _1, _2: EnemyReward(2, 3, 0, None))