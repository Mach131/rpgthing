from __future__ import annotations
import asyncio
from random import Random
from typing import Callable

from structures.rpg_combat_interface import CombatInputHandler, CombatInterface, EnemyInputHandler, LocalPlayerInputHandler
from rpg_consts import *
from structures.rpg_combat_entity import *
from structures.rpg_messages import MessageCollector, makeTeamString

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
        self.previousSpawners : list[Callable[[], Enemy]] = []

    def spawnEnemies(self, controller : DungeonController, retry : bool) -> list[Enemy]:
        if not retry:
            roll = controller.rng.randrange(sum(self.weights))
            groupIndex = 0
            while roll > self.weights[groupIndex] and groupIndex <= len(self.enemyGroups) - 1:
                roll -= self.weights[groupIndex]
                groupIndex += 1
            
            self.previousSpawners = self.enemyGroups[groupIndex]

        return [spawner() for spawner in self.previousSpawners]
    
class DungeonController(object):
    def __init__(self, dungeonData : DungeonData, playerTeamHandlers : dict[Player, DungeonInputHandler],
                 startingPlayerTeamDistances : dict[CombatEntity, int], loggers : dict[Player, MessageCollector]):
        self.dungeonData = dungeonData
        self.playerTeamHandlers = playerTeamHandlers
        self.startingPlayerTeamDistances = startingPlayerTeamDistances
        self.loggers = loggers

        self.rng = Random()
        self.currentRoom = 0
        self.totalRooms = len(self.dungeonData.dungeonRooms)
        self.currentEnemyTeam : list[Enemy] = []
        self.currentCombatInterface : CombatInterface | None = None
        self.currentHealth : dict[CombatEntity, int] = {player : player.getStatValue(BaseStats.HP) for player in self.playerTeamHandlers}
        self.currentMana : dict[CombatEntity, int] = {player : player.getStatValue(BaseStats.MP) for player in self.playerTeamHandlers}
        
    def sendAllLatestMessages(self):
        [logger.sendNewestMessages(None, False) for logger in self.loggers.values()]

    def logMessage(self, messageType : MessageType, messageText : str):
        [log.addMessage(messageType, messageText) for log in self.loggers.values()]

    def beginRoom(self) -> CombatInterface | None:
        if self.currentRoom < self.totalRooms and self.currentCombatInterface is None:
            playerHandlerMap : dict[CombatEntity, CombatInputHandler] = {player: self.playerTeamHandlers[player].makeCombatInputController()
                                                                         for player in self.playerTeamHandlers}
            nextRoom = self.dungeonData.dungeonRooms[self.currentRoom]

            if len(self.currentEnemyTeam) == 0:
                self.currentEnemyTeam = nextRoom.spawnEnemies(self, False)
            else:
                self.currentEnemyTeam = nextRoom.spawnEnemies(self, True)

            enemyHandlerMap : dict[CombatEntity, CombatInputHandler] = {enemy: EnemyInputHandler(enemy) for enemy in self.currentEnemyTeam}
            self.currentCombatInterface = CombatInterface(playerHandlerMap, enemyHandlerMap, {player : self.loggers[player] for player in self.loggers},
                                                          self.currentHealth, self.currentMana)
            return self.currentCombatInterface
    
    def completeRoom(self) -> dict[Player, DungeonReward] | None:
        if self.currentCombatInterface is not None and self.currentCombatInterface.cc.checkPlayerVictory():
            rewards = {player : DungeonReward() for player in self.playerTeamHandlers}
            for enemy in self.currentEnemyTeam:
                [rewards[player].addEnemyReward(enemy.getReward(self.currentCombatInterface.cc, player)) for player in self.playerTeamHandlers]

            self.currentRoom += 1

            if self.currentRoom < self.totalRooms:
                self.doDungeonRestoration()

            self.currentCombatInterface = None
            self.currentEnemyTeam = []
            return rewards
        
    def doDungeonRestoration(self):
        if self.currentCombatInterface is not None:
            combatController : CombatController = self.currentCombatInterface.cc
            for player in self.playerTeamHandlers:
                combatController.gainHealth(player, round(combatController.getMaxHealth(player) * self.dungeonData.hpBetweenRooms))
                self.currentHealth[player] = combatController.getCurrentHealth(player)
                combatController.gainMana(player, round(combatController.getMaxMana(player) * self.dungeonData.mpBetweenRooms))
                self.currentMana[player] = combatController.getCurrentMana(player)
            self.sendAllLatestMessages()
        
    def completeDungeon(self) -> dict[Player, DungeonReward] | None:
        if self.currentCombatInterface is None and self.currentRoom == self.totalRooms:
            rewards = {player : DungeonReward() for player in self.playerTeamHandlers}
            [rewards[player].addEnemyReward(self.dungeonData.getReward(self, player)) for player in self.playerTeamHandlers]
            return rewards
        
    async def handleRewardsForPlayer(self, player : Player, reward : DungeonReward):
        levelUp, rankUp = player.gainExp(reward.exp)
        self.loggers[player].addMessage(
            MessageType.BASIC, f"Gained {reward.exp} EXP!"
        )
        if levelUp:
            self.loggers[player].addMessage(
                MessageType.BASIC, f"Your level increased to {player.level}! Gained {STAT_POINTS_PER_LEVEL} stat points."
            )
        if rankUp:
            classData =  PlayerClassData.PLAYER_CLASS_DATA_MAP[player.currentPlayerClass]
            newSkillData = classData.getSingleSkillForRank(player.currentPlayerClass, player.classRanks[player.currentPlayerClass])
            newSkillString = f" Gained new skill: {newSkillData.skillName}!" if newSkillData is not None else "" 
            self.loggers[player].addMessage(
                MessageType.BASIC, f"Your {classData.className.name[0] + classData.className.name[1:].lower()}" +
                    f" rank increased to {player.classRanks[player.currentPlayerClass]}!{newSkillString}"
            )
        
        player.wup += reward.wup
        player.swup += reward.swup
        swupString = f" and {reward.swup} SWUP" if reward.swup > 0 else ""
        self.loggers[player].addMessage(
            MessageType.BASIC, f"Picked up {reward.wup} WUP{swupString}!"
        )

        for equip in reward.equips:
            self.loggers[player].addMessage(
                MessageType.BASIC, f"Picked up {equip.name}!"
            )
            self.sendAllLatestMessages()
            await self.playerTeamHandlers[player].getEquip(self, equip)

        self.loggers[player].addMessage(
            MessageType.BASIC, f"Waiting for teammates..."
        )
        self.sendAllLatestMessages()

        
    """
        Returns true if the run is successful.
    """
    async def runDungeon(self) -> bool:
        plural = "s" if len(self.playerTeamHandlers) == 1 else ""
        self.logMessage(MessageType.BASIC,
                        f"{makeTeamString([player for player in self.playerTeamHandlers])} enter{plural} {self.dungeonData.dungeonName}...\n")
        
        while self.currentRoom < self.totalRooms:
            combatInterface = self.beginRoom()
            assert (self.currentCombatInterface is not None)

            await self.currentCombatInterface.runCombat()

            if not self.currentCombatInterface.cc.checkPlayerVictory():
                if self.dungeonData.allowRetryFights:
                    checkRetries : list[int] = await asyncio.gather(*[handler.makeChoice(self, ["Retry Fight", "Give Up"])
                                                                      for handler in self.playerTeamHandlers.values()])
                    if all([response == 0 for response in checkRetries]):
                        self.doDungeonRestoration()
                        self.currentCombatInterface = None
                    else:
                        return False
                    
            else:
                rewardMap = self.completeRoom()
                assert(rewardMap is not None)
                await asyncio.gather(*[self.handleRewardsForPlayer(player, rewardMap[player]) for player in self.playerTeamHandlers])
                if self.currentRoom < self.totalRooms:
                    await asyncio.gather(*[self.playerTeamHandlers[player].waitReady(self) for player in self.playerTeamHandlers])
        
        self.logMessage(MessageType.BASIC,
                        f"{makeTeamString([player for player in self.playerTeamHandlers])} cleared {self.dungeonData.dungeonName}!\n")
        rewardMap = self.completeDungeon()
        assert(rewardMap is not None)
        await asyncio.gather(*[self.handleRewardsForPlayer(player, rewardMap[player]) for player in self.playerTeamHandlers])
        if self.currentRoom < self.totalRooms:
            await asyncio.gather(*[self.playerTeamHandlers[player].waitReady(self) for player in self.playerTeamHandlers])

        self.sendAllLatestMessages()
        return True


class DungeonReward(object):
    def __init__(self):
        self.exp = 0
        self.wup = 0
        self.swup = 0
        self.equips : list[Equipment] = []

    def addEnemyReward(self, enemyReward : EnemyReward):
        self.exp += enemyReward.exp
        self.wup += enemyReward.wup
        self.swup += enemyReward.swup
        if enemyReward.equip is not None:
            self.equips.append(enemyReward.equip)


class DungeonInputHandler(object):
    def __init__(self, player : Player, combatInputControllerClass : type[CombatInputHandler]):
        self.player = player
        self.combatInputControllerClass = combatInputControllerClass

    def makeCombatInputController(self):
        return self.combatInputControllerClass(self.player)

    """
        Waits for the player to be ready for the dungeon rooms.
        Allows free skills, equips, and formation positions to be changed.
    """
    async def waitReady(self, dungeonController : DungeonController):
        # TODO
        # add a "waiting for allies" message before returning
        return True
    
    """
        Allows the player to choose between a set of text options.
        Returns the index of the selection.
    """
    async def makeChoice(self, dungeonController : DungeonController, options : list[str]):
        # TODO: offer choice of options
        return 0
    
    """
        Picks up a new equip; if inventory is full, gives the player the option to
        drop something from their inventory. (Should give a confirmation prompt as well; maybe add a way to lock items later?)
    """
    async def getEquip(self, dungeonController : DungeonController, newEquip : Equipment):
        hadSpace = self.player.storeEquipItem(newEquip)
        if not hadSpace:
            # TODO
            pass