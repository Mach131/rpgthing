import traceback
import random

from rpg_consts import *
from rpg_combat_entity import CombatEntity, Player
from rpg_classes_skills import AttackSkillData, SkillData
from rpg_combat_state import CombatController, ActionResultInfo, AttackResultInfo
from rpg_items import * # TODO

def simpleCombatSimulation(p1 : Player, p2 : Player, starting_dist : int = 1) -> None:
    cc : CombatController = CombatController([p1], [p2])
    handlerMap : dict[CombatEntity, PlayerInputHandler] = {
        p1 : PlayerInputHandler(p1),
        p2 : PlayerInputHandler(p2)
    }
    cc.updateDistance(p1, p2, starting_dist)

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
        print(f"{p1.name} wins!")
    else:
        print(f"{p2.name} wins!")

class CombatInputHandler(object):
    def __init__(self, entity : CombatEntity):
        self.entity : CombatEntity = entity

    def doAttack(self, combatController : CombatController, target : CombatEntity, isPhysical : bool, isBasic : bool):
        print (f"{self.entity.name} attacks {target.name}!")
        attackResult : AttackResultInfo | None = combatController.performAttack(self.entity, target, isPhysical, isBasic)
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

    def doSkill(self, combatController : CombatController, target : CombatEntity, skillData : SkillData) -> ActionResultInfo:
        actionResult : ActionResultInfo = combatController.performActiveSkill(self.entity, target, skillData)
        if actionResult.success == ActionSuccessState.SUCCESS:
            print (f"{self.entity.name} uses {skillData.skillName}!")
            if actionResult.startAttack:
                assert(isinstance(skillData, AttackSkillData))
                self.doAttack(combatController, target, skillData.isPhysical, False)
        return actionResult
    
    def doReposition(self, combatController : CombatController, target : CombatEntity, distanceChange : int) -> bool:
        changedDistances = combatController.performReposition(self.entity, target, distanceChange)
        if len(changedDistances) == 0:
            return False
        
        for changedTarget in changedDistances:
            print (f"Distance to {changedTarget.name} is now {changedDistances[changedTarget]}.")
        return True

class PlayerInputHandler(CombatInputHandler):
    def __init__(self, player : Player):
        super().__init__(player)
        self.player : Player = player

    def takeTurn(self, combatController : CombatController):
        while True:
            targetList = combatController.getTargets(self.player)
            print(f"What will {self.player.name} do? (attack, skill, approach, retreat, check)")
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
                    self.doAttack(combatController, target, isPhysical, True)
                    return
                except ValueError:
                    print(f"Invalid target; use 'attack [index]'.")
                except IndexError:
                    print(f"Invalid target; use 'attack [index]' (there are currently {len(targetList)} targetable enemies).")

            elif command == "skill":
                # TODO: account for targeting differences eventually
                if len(inpSplit) < 3:
                    print("Use 'skill [skillIndex] [targetIndex]'.")
                else:
                    try:
                        skillIndex = int(inpSplit[1])
                        if skillIndex <= 0:
                            raise IndexError
                        chosenSkill = self.player.availableActiveSkills[skillIndex - 1]

                        targetIndex = int(inpSplit[2])
                        if targetIndex <= 0:
                            raise IndexError
                        target = targetList[targetIndex - 1]

                        skillResult = self.doSkill(combatController, target, chosenSkill)
                        if skillResult.success == ActionSuccessState.SUCCESS:
                            return
                        elif skillResult.success == ActionSuccessState.FAILURE_MANA:
                            print("You do not have enough MP to use this skill.")
                    except ValueError:
                        print(f"Invalid target; use 'skill [skillIndex] [targetIndex]'.")
                    except IndexError:
                        print(f"Invalid target; use 'skill [skillIndex] [targetIndex]' (there are currently {len(targetList)} targetable enemies).")

            elif command == "approach":
                if len(inpSplit) < 3:
                    print("Use 'approach [targetIndex] [amount]'.")
                else:
                    try:
                        targetIndex = int(inpSplit[1])
                        if targetIndex <= 0:
                            raise IndexError
                        target = targetList[targetIndex - 1]

                        amount = int(inpSplit[2])
                        if amount < 0 or amount > MAX_SINGLE_REPOSITION:
                            print("You may change your distance by at most 2 on your turn.")
                            
                        if self.doReposition(combatController, target, -amount):
                            return
                        else:
                            print("Unable to approach this target further.")
                    except ValueError:
                        print(f"Invalid target or amount; use 'approach [targetIndex] [amount]'.")
                    except IndexError:
                        print(f"Invalid target or amount; use 'approach [targetIndex] [amount]' (there are currently {len(targetList)} targetable enemies).")

            elif command == "retreat":
                if len(inpSplit) < 3:
                    print("Use 'retreat [targetIndex] [amount]'.")
                else:
                    try:
                        targetIndex = int(inpSplit[1])
                        if targetIndex <= 0:
                            raise IndexError
                        target = targetList[targetIndex - 1]

                        amount = int(inpSplit[2])
                        if amount < 0 or amount > MAX_SINGLE_REPOSITION:
                            print("You may change your distance by at most 2 on your turn.")
                            
                        if self.doReposition(combatController, target, amount):
                            return
                        else:
                            print("Unable to retreat from this target further.")
                    except ValueError:
                        print(f"Invalid target or amount; use 'retreat [targetIndex] [amount]'.")
                    except IndexError:
                        print(f"Invalid target or amount; use 'retreat [targetIndex] [amount]' (there are currently {len(targetList)} targetable enemies).")

            elif command == "check":
                if len(inpSplit) == 1:
                    self.doCheck(combatController, self.player)
                else:
                    # TODO: flesh out, should be able to check allies as well
                    try:
                        index = int(inpSplit[1])
                        if index <= 0:
                            raise IndexError
                        target = targetList[index - 1]

                        self.doCheck(combatController, target)
                    except ValueError:
                        print(f"Invalid target; use 'check [index]'.")
                    except IndexError:
                        print(f"Invalid target; there are currently {len(targetList)} targetable enemies.")
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
        lambda wc: player.currentPlayerClass in weaponTypeAttributeMap[weaponClassAttributeMap[wc].weaponType].permittedClasses,
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
    p1.playerLevel = 3
    p1.freeStatPoints = 12
    p1.assignStatPoints([BaseStats.ATK, BaseStats.DEF, BaseStats.HP, BaseStats.SPD,
                         BaseStats.ATK, BaseStats.DEF, BaseStats.HP, BaseStats.SPD,
                         BaseStats.ATK, BaseStats.DEF, BaseStats.HP, BaseStats.SPD,])
    p1.classRanks[BasePlayerClassNames.WARRIOR] = 3
    rerollWeapon(p1, testRarity)
    rerollOtherEquips(p1, testRarity)
    # p1._updateAvailableSkills()
    print()

    p2 = Player("shubi", BasePlayerClassNames.ROGUE)
    p2.playerLevel = 3
    p2.freeStatPoints = 12
    p2.assignStatPoints([BaseStats.ATK, BaseStats.AVO, BaseStats.SPD, BaseStats.HP,
                         BaseStats.ATK, BaseStats.AVO, BaseStats.SPD, BaseStats.HP,
                         BaseStats.ATK, BaseStats.AVO, BaseStats.SPD, BaseStats.HP])
    p2.classRanks[BasePlayerClassNames.ROGUE] = 3
    rerollWeapon(p2, testRarity)
    rerollOtherEquips(p2, testRarity)
    # p2._updateAvailableSkills()
    print()

    simpleCombatSimulation(p1, p2, 2)

    while True:
        inp = input("> ")
        if inp == "exit":
            break
        try:
            print(eval(inp))
        except Exception:
            print(traceback.format_exc())