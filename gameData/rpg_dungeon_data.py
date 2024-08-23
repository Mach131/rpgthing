from __future__ import annotations
from functools import reduce
from typing import Callable, TYPE_CHECKING, Generator

from structures.rpg_combat_entity import EnemyReward
from rpg_consts import *
from structures.rpg_dungeons import DungeonData, DungeonRoomData, IntRoomSetting, PlayerTeamRoomSetting, SettingsDungeonRoomData
from gameData.rpg_enemy_data import *
from gameData.rpg_enemy_data2 import *

def enemyCombosIter(enemyList : list, numEnemies : int, prev : tuple = ()) -> Generator:
    for enemy in enemyList:
        result = list(prev) + [enemy]
        while len(result) < numEnemies:
            yield from enemyCombosIter(enemyList[1:], numEnemies, tuple(result))
            result = result + [enemy]
        yield result

trainingDungeon = DungeonData("Training Yard", "Yard", DungeonCategory.NORMAL,
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

fieldDungeon = DungeonData("Fresh Fields", "Field", DungeonCategory.NORMAL,
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

caveDungeon = DungeonData("Skylight Cave", "Cave", DungeonCategory.NORMAL,
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

forestDungeon = DungeonData("Saffron Forest", "Forest", DungeonCategory.NORMAL,
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

sdSecondStageCombos = []
for combo in enemyCombosIter([ffRat, scRat, sfRat], 2):
    sdSecondStageCombos.append(([asMageRat] + combo, 1))
    sdSecondStageCombos.append(([asStrongRat] + combo, 1))
sdFourthStageCombos = []
[[sdFourthStageCombos.append(([asSpawner, exRat, otherRat],
                            1 if otherRat in [asMageRat, asStrongRat] else 2))
 for exRat in [asMageRat, asStrongRat]]
 for otherRat in [ffRat, scRat, sfRat, asMageRat, asStrongRat]]
storehouseDungeon = DungeonData("Abandoned Storehouse", "Storehouse", DungeonCategory.NORMAL,
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


damageTestDungeon = DungeonData("Analysis Room", "Analysis", DungeonCategory.SPECIAL,
                                "A hidden annex of the building next to the Training Yard. Only adventurers of some amount of renown are allowed inside.\n" +
                                "Within is said to preside a mysterious automaton. It does not seem to pose any danger, nor does it seem to receive any damage; thus, its purpose has become to be beat up for casual entertainment.",
                                "1 EXP",
                                set([Milestones.ABANDONED_STOREHOUSE_COMPLETE]),
                                4, 5, True, 1, 1,
                                [
                                    SettingsDungeonRoomData(
                                        [([damageTestDummy], 1)], [
                                            IntRoomSetting("Turns", "turns", "Number of dummy's turns to analyze for.", 10, 1, 30, [1, 5]),
                                            IntRoomSetting("Level", "level", "Level of the training dummy.", 5, 1, 20, [1, 5]),
                                            IntRoomSetting("DEF", "def", "Defense of the training dummy.", 50, 5, 10000, [5, 25, 100, 500]),
                                            IntRoomSetting("RES", "res", "Resistance of the training dummy.", 50, 5, 10000, [5, 25, 100, 500]),
                                            IntRoomSetting("AVO", "avo", "Avoidability of the training dummy.", 50, 5, 10000, [5, 25, 100, 500]),
                                            IntRoomSetting("SPD", "spd", "Speed of the training dummy.", 25, 5, 10000, [5, 25, 100, 500])
                                        ], "analysisRoom"
                                    )
                                ],
                                lambda _1, _2: EnemyReward(0, 0, 0, None, set([Milestones.ANALYSIS_ROOM_COMPLETE])),
                                Milestones.ANALYSIS_ROOM_COMPLETE)

arAttackerOptions = [arenaMercenary, arenaSniper, arenaAssassin, arenaWizard ]
arDefenderOptions = [arenaKnight, arenaAcrobat]
arSupportOptions = [arenaHunter, arenaSaint]
arPairs = [(combo, 1) for combo in enemyCombosIter(arAttackerOptions + arDefenderOptions + arSupportOptions, 2)]
arTrios = [(combo, 1) for combo in enemyCombosIter(arAttackerOptions + arDefenderOptions + arSupportOptions, 3)]
arBalanced = []
for attacker in arAttackerOptions:
    for defender in arDefenderOptions:
        for support in arSupportOptions:
            arBalanced.append(([attacker, defender, support], 1))
arenaDungeon = DungeonData("Arena: Lightweight Bracket", "Arena I", DungeonCategory.NORMAL,
                           "The city's arena holds tournaments between adventurer teams, offering a fresh experience for the rat-dungeon-weary.\n" +
                           "This tournament is intended for newer adventurers with minimal renown. While there is a small prize, it mostly pays in experience.",
                           "~90 EXP",
                           set([Milestones.ABANDONED_STOREHOUSE_COMPLETE]),
                           3, 6, False, 1, 1,
                           [
                               DungeonRoomData(arPairs, {'roomNumber': 0 }),
                               DungeonRoomData(arPairs, {'roomNumber': 1 }),
                               DungeonRoomData(arTrios, {'roomNumber': 2 }),
                               DungeonRoomData(arTrios, {'roomNumber': 3 }),
                               DungeonRoomData(arBalanced, {'roomNumber': 4 })
                           ],
                           lambda controller, player: EnemyReward(15, 3, 0,
                                                          makeBasicCommonDrop(controller.rng, MAX_ITEM_RANK, MAX_ITEM_RANK, 1),
                                                          set([Milestones.ARENA_I_COMPLETE])),
                        Milestones.ARENA_I_COMPLETE)

pvpDungeon = DungeonData("Open Arena", "Arena PvP", DungeonCategory.SPECIAL,
                                "Champions have free access to the city's arena when tournaments are not in progress, providing a popular sparring ground.\n" +
                                "Most adventurer's skills are not built for fighting other adventurers, but as with the normal arena, most of the charm is in the variety.",
                                "Bragging Rights",
                                set([Milestones.ARENA_I_COMPLETE]),
                                6, 1, False, 1, 1,
                                [
                                    SettingsDungeonRoomData(
                                        [([damageTestDummy], 1)], [
                                            PlayerTeamRoomSetting("{} Team", "playerTeam0", "Team selected for {}.", True, 0),
                                            PlayerTeamRoomSetting("{} Team", "playerTeam1", "Team selected for {}.", False, 1),
                                            PlayerTeamRoomSetting("{} Team", "playerTeam2", "Team selected for {}.", True, 2),
                                            PlayerTeamRoomSetting("{} Team", "playerTeam3", "Team selected for {}.", False, 3),
                                            PlayerTeamRoomSetting("{} Team", "playerTeam4", "Team selected for {}.", True, 4),
                                            PlayerTeamRoomSetting("{} Team", "playerTeam5", "Team selected for {}.", False, 5)
                                        ], "pvpRoom"
                                    )
                                ],
                                lambda _1, _2: EnemyReward(0, 0, 0, None, set([Milestones.ARENA_PVP_COMPLETE])),
                                Milestones.ARENA_PVP_COMPLETE, True)