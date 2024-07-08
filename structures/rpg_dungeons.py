from __future__ import annotations
import asyncio
import math
from random import Random
from typing import Callable

from structures.rpg_combat_interface import CombatInputHandler, CombatInterface, EnemyInputHandler, LocalPlayerInputHandler
from rpg_consts import *
from structures.rpg_combat_entity import *
from structures.rpg_messages import MessageCollector, makeTeamString

class DungeonData(object):
    registeredDungeons : list[DungeonData] = []

    def __init__(self, dungeonName : str, shortDungeonName : str, description : str, rewardDescription : str, milestoneRequirements : set[Milestones],
                 maxPartySize : int, recLevel : int, allowRetryFights : bool, hpBetweenRooms : float, mpBetweenRooms : float,
                dungeonRooms: list[DungeonRoomData], rewardFn: Callable[[DungeonController, Player], EnemyReward], clearFlag : Milestones):
        self.dungeonName = dungeonName
        self.shortDungeonName = shortDungeonName
        self.description = description
        self.rewardDescription = rewardDescription
        self.milestoneRequirements = milestoneRequirements
        self.maxPartySize = maxPartySize
        self.recLevel = recLevel
        self.allowRetryFights = allowRetryFights
        self.hpBetweenRooms = hpBetweenRooms
        self.mpBetweenRooms = mpBetweenRooms
        self.dungeonRooms = dungeonRooms
        self.rewardFn = rewardFn
        self.clearFlag = clearFlag

        DungeonData.registeredDungeons.append(self)

    def getReward(self, controller : DungeonController, player : Player):
        return self.rewardFn(controller, player)
    
    def meetsRequirements(self, player : Player) -> bool:
        return len(self.milestoneRequirements.intersection(player.milestones)) == len(self.milestoneRequirements)
    
class DungeonRoomData(object):
    def __init__(self, enemyGroupWeights : list[tuple[list[Callable[[dict], Enemy]], int]], params : dict):
        self.enemyGroups = [egw[0] for egw in enemyGroupWeights]
        self.weights = [egw[1] for egw in enemyGroupWeights]
        self.previousSpawners : list[Callable[[dict], Enemy]] = []
        self.params = params

    def spawnEnemies(self, controller : DungeonController, retry : bool) -> list[Enemy]:
        if not retry:
            roll = controller.rng.randrange(sum(self.weights))
            groupIndex = 0
            while roll >= self.weights[groupIndex] and groupIndex <= len(self.enemyGroups) - 1:
                roll -= self.weights[groupIndex]
                groupIndex += 1
            
            self.previousSpawners = self.enemyGroups[groupIndex]

        return [spawner(self.params) for spawner in self.previousSpawners]
    
class DungeonController(object):
    def __init__(self, dungeonData : DungeonData, playerTeamHandlers : dict[Player, DungeonInputHandler],
                 startingPlayerTeamDistances : dict[CombatEntity, int], loggers : dict[Player, MessageCollector]):
        self.dungeonData = dungeonData
        self.playerTeamHandlers = playerTeamHandlers
        self.startingPlayerTeamDistances = startingPlayerTeamDistances
        self.loggers = loggers

        self.playersToRemove : list[Player] = []

        self.combatReadyFlag = asyncio.Event()
        self.combatIsActive = False
        self.waitingForReady = False
        self.waitingForRetry = False

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

    def combatActive(self) -> bool:
        return self.combatIsActive

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
                                                          self.currentHealth, self.currentMana, self.startingPlayerTeamDistances)
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
        
    def removePlayer(self, player : Player):
        if self.combatActive():
            assert(self.currentCombatInterface is not None)
            self.currentCombatInterface.removePlayer(player)
            self.playersToRemove.append(player)
        else:
            handler = self.playerTeamHandlers.pop(player, None)
            if handler is not None:
                handler.onPlayerLeaveDungeon()

        self.loggers.pop(player, None)
        self.logMessage(MessageType.BASIC, f"{player.name} escaped from the dungeon.")
        self.sendAllLatestMessages()

    def _scaleDungeonExp(self, player : Player, exp : int) -> int:
        if player.level < self.dungeonData.recLevel:
            return exp
        levelDiff = player.level - self.dungeonData.recLevel
        if levelDiff <= 2:
            return exp
        scaling = 2 ** (-(levelDiff - 2) / 3)
        return math.ceil(exp * scaling)
        
    async def handleRewardsForPlayer(self, player : Player, reward : DungeonReward):
        scaledExp = self._scaleDungeonExp(player, reward.exp)
        levelUp, rankUp = player.gainExp(scaledExp)
        self.loggers[player].addMessage(
            MessageType.BASIC, f"*Gained **{scaledExp} EXP!***{' *(Scaled down because you outlevel this dungeon.)*' if scaledExp != reward.exp else ''}"
        )
        if levelUp:
            self.loggers[player].addMessage(
                MessageType.BASIC, f"**Your level increased to {player.level}! Gained {STAT_POINTS_PER_LEVEL} stat points.**"
            )
        if rankUp:
            classData =  PlayerClassData.PLAYER_CLASS_DATA_MAP[player.currentPlayerClass]
            newSkillData = classData.getSingleSkillForRank(player.currentPlayerClass, player.classRanks[player.currentPlayerClass])
            newSkillString = f" Gained new skill: {newSkillData.skillName}!" if newSkillData is not None else "" 
            self.loggers[player].addMessage(
                MessageType.BASIC, f"**Your {classData.className.name[0] + classData.className.name[1:].lower()}" +
                    f" rank increased to {player.classRanks[player.currentPlayerClass]}!{newSkillString}**"
            )
        
        player.wup += reward.wup
        player.swup += reward.swup
        player.milestones = player.milestones.union(reward.milestones)
        wupString = f"**{reward.wup} WUP**" if reward.wup > 0 else ""
        swupString = f"**{reward.swup} SWUP**" if reward.swup > 0 else ""
        andString = " and " if reward.wup > 0 and reward.swup > 0 else ""
        if reward.wup > 0 or reward.swup > 0:
            self.loggers[player].addMessage(
                MessageType.BASIC, f"*Picked up {wupString}{andString}{swupString}!*"
            )

        for equip in reward.equips:
            self.loggers[player].addMessage(
                MessageType.BASIC, f"*Picked up {equip.name}!*"
            )
            self.sendAllLatestMessages()
            await self.playerTeamHandlers[player].getEquip(self, equip)

        # self.loggers[player].addMessage(
        #     MessageType.BASIC, f"*Waiting for teammates...*"
        # )
        self.sendAllLatestMessages()

    async def _processRetry(self) -> bool:
        confirmRetry = False
        if self.dungeonData.allowRetryFights:
            self.waitingForRetry = True
            checkRetries : list[int] = await asyncio.gather(*[handler.waitDungeonRetryResponse(self)
                                                            for handler in self.playerTeamHandlers.values()])
            self.waitingForRetry = False
            # Previously wanted to end run if anyone declined to retry
            # Now just continues with remaining party members if anyone leaves
            if len(checkRetries) > 0: # and all([response for response in checkRetries]):
                confirmRetry = True
                self.doDungeonRestoration()
                self.currentCombatInterface = None

        if confirmRetry:
            return True
        else:
            [handler.onDungeonFail() for handler in self.playerTeamHandlers.values()]
            self.sendAllLatestMessages()
            return False
        
    async def _processReady(self):
        self.waitingForReady = True
        await asyncio.gather(*[self.playerTeamHandlers[player].waitReady(self) for player in self.playerTeamHandlers])
        self.waitingForReady = False

    def loadCheckWaiting(self):
        return self.waitingForReady or self.waitingForRetry
        
    """
        Returns true if the run is successful.
    """
    async def runDungeon(self, reload : bool) -> bool:
        if not reload:
            plural = "s" if len(self.playerTeamHandlers) == 1 else ""
            self.logMessage(MessageType.BASIC,
                            f"*{makeTeamString([player for player in self.playerTeamHandlers])} enter{plural} {self.dungeonData.dungeonName}...*\n")

        while self.currentRoom < self.totalRooms:
            if not self.loadCheckWaiting():
                if len(self.playerTeamHandlers) == 0:
                    return False
                
                if reload:
                    self.currentCombatInterface = None

                self.beginRoom()
                assert (self.currentCombatInterface is not None)

                self.combatIsActive = True
                await self.currentCombatInterface.runCombat(self.combatReadyFlag)
                self.combatIsActive = False

                self.combatReadyFlag.clear()
                for player in self.playersToRemove:
                    self.playerTeamHandlers.pop(player, None)
                self.playersToRemove = []

                if not self.currentCombatInterface.cc.checkPlayerVictory():
                    if not (await self._processRetry()):
                        return False
                else:
                    rewardMap = self.completeRoom()
                    assert(rewardMap is not None)
                    await asyncio.gather(*[self.handleRewardsForPlayer(player, rewardMap[player]) for player in self.playerTeamHandlers])
                    if self.currentRoom < self.totalRooms:
                        await self._processReady()
                        if len(self.playerTeamHandlers) == 0:
                            return False
            else:
                # Attempt to handle interruptions between rooms
                assert(reload)
                if self.waitingForRetry:
                    if not (await self._processRetry()):
                        return False
                else:
                    await self._processReady()

        self.logMessage(MessageType.BASIC,
                        f"**{makeTeamString([player for player in self.playerTeamHandlers])} cleared {self.dungeonData.dungeonName}!**\n")
        rewardMap = self.completeDungeon()
        assert(rewardMap is not None)
        await asyncio.gather(*[self.handleRewardsForPlayer(player, rewardMap[player]) for player in self.playerTeamHandlers])
        self.sendAllLatestMessages()
        [self.playerTeamHandlers[player].onDungeonComplete() for player in self.playerTeamHandlers]

        return True


class DungeonReward(object):
    def __init__(self):
        self.exp = 0
        self.wup = 0
        self.swup = 0
        self.equips : list[Equipment] = []
        self.milestones : set[Milestones] = set()

    def addEnemyReward(self, enemyReward : EnemyReward):
        self.exp += enemyReward.exp
        self.wup += enemyReward.wup
        self.swup += enemyReward.swup
        self.milestones = self.milestones.union(enemyReward.milestones)
        if enemyReward.equip is not None:
            self.equips.append(enemyReward.equip)


class DungeonInputHandler(object):
    def __init__(self, player : Player, combatInputControllerClass : type[CombatInputHandler]):
        self.player = player
        self.combatInputControllerClass = combatInputControllerClass

    def makeCombatInputController(self):
        return self.combatInputControllerClass(self.player)
    
    def onPlayerLeaveDungeon(self):
        raise NotImplementedError()
    
    def onDungeonComplete(self):
        return True
    
    def onDungeonFail(self):
        return True
    
    """
        Promps the player to retry after a failed fight.
        Returns whether or not the retry is accepted.
    """
    async def waitDungeonRetryResponse(self, dungeonController : DungeonController):
        return True

    """
        Waits for the player to be ready for the dungeon rooms.
        Allows free skills, equips, and formation positions to be changed.
    """
    async def waitReady(self, dungeonController : DungeonController):
        # TODO
        # add a "waiting for allies" message before returning
        return True
    
    """
        Picks up a new equip; if inventory is full, gives the player the option to
        drop something from their inventory. (Should give a confirmation prompt as well; maybe add a way to lock items later?)
    """
    async def getEquip(self, dungeonController : DungeonController, newEquip : Equipment):
        hadSpace = self.player.storeEquipItem(newEquip)
        if not hadSpace:
            # TODO
            pass