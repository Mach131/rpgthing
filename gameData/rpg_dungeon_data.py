from __future__ import annotations
from functools import reduce
from typing import Callable, TYPE_CHECKING, Generator

from structures.rpg_combat_entity import EnemyReward
from rpg_consts import *
from structures.rpg_dungeons import DungeonData, DungeonRoomData
from gameData.rpg_enemy_data import *

def enemyCombosIter(enemyList : list, numEnemies : int, prev : tuple = ()) -> Generator:
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
                              lambda _1, player: EnemyReward(2, 1, 0, None, set([Milestones.TUTORIAL_COMPLETE])),
                        Milestones.TUTORIAL_COMPLETE)

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
                                   ([ffPlantBoss, ffPlant, ffPlant], 1)], {'roomNumber': 3, 'boss': True})
                           ],
                           lambda _1, player: EnemyReward(10, 3,
                                                          1 if random.random() < 0.3 else 0,
                                                          None, set([Milestones.FRESH_FIELDS_COMPLETE])),
                        Milestones.FRESH_FIELDS_COMPLETE)

caveDungeon = DungeonData("Skylight Cave", "Cave",
                           "A cave with a ceiling lightly dotted by holes, letting in scatterings of daylight.\n" +
                           "It still has a claustrophobic feeling at times, as some corners remain largely shrouded in darkness.",
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
                                                          None, set([Milestones.SKYLIGHT_CAVE_COMPLETE])),
                        Milestones.SKYLIGHT_CAVE_COMPLETE)

forestDungeon = DungeonData("Saffron Forest", "Forest",
                           "The entrance to a magical forest, lush with colorful and fragrant plantlife.\n" +
                           "Though not as dangerous as the deeper parts, one must still be careful not to anger the elementals or the inhabitants they trust.",
                           "45~50 EXP, 5~10 WUP, Long Range-focused Weapons",
                           set([Milestones.TUTORIAL_COMPLETE]),
                           3, 3, False, 0.5, 0.65,
                           [
                               DungeonRoomData([
                                   (combo, 1) for combo in enemyCombosIter([sfReaper, sfNinja, sfElemental, sfRat], 2)
                                        if combo.count(sfRat) < 2
                                   ], {'roomNumber': 0}),
                               DungeonRoomData([
                                   (combo + [sfRat], 1) for combo in enemyCombosIter([sfReaper, sfNinja, sfElemental, sfRat], 2)
                                        if combo.count(sfRat) < 2], {'roomNumber': 1}),
                               DungeonRoomData([
                                   (combo, 1) for combo in enemyCombosIter([sfReaper, sfNinja, sfElemental, sfRat], 3)
                                        if combo.count(sfRat) < 3 and combo.count(sfReaper) < 2], {'roomNumber': 2}),
                               DungeonRoomData([
                                   ([sfNinjaBoss, sfNinja, sfNinja], 1),
                                   ([sfRuneBoss], 1)], {'roomNumber': 3, 'boss': True})
                           ],
                           lambda _1, player: EnemyReward(10, 3,
                                                          1 if random.random() < 0.4 else 0,
                                                          None, set([Milestones.SAFFRON_FOREST_COMPLTE])),
                        Milestones.SAFFRON_FOREST_COMPLTE)

# add storehouse tag
sdSecondStageCombos = []
for combo in enemyCombosIter([ffRat, scRat, sfRat], 2):
    sdSecondStageCombos.append(([asMageRat] + combo, 1))
    sdSecondStageCombos.append(([asStrongRat] + combo, 1))
sdFourthStageCombos = []
[[sdFourthStageCombos.append(([asSpawner, exRat, otherRat],
                            1 if otherRat in [asMageRat, asStrongRat] else 2))
 for exRat in [asMageRat, asStrongRat]]
 for otherRat in [ffRat, scRat, sfRat, asMageRat, asStrongRat]]
storehouseDungeon = DungeonData("Abandoned Storehouse", "Storehouse",
                           "An old building with an elaborate underground layout; though currently unused, it's served various purposes over time.\n" +
                           "There have been rumors of a rat infestation getting in the way of any more work being done on it. Come to think of it, rats seem to be everywhere lately...",
                           "75~85 EXP, 10~15 WUP, 1~2 SWUP, Uncommon Equipment",
                           set([Milestones.FRESH_FIELDS_COMPLETE, Milestones.SKYLIGHT_CAVE_COMPLETE, Milestones.SAFFRON_FOREST_COMPLTE]),
                           4, 4, False, 0.8, 0.8,
                           [
                               DungeonRoomData([
                                   (combo, 1) for combo in enemyCombosIter([ffRat, scRat, sfRat], 3)
                                   ], {'roomNumber': 0, 'storehouse': True}),
                               DungeonRoomData(sdSecondStageCombos, {'roomNumber': 1, 'storehouse': True}),
                               DungeonRoomData([
                                   ([asSpawner] + combo,
                                    2 if asMageRat in combo or asStrongRat in combo else 3)
                                    for combo in enemyCombosIter([ffRat, scRat, sfRat, asMageRat, asStrongRat], 2)
                                        if combo.count(asMageRat) + combo.count(asStrongRat) < 2], {'roomNumber': 2, 'storehouse': True}),
                               DungeonRoomData(sdFourthStageCombos, {'roomNumber': 3, 'storehouse': True}),
                               DungeonRoomData([
                                   ([asSalali], 1)], {'roomNumber': 4, 'storehouse': True, 'boss': True})
                           ],
                           lambda _1, player: EnemyReward(10, 3,
                                                          1 if random.random() < 0.5 else 0,
                                                          None, set([Milestones.ABANDONED_STOREHOUSE_COMPLETE])),
                        Milestones.ABANDONED_STOREHOUSE_COMPLETE)