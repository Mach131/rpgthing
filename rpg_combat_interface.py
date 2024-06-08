from __future__ import annotations
import random

from rpg_classes_skills import ActiveSkillDataSelector, AttackSkillData, SkillData
from rpg_combat_entity import CombatEntity, Player
from rpg_combat_state import ActionResultInfo, CombatController
from rpg_consts import *
from rpg_messages import MessageCollector

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

    async def takeTurn(self, combatController : CombatController) -> None:
        raise NotImplementedError()
    
class RandomEntityInputHandler(CombatInputHandler):
    def __init__(self, entity : CombatEntity):
        super().__init__(entity)

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
                    return

            elif command == "retreat":
                targets = random.sample(retreatTargets, random.choice([1, 2])) if len(retreatTargets) > 1 else retreatTargets

                amount = random.choice([1, MAX_SINGLE_REPOSITION])
                if amount < 0 or amount > MAX_SINGLE_REPOSITION:
                    print("You may change your distance by at most 2 on your turn.")
                    
                if self.doReposition(combatController, targets, amount):
                    return
                
            elif command == "defend":
                self.doDefend(combatController)
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

class CombatInterface(object):
    def __init__(self, players : dict[CombatEntity, CombatInputHandler], opponents: dict[CombatEntity, CombatInputHandler],
                 loggers : list[MessageCollector]):
        self.players : list[CombatEntity] = list(players.keys())
        self.opponents : list[CombatEntity] = list(opponents.keys())
        self.handlerMap : dict[CombatEntity, CombatInputHandler] = players.copy()
        self.handlerMap.update(opponents.copy())
        self.loggers : list[MessageCollector] = loggers
        
        self.cc : CombatController = CombatController(
            self.players, self.opponents, {player : DEFAULT_STARTING_DISTANCE for player in self.players}, self.loggers)
        
    def sendAllLatestMessages(self):
        [logger.sendNewestMessages(None, True) for logger in self.loggers]
        
    async def runCombat(self):
        self.sendAllLatestMessages()
        
        while (self.cc.checkPlayerVictory() is None):
            self.cc.logMessage(MessageType.BASIC, "\n" + self.cc.getCombatOverviewString() + "\n")
            activePlayer : CombatEntity = self.cc.advanceToNextPlayer()
            self.sendAllLatestMessages()
            if self.cc.isStunned(activePlayer):
                self.cc.stunSkipTurn(activePlayer)
            else:
                activePlayerHandler : CombatInputHandler = self.handlerMap[activePlayer]
                self.cc.beginPlayerTurn(activePlayer)
                await activePlayerHandler.takeTurn(self.cc)
            
        self.sendAllLatestMessages()
        if self.cc.checkPlayerVictory():
            self.cc.logMessage(MessageType.BASIC, f"Player team wins!")
        else:
            self.cc.logMessage(MessageType.BASIC, f"Player team loses...")
        self.sendAllLatestMessages()