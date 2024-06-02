import traceback
import random

from rpg_consts import *
from rpg_combat_entity import CombatEntity, Player
from rpg_classes_skills import ActiveSkillDataSelector, AttackSkillData, PlayerClassData, SkillData
from rpg_combat_state import CombatController, ActionResultInfo, AttackResultInfo
from rpg_items import * # TODO

def simpleCombatSimulation(team1 : list[Player], team2 : list[Player], starting_dist : int = 2) -> None:
    cc : CombatController = CombatController([player for player in team1], [player for player in team2], {player : starting_dist for player in team1})
    handlerMap : dict[CombatEntity, PlayerInputHandler] = {player : PlayerInputHandler(player) for player in team1 + team2}

    while (cc.checkPlayerVictory() is None):
        activePlayer : CombatEntity = cc.advanceToNextPlayer()
        activePlayerHandler : PlayerInputHandler = handlerMap[activePlayer]

        print(cc.getCombatOverviewString())
        print("---")
        print(f"{activePlayer.name}'s turn!")
        activePlayerHandler.takeTurn(cc)

    print(cc.getCombatOverviewString())
    print("---")
    if cc.checkPlayerVictory():
        print(f"Team 1 ({', '.join([player.name for player in team1])}) wins!")
    else:
        print(f"Team 2 ({', '.join([player.name for player in team2])}) wins!")

class CombatInputHandler(object):
    def __init__(self, entity : CombatEntity):
        self.entity : CombatEntity = entity

    def doAttack(self, combatController : CombatController, target : CombatEntity,
                 isPhysical : bool, attackType : AttackType | None, isBasic : bool):
        print (f"{self.entity.name} attacks {target.name}!")
        attackResult : AttackResultInfo | None = combatController.performAttack(self.entity, target, isPhysical, attackType, isBasic)
        while attackResult is not None:
            if not attackResult.inRange:
                print ("Target out of range!\n")
            elif not attackResult.attackHit:
                print ("Attack missed!\n")
            else:
                print(f"{attackResult.damageDealt} damage{' (Crit)' if attackResult.isCritical else ''}!\n")
            
            attackResult = attackResult.bonusResultInfo
            if attackResult is not None:
                print(f"{attackResult.attacker.name} performs an extra attack against {attackResult.defender.name}!")

    def doSkill(self, combatController : CombatController, targets : list[CombatEntity], skillData : SkillData) -> ActionResultInfo:
        actionResult : ActionResultInfo = combatController.performActiveSkill(self.entity, targets, skillData)
        if actionResult.success == ActionSuccessState.SUCCESS:
            if actionResult.toggleChanged:
                toggleString = "activates" if actionResult.newToggle else "deactivates"
                print (f"{self.entity.name} {toggleString} {skillData.skillName}!")
            else:
                print (f"{self.entity.name} uses {skillData.skillName}!")

            if actionResult.startAttack:
                assert(isinstance(skillData, AttackSkillData))
                assert(actionResult.attackTarget is not None)
                self.doAttack(combatController, actionResult.attackTarget, skillData.isPhysical, skillData.attackType, False)
        return actionResult
    
    def doReposition(self, combatController : CombatController, targets : list[CombatEntity], distanceChange : int) -> bool:
        changedDistances = combatController.performReposition(self.entity, targets, distanceChange)
        if len(changedDistances) == 0:
            return False
        
        for changedTarget in changedDistances:
            print (f"Distance to {changedTarget.name} is now {changedDistances[changedTarget]}.")
        return True
    
    def doDefend(self, combatController : CombatController) -> None:
        combatController.performDefend(self.entity)
        print (f"{self.entity.name} defends against the next attack!")

class PlayerInputHandler(CombatInputHandler):
    def __init__(self, player : Player):
        super().__init__(player)
        self.player : Player = player

    def takeTurn(self, combatController : CombatController):
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
                    self.doAttack(combatController, target, isPhysical, None, True)
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
                                print("Invalid parameter for this skill; check the description.")
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
                print(f"[{idx+1}] {skill.skillName} ({skill.mpCost} MP): {skill.description}")
        else:
            nextActionTime = combatController.getTimeToFullAction(target) * ACTION_TIME_DISPLAY_MULTIPLIER
            print(f"Time to next action: {nextActionTime:.3f}")
        print()

def rerollWeapon(player : Player, testRarity : int = 0):
    weaponClass = random.choice(list(filter(
        lambda wc: any([baseClass in weaponTypeAttributeMap[weaponClassAttributeMap[wc].weaponType].permittedClasses
                        for baseClass in PlayerClassData.getBaseClasses(player.currentPlayerClass)]),
        [weaponClass for weaponClass in WeaponClasses])))
    newWeapon = generateWeapon(testRarity, 10, weaponClass)
    print(newWeapon.getDescription())
    player.equipItem(newWeapon)

def rerollOtherEquips(player : Player, testRarity : int = 0):
    for drip in [generateHat(testRarity, 10), generateOverall(testRarity, 10), generateShoes(testRarity, 10)]:
        print(drip.getDescription())
        player.equipItem(drip)

if __name__ == '__main__':
    testRarity = 0

    p1 = Player("vulcan", BasePlayerClassNames.WARRIOR)
    p1.level = 3
    p1.freeStatPoints = 12
    p1.assignStatPoints([BaseStats.ATK, BaseStats.DEF, BaseStats.HP, BaseStats.SPD,
                         BaseStats.ATK, BaseStats.DEF, BaseStats.HP, BaseStats.SPD,
                         BaseStats.ATK, BaseStats.DEF, BaseStats.HP, BaseStats.SPD,])
    p1.classRanks[BasePlayerClassNames.WARRIOR] = 3
    p1.changeClass(AdvancedPlayerClassNames.MERCENARY)
    [p1.rankUp() for i in range(9-1)]
    rerollWeapon(p1, testRarity)
    rerollOtherEquips(p1, testRarity)
    print()

    p2 = Player("shubi", BasePlayerClassNames.ROGUE)
    p2.level = 3
    p2.freeStatPoints = 12
    p2.assignStatPoints([BaseStats.ATK, BaseStats.AVO, BaseStats.SPD, BaseStats.HP,
                         BaseStats.ATK, BaseStats.AVO, BaseStats.SPD, BaseStats.HP,
                         BaseStats.ATK, BaseStats.AVO, BaseStats.SPD, BaseStats.HP])
    p2.classRanks[BasePlayerClassNames.ROGUE] = 3
    rerollWeapon(p2, testRarity)
    rerollOtherEquips(p2, testRarity)
    print()

    p3 = Player("haihaya", BasePlayerClassNames.RANGER)
    p3.level = 3
    p3.freeStatPoints = 12
    p3.assignStatPoints([BaseStats.ATK, BaseStats.ACC, BaseStats.SPD, BaseStats.HP,
                         BaseStats.ATK, BaseStats.ACC, BaseStats.SPD, BaseStats.HP,
                         BaseStats.ATK, BaseStats.ACC, BaseStats.SPD, BaseStats.HP])
    p3.classRanks[BasePlayerClassNames.RANGER] = 3
    p3.changeClass(AdvancedPlayerClassNames.SNIPER)
    [p3.rankUp() for i in range(2-1)]
    rerollWeapon(p3, testRarity)
    rerollOtherEquips(p3, testRarity)
    print()

    p4 = Player("sienna", BasePlayerClassNames.MAGE)
    p4.level = 3
    p4.freeStatPoints = 12
    p4.assignStatPoints([BaseStats.MAG, BaseStats.MP, BaseStats.ACC, BaseStats.HP,
                         BaseStats.MAG, BaseStats.MP, BaseStats.ACC, BaseStats.HP,
                         BaseStats.MAG, BaseStats.MP, BaseStats.ACC, BaseStats.HP])
    p4.classRanks[BasePlayerClassNames.MAGE] = 3
    rerollWeapon(p4, testRarity)
    rerollOtherEquips(p4, testRarity)
    print()

    p5 = Player("kenelm", BasePlayerClassNames.WARRIOR)
    p5.level = 3
    p5.freeStatPoints = 12
    p5.assignStatPoints([BaseStats.ATK, BaseStats.DEF, BaseStats.HP, BaseStats.RES,
                         BaseStats.ATK, BaseStats.DEF, BaseStats.HP, BaseStats.RES,
                         BaseStats.ATK, BaseStats.DEF, BaseStats.HP, BaseStats.RES,])
    p5.classRanks[BasePlayerClassNames.WARRIOR] = 3
    p5.changeClass(AdvancedPlayerClassNames.KNIGHT)
    [p5.rankUp() for i in range(9-1)]
    rerollWeapon(p5, testRarity)
    rerollOtherEquips(p5, testRarity)
    print()

    simpleCombatSimulation([p3, p4], [p2], 2)
    # simpleCombatSimulation([p1, p2], [p3, p4], 2)

    while True:
        inp = input("> ")
        if inp == "exit":
            break
        try:
            print(eval(inp))
        except Exception:
            print(traceback.format_exc())