from __future__ import annotations
from random import Random
from typing import Callable

from rpg_combat_interface import CombatInputHandler, CombatInterface, EnemyInputHandler, LocalPlayerInputHandler
from rpg_consts import *
from rpg_combat_entity import *
from rpg_messages import MessageCollector

class DungeonData(object):
    def __init__(self, dungeonName : str, allowRetryFights : bool, hpBetweenRooms : float, mpBetweenRooms : float,
                 dungeonRooms: list[DungeonRoomData], rewardFn: Callable[[DungeonController, CombatEntity], EnemyReward]):
        self.dungeonName = dungeonName
        self.allowRetryFights = allowRetryFights
        self.hpBetweenRooms = hpBetweenRooms
        self.mpBetweenRooms = mpBetweenRooms
        self.dungeonRooms = dungeonRooms
        self.rewardFn = rewardFn

    def getReward(self, controller : DungeonController, player : CombatEntity):
        return self.rewardFn(controller, player)
    
class DungeonRoomData(object):
    def __init__(self, enemyGroupWeights : list[tuple[list[Callable[[], Enemy]], int]]):
        self.enemyGroups = [egw[0] for egw in enemyGroupWeights]
        self.weights = [egw[1] for egw in enemyGroupWeights]

    def spawnEnemies(self, controller : DungeonController) -> list[Enemy]:
        roll = controller.rng.randrange(sum(self.weights))
        groupIndex = 0
        while roll > self.weights[groupIndex] and groupIndex <= len(self.enemyGroups) - 1:
            roll -= self.weights[groupIndex]
            groupIndex += 1
        
        return [spawner() for spawner in self.enemyGroups[groupIndex]]
    
class DungeonController(object):
    def __init__(self, dungeonData : DungeonData, playerTeam : list[Player],
                 startingPlayerTeamDistances : dict[CombatEntity, int], loggers : list[MessageCollector]):
        self.dungeonData = dungeonData
        self.playerTeam = playerTeam
        self.startingPlayerTeamDistances = startingPlayerTeamDistances
        self.loggers = loggers

        self.rng = Random()
        self.currentRoom = 0
        self.totalRooms = len(self.dungeonData.dungeonRooms)
        self.currentEnemyTeam : list[Enemy] = []
        self.currentCombatInterface : CombatInterface | None = None

    def logMessage(self, messageType : MessageType, messageText : str):
        [log.addMessage(messageType, messageText) for log in self.loggers]

    def beginRoom(self) -> CombatInterface | None:
        if self.currentRoom < self.totalRooms:
            # TODO: player input handlers initialized by some higher-level handler?
            playerHandlerMap : dict[CombatEntity, CombatInputHandler] = {player: LocalPlayerInputHandler(player) for player in self.playerTeam}
            nextRoom = self.dungeonData.dungeonRooms[self.currentRoom]
            self.currentEnemyTeam = nextRoom.spawnEnemies(self)
            enemyHandlerMap : dict[CombatEntity, CombatInputHandler] = {enemy: EnemyInputHandler(enemy) for enemy in self.currentEnemyTeam}
            self.currentCombatInterface = CombatInterface(playerHandlerMap, enemyHandlerMap, self.loggers)
            return self.currentCombatInterface
    
    def completeRoom(self) -> dict[Player, DungeonReward] | None:
        if self.currentCombatInterface is not None and self.currentCombatInterface.cc.checkPlayerVictory():
            rewards = {player : DungeonReward() for player in self.playerTeam}
            for enemy in self.currentEnemyTeam:
                [rewards[player].addEnemyReward(enemy.getReward(self.currentCombatInterface.cc, player)) for player in self.playerTeam]

            self.currentRoom += 1
            self.currentCombatInterface = None
            self.currentEnemyTeam = []
            return rewards
        
    def completeDungeon(self) -> dict[Player, DungeonReward] | None:
        if self.currentCombatInterface is None and self.currentRoom == self.totalRooms:
            rewards = {player : DungeonReward() for player in self.playerTeam}
            [rewards[player].addEnemyReward(self.dungeonData.getReward(self, player)) for player in self.playerTeam]
            return rewards

class DungeonReward(object):
    def __init__(self):
        self.exp = 0
        self.wup = 0
        self.swup = 0
        self.equips = []

    def addEnemyReward(self, enemyReward : EnemyReward):
        self.exp += enemyReward.exp
        self.wup += enemyReward.wup
        self.swup += enemyReward.swup
        if enemyReward.equip is not None:
            self.equips.append(enemyReward.equip)