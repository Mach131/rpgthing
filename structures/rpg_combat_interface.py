from __future__ import annotations
import asyncio
import random

from structures.rpg_classes_skills import ActiveSkillDataSelector, ActiveToggleSkillData, AttackSkillData, SkillData
from structures.rpg_combat_entity import CombatEntity, Enemy, Player
from structures.rpg_combat_state import ActionResultInfo, CombatController
from rpg_consts import *
from structures.rpg_messages import MessageCollector

class CombatInputHandler(object):
    def __init__(self, entity : CombatEntity):
        self.entity : CombatEntity = entity

    def doAttack(self, combatController : CombatController, target : CombatEntity,
                 isPhysical : bool | None, attackType : AttackType | None, isBasic : bool,
                 bonusAttackData : list[tuple[CombatEntity, CombatEntity, AttackSkillData]]):
        if isBasic:
            isPhysical = self.entity.basicAttackType != AttackType.MAGIC
        assert(isPhysical is not None)
        combatController.performAttack(self.entity, target, isPhysical, attackType, isBasic, bonusAttackData)

    def _doReactionAttack(self, combatController : CombatController, user : CombatEntity, target : CombatEntity,
                          attackData : AttackSkillData, additionalAttacks : list[tuple[CombatEntity, CombatEntity, AttackSkillData]]):
        combatController.performReactionAttack(self.entity, user, target, attackData, additionalAttacks)

    def doSkill(self, combatController : CombatController, targets : list[CombatEntity], skillData : SkillData) -> ActionResultInfo:
        actionResult : ActionResultInfo = combatController.performActiveSkill(self.entity, targets, skillData)
        if actionResult.success == ActionSuccessState.SUCCESS:
            if actionResult.startAttack:
                assert(isinstance(skillData, AttackSkillData))
                assert(actionResult.attackTarget is not None)
                self.doAttack(combatController, actionResult.attackTarget, skillData.isPhysical,
                              skillData.attackType, False, actionResult.reactionAttackData)
            elif len(actionResult.reactionAttackData) > 0:
                reactionData = actionResult.reactionAttackData[0]
                reactionFollowups = actionResult.reactionAttackData[1:]
                self._doReactionAttack(combatController, reactionData[0], reactionData[1], reactionData[2], reactionFollowups)
        return actionResult
    
    def doReposition(self, combatController : CombatController, targets : list[CombatEntity], distanceChange : int) -> bool:
        repositionResult = combatController.performReposition(self.entity, targets, distanceChange)
        if not repositionResult.success:
            return False
        
        if repositionResult.startAttack:
            assert(repositionResult.attackUser is not None)
            assert(repositionResult.attackTarget is not None)
            assert(repositionResult.attackData is not None)
            self._doReactionAttack(combatController, repositionResult.attackUser, repositionResult.attackTarget,
                                   repositionResult.attackData, repositionResult.additionalAttacks)
        return True
    
    def doDefend(self, combatController : CombatController) -> None:
        combatController.performDefend(self.entity)

    def onPlayerLeaveDungeon(self) -> None:
        raise NotImplementedError()

    async def takeTurn(self, combatController : CombatController) -> None:
        raise NotImplementedError()
    
class RandomEntityInputHandler(CombatInputHandler):
    def __init__(self, entity : CombatEntity, sleepTime : float):
        super().__init__(entity)
        self.sleepTime = sleepTime

    async def takeTurn(self, combatController : CombatController) -> None:
        targetList = combatController.getTargets(self.entity)
        teammateList = combatController.getTeammates(self.entity)

        attackTargets = []
        for target in combatController.getTargets(self.entity):
            if combatController.checkInRange(self.entity, target):
                attackTargets.append(target)

        availableSkills = []
        for skill in self.entity.availableActiveSkills:
            manaCost = combatController.getSkillManaCost(self.entity, skill)
            if manaCost is None or combatController.getCurrentMana(self.entity) >= manaCost:
                availableSkills.append(skill)

        approachTargets = []
        for target in combatController.getTargets(self.entity):
            if combatController.checkDistanceStrict(self.entity, target) > 0:
                approachTargets.append(target)

        retreatTargets = []
        for target in combatController.getTargets(self.entity):
            if combatController.checkDistanceStrict(self.entity, target) < MAX_DISTANCE:
                retreatTargets.append(target)

        while True:
            availableCommands = ["defend"]
            if len(attackTargets) > 0:
                availableCommands.append("attack")
            if len(availableSkills) > 0:
                availableCommands.append("skill")
            if len(approachTargets) > 0:
                availableCommands.append("approach")
            if len(retreatTargets) > 0:
                availableCommands.append("retreat")
            command = random.choice(availableCommands)

            if command == "attack":
                target = random.choice(attackTargets)
                self.doAttack(combatController, target, None, None, True, [])
                await asyncio.sleep(self.sleepTime)
                return
            elif command == "skill":
                chosenSkill = random.choice(availableSkills)
                originalChosenSkill = chosenSkill

                if isinstance(chosenSkill, ActiveSkillDataSelector):
                    chosenSkill = chosenSkill.selectSkill(random.choice(chosenSkill.options))

                targets = []
                targetCount = 1 if chosenSkill.expectedTargets is None else chosenSkill.expectedTargets
                if chosenSkill.targetOpponents:
                    if chosenSkill.causesAttack:
                        if len(attackTargets) >= targetCount:
                            targets = random.sample(attackTargets, targetCount)
                        else:
                            availableSkills.remove(originalChosenSkill)
                            continue
                    else:
                        targets = random.sample(targetList, targetCount)
                else:
                    targets = random.sample(teammateList, targetCount)

                skillResult = self.doSkill(combatController, targets, chosenSkill)
                if skillResult.success == ActionSuccessState.SUCCESS:
                    await asyncio.sleep(self.sleepTime)
                    return
                # elif skillResult.success == ActionSuccessState.FAILURE_MANA:
                #     print("You do not have enough MP to use this skill.")
                # elif skillResult.success == ActionSuccessState.FAILURE_TARGETS:
                    #     print("Invalid target(s) for this skill.")

            elif command == "approach":
                targets = random.sample(approachTargets, random.choice([1, 2])) if len(approachTargets) > 1 else approachTargets

                amount = random.choice([1, MAX_SINGLE_REPOSITION])
                if amount < 0 or amount > MAX_SINGLE_REPOSITION:
                    print("You may change your distance by at most 2 on your turn.")
                    
                if self.doReposition(combatController, targets, -amount):
                    await asyncio.sleep(self.sleepTime)
                    return

            elif command == "retreat":
                targets = random.sample(retreatTargets, random.choice([1, 2])) if len(retreatTargets) > 1 else retreatTargets

                amount = random.choice([1, MAX_SINGLE_REPOSITION])
                if amount < 0 or amount > MAX_SINGLE_REPOSITION:
                    print("You may change your distance by at most 2 on your turn.")
                    
                if self.doReposition(combatController, targets, amount):
                    await asyncio.sleep(self.sleepTime)
                    return
                
            elif command == "defend":
                self.doDefend(combatController)
                await asyncio.sleep(self.sleepTime)
                return
            
            else:
                print("Command not recognized; try again.")

class LocalPlayerInputHandler(CombatInputHandler):
    def __init__(self, player : Player):
        super().__init__(player)
        self.player : Player = player

    async def takeTurn(self, combatController : CombatController) -> None:
        while True:
            targetList = combatController.getTargets(self.player)
            print(f"What will {self.player.name} do? (attack, skill, approach, retreat, defend, check)")
            inp : str = input(">>> ")

            inpSplit = inp.strip().split()
            if len(inpSplit) == 0:
                continue
            command = inpSplit[0]

            if command == "attack":
                try:
                    index = int(inpSplit[1])
                    if index <= 0:
                        raise IndexError
                    target = targetList[index - 1]

                    isPhysical = self.player.basicAttackType != AttackType.MAGIC
                    self.doAttack(combatController, target, isPhysical, None, True, [])
                    return
                except ValueError:
                    print(f"Invalid target; use 'attack [index]'.")
                except IndexError:
                    print(f"Invalid target; use 'attack [index]' (there are currently {len(targetList)} targetable enemies).")

            elif command == "skill":
                if len(inpSplit) < 2:
                    print("Use 'skill [skillIndex] [targetIndices...]'.")
                else:
                    try:
                        skillIndex = int(inpSplit[1])
                        if skillIndex <= 0:
                            raise IndexError
                        chosenSkill = self.player.availableActiveSkills[skillIndex - 1]

                        targetIdx = 2
                        if isinstance(chosenSkill, ActiveSkillDataSelector):
                            try:
                                chosenSkill = chosenSkill.selectSkill(inpSplit[2].upper())
                                targetIdx = 3
                            except IndexError:
                                print("This skill expects additional parameters; check the description.")
                                continue
                            except KeyError:
                                print(f"Invalid parameter for this skill, options are: {', '.join(chosenSkill.options)}.")
                                continue

                        if not chosenSkill.targetOpponents:
                            targetList = combatController.getTeammates(self.player)
                        targetIndices = [int(inps) for inps in inpSplit[targetIdx:]]
                        if any([targetIndex <= 0 for targetIndex in targetIndices]):
                            raise IndexError
                        targets = [targetList[targetIndex - 1] for targetIndex in targetIndices]

                        skillResult = self.doSkill(combatController, targets, chosenSkill)
                        if skillResult.success == ActionSuccessState.SUCCESS:
                            return
                        elif skillResult.success == ActionSuccessState.FAILURE_MANA:
                            print("You do not have enough MP to use this skill.")
                        elif skillResult.success == ActionSuccessState.FAILURE_TARGETS:
                            print("Invalid target(s) for this skill.")
                    except ValueError:
                        print(f"Invalid target; use 'skill [skillIndex] [targetIndices...]'.")
                    except IndexError:
                        print(f"Invalid target; use 'skill [skillIndex] [targetIndices...]' (there are currently {len(targetList)} targets).")

            elif command == "approach":
                if len(inpSplit) < 3:
                    print("Use 'approach [targetIndices...] [amount]'.")
                else:
                    try:
                        targetIndices = [int(inps) for inps in inpSplit[1:-1]]
                        if any(map(lambda x: x <= 0, targetIndices)):
                            raise IndexError
                        targets = [targetList[targetIndex - 1] for targetIndex in targetIndices]

                        amount = int(inpSplit[-1])
                        if amount < 0 or amount > MAX_SINGLE_REPOSITION:
                            print("You may change your distance by at most 2 on your turn.")
                            
                        if self.doReposition(combatController, targets, -amount):
                            return
                        else:
                            print("Unable to approach these targets by this amount.")
                    except ValueError:
                        print(f"Invalid target or amount; use 'approach [targetIndices...] [amount]'.")
                    except IndexError:
                        print(f"Invalid target or amount; use 'approach [targetIndices...] [amount]' (there are currently {len(targetList)} targetable enemies).")

            elif command == "retreat":
                if len(inpSplit) < 3:
                    print("Use 'retreat [targetIndices...] [amount]'.")
                else:
                    try:
                        targetIndices = [int(inps) for inps in inpSplit[1:-1]]
                        if any(map(lambda x: x <= 0, targetIndices)):
                            raise IndexError
                        targets = [targetList[targetIndex - 1] for targetIndex in targetIndices]

                        amount = int(inpSplit[-1])
                        if amount < 0 or amount > MAX_SINGLE_REPOSITION:
                            print("You may change your distance by at most 2 on your turn.")
                            
                        if self.doReposition(combatController, targets, amount):
                            return
                        else:
                            print("Unable to retreat from these targets by these amounts.")
                    except ValueError:
                        print(f"Invalid target or amount; use 'retreat [targetIndices...] [amount]'.")
                    except IndexError:
                        print(f"Invalid target or amount; use 'retreat [targetIndices...] [amount]' (there are currently {len(targetList)} targetable enemies).")

            elif command == "defend":
                self.doDefend(combatController)
                return

            elif command == "check":
                if len(inpSplit) == 1:
                    self.doCheck(combatController, self.player)
                else:
                    idxIndex = 1
                    if inpSplit[1] == "ally":
                        targetList = combatController.getTeammates(self.player)
                        idxIndex = 2
                    
                    try:
                        index = int(inpSplit[idxIndex])
                        if index <= 0:
                            raise IndexError
                        target = targetList[index - 1]

                        self.doCheck(combatController, target)
                    except ValueError:
                        print(f"Invalid target; use 'check [index]' or 'check ally [index]'.")
                    except IndexError:
                        print(f"Invalid target; there are currently {len(targetList)} targets.")

            else:
                print("Command not recognized; try again.")

    def doCheck(self, combatController : CombatController, target : CombatEntity):
        print(combatController.getFullStatusStringFor(target))
        distance = combatController.checkDistance(self.player, target)
        if distance is not None:
            print(f"Current distance: {distance}")

        if target == self.player and len(self.player.availableActiveSkills) > 0:
            print("Your Skills:")
            for idx, skill in enumerate(self.player.availableActiveSkills):
                print(f"[{idx+1}] {skill.skillName} ({combatController.getSkillManaCost(target, skill)} MP): {skill.description}")
        else:
            nextActionTime = combatController.getTimeToFullAction(target) * ACTION_TIME_DISPLAY_MULTIPLIER
            print(f"Time to next action: {nextActionTime:.3f}")
        print()

class EnemyInputHandler(CombatInputHandler):
    def __init__(self, enemy : Enemy):
        super().__init__(enemy)
        self.enemy : Enemy = enemy

    async def takeTurn(self, combatController : CombatController) -> None:
        targetList = combatController.getTargets(self.entity)
        teammateList = combatController.getTeammates(self.entity)

        aiDecision = self.enemy.ai.chooseAction(combatController, self.enemy)

        if aiDecision.action == CombatActions.ATTACK:
            target = targetList[aiDecision.targetIndices[0]]
            self.doAttack(combatController, target, None, None, True, [])
            return
        elif aiDecision.action == CombatActions.SKILL:
            assert(aiDecision.skillIndex is not None)
            chosenSkill = self.entity.availableActiveSkills[aiDecision.skillIndex]

            if isinstance(chosenSkill, ActiveSkillDataSelector):
                assert(aiDecision.skillSelector) is not None
                chosenSkill = chosenSkill.selectSkill(aiDecision.skillSelector)

            skillTargetList = targetList if chosenSkill.targetOpponents else teammateList
            targets = [skillTargetList[i] for i in aiDecision.targetIndices]

            skillResult = self.doSkill(combatController, targets, chosenSkill)
            if skillResult.success == ActionSuccessState.SUCCESS:
                return

        elif aiDecision.action == CombatActions.APPROACH:
            targets = [targetList[i] for i in aiDecision.targetIndices]

            assert(aiDecision.actionParameter is not None)
            amount =  aiDecision.actionParameter
                
            if self.doReposition(combatController, targets, -amount):
                return

        elif aiDecision.action == CombatActions.RETREAT:
            targets = [targetList[i] for i in aiDecision.targetIndices]

            assert(aiDecision.actionParameter is not None)
            amount =  aiDecision.actionParameter
                
            if self.doReposition(combatController, targets, amount):
                return
            
        elif aiDecision.action == CombatActions.DEFEND:
            self.doDefend(combatController)
            return
        
        assert(False) # AI tried to do an action that failed
        self.doDefend(combatController)
        return

class CombatInterface(object):
    def __init__(self, players : dict[CombatEntity, CombatInputHandler], opponents: dict[CombatEntity, CombatInputHandler],
                 loggers : dict[CombatEntity, MessageCollector], startingPlayerHealth : dict[CombatEntity, int],
                 startingPlayerMana : dict[CombatEntity, int], startingPlayerDistances : dict[CombatEntity, int]):
        self.players : list[CombatEntity] = list(players.keys())
        self.opponents : list[CombatEntity] = list(opponents.keys())
        self.handlerMap : dict[CombatEntity, CombatInputHandler] = players.copy()
        self.handlerMap.update(opponents.copy())
        self.loggers : dict[CombatEntity, MessageCollector] = loggers

        self.activePlayer : CombatEntity | None = None
        
        self.cc : CombatController = CombatController(
            self.players, self.opponents, startingPlayerDistances.copy(), self.loggers, self.spawnEntity)
        
        for player in startingPlayerHealth:
            healthDelta = self.cc.getCurrentHealth(player) - startingPlayerHealth[player]
            self.cc.applyDamage(player, player, healthDelta, False, True)
        for player in startingPlayerMana:
            manaDelta = self.cc.getCurrentMana(player) - startingPlayerMana[player]
            self.cc.spendMana(player, manaDelta, True)

    def spawnEntity(self, entity : CombatEntity, enemyTeam : bool):
        if not enemyTeam:
            raise Exception("spawning for player team not supported yet")
        else:
            assert isinstance(entity, Enemy)
            enemyHandler = EnemyInputHandler(entity)
            self.opponents.append(entity)
            self.handlerMap[entity] = enemyHandler
        
    def sendAllLatestMessages(self):
        [logger.sendNewestMessages(None, False) for logger in self.loggers.values()]
        
    async def runCombat(self, readyFlag: asyncio.Event | None = None):
        self.sendAllLatestMessages()
        if readyFlag is not None:
            readyFlag.set()
        
        while (self.cc.checkPlayerVictory() is None):
            # self.cc.logMessage(MessageType.BASIC, "\n" + self.cc.getCombatOverviewString() + "\n")
            self.activePlayer = self.cc.advanceToNextPlayer()
            self.sendAllLatestMessages()
            if self.cc.isStunned(self.activePlayer):
                self.cc.stunSkipTurn(self.activePlayer)
            else:
                activePlayerHandler : CombatInputHandler = self.handlerMap[self.activePlayer]
                self.cc.beginPlayerTurn(self.activePlayer)
                await activePlayerHandler.takeTurn(self.cc)
            
        self.sendAllLatestMessages()
        if self.cc.checkPlayerVictory():
            self.cc.logMessage(MessageType.BASIC, f"**Your party is victorious!**\n")
            for opponent in self.cc.opponentTeam:
                if len(opponent.defeatMessage) > 0:
                    self.cc.logMessage(MessageType.DIALOGUE, opponent.defeatMessage)
        else:
            self.cc.logMessage(MessageType.BASIC, f"**Your party is defeated...**\n")
        self.sendAllLatestMessages()

    def removePlayer(self, player : Player):
        self.cc.applyDamage(player, player, self.cc.getCurrentHealth(player), False, True)
        if self.activePlayer is not None and self.activePlayer == player:
            self.handlerMap[self.activePlayer].onPlayerLeaveDungeon()

    def getPlayerTeamSummary(self, player : Player):
        teamInfoStrings = []
        for member in self.cc.playerTeam:
            overviewString = self.cc.combatStateMap[member].getStateOverviewString()
            nextActionTime = self.cc.getTimeToFullAction(member) * ACTION_TIME_DISPLAY_MULTIPLIER
            overviewString += f"\n--*To Next Action: {nextActionTime:.3f}*"
            if member == player:
                teamInfoStrings.append(f"\\*{overviewString}")
            else:
                teamInfoStrings.append(overviewString)
        return '\n'.join(teamInfoStrings)

    def getEnemyTeamSummary(self, player : Player):
        teamInfoStrings = []
        for member in self.cc.opponentTeam:
            overviewString = self.cc.combatStateMap[member].getStateOverviewString()
            distance = self.cc.checkDistance(player, member)
            if distance is not None:
                overviewString += f" (dist. {distance})"
            nextActionTime = self.cc.getTimeToFullAction(member) * ACTION_TIME_DISPLAY_MULTIPLIER
            overviewString += f"\n*--To Next Action: {nextActionTime:.3f}*"
            teamInfoStrings.append(overviewString)
        return '\n'.join(teamInfoStrings)
    
    def advancePossible(self, player : Player):
        return any([self.cc.validateReposition(player, [target], -1) for target in self.cc.getTargets(player)])
    
    def retreatPossible(self, player : Player):
        return any([self.cc.validateReposition(player, [target], 1) for target in self.cc.getTargets(player)])
    
    def validateReposition(self, player : Player, targets : list[CombatEntity], amount : int):
        return self.cc.validateReposition(player, targets, amount)
    
    def getTeammates(self, player : Player, onlyAlive : bool):
        if onlyAlive:
            return self.cc.getTeammates(player)
        else:
            return self.cc.playerTeam
    
    def getOpponents(self, player : Player, onlyAlive : bool):
        if onlyAlive:
            return self.cc.getTargets(player)
        else:
            return self.cc.opponentTeam
        
    def getSkillManaCost(self, player : Player, skillData : SkillData):
        return self.cc.getSkillManaCost(player, skillData)
    
    def isActiveToggle(self, player : Player, skillData : SkillData):
        isToggle = isinstance(skillData, ActiveToggleSkillData)
        toggleEnabled = isToggle and skillData in self.cc.combatStateMap[player].activeToggleSkills
        return toggleEnabled
        
    def canPayForSkill(self, player : Player, skillData : SkillData):
        if self.isActiveToggle(player, skillData):
            return True
        manaCost = self.cc.getSkillManaCost(player, skillData)
        if manaCost is None:
            return True
        return self.cc.getCurrentMana(player) >= manaCost
    
    def getEntityStatus(self, requester : CombatEntity, entity : CombatEntity):
        statusString =  self.cc.getFullStatusStringFor(entity)

        distance = self.cc.checkDistance(requester, entity)
        if distance is not None:
            statusString += f"\n\nDistance from {requester.name}: {distance}"
        nextActionTime = self.cc.getTimeToFullAction(entity) * ACTION_TIME_DISPLAY_MULTIPLIER
        statusString += f"\nTime To Next Action: {nextActionTime:.3f}"

        return statusString
    
    def getEntityBuffs(self, entity : CombatEntity):
        return self.cc.getBuffStatusStringFor(entity)
    
    def getRange(self, entity : CombatEntity):
        return self.cc.combatStateMap[entity].getTotalStatValue(CombatStats.RANGE)