from __future__ import annotations
from functools import reduce
from typing import Callable, TYPE_CHECKING

from rpg_combat_entity import EnemyReward
from rpg_consts import *
from rpg_dungeons import DungeonData, DungeonRoomData
from rpg_enemy_data import *

trainingDungeon = DungeonData("Training Courtyard", True, 1.0, 1.0,
                              [
                                  DungeonRoomData([([basicDummy], 1)]),
                                  DungeonRoomData([([skillfulDummy], 1)]),
                                  DungeonRoomData([([trainingBoss], 1)])
                              ],
                              lambda _1, _2: EnemyReward(2, 3, 0, None))