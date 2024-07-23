from __future__ import annotations
from typing import Callable
import random

from gameData.rpg_item_data import *
from gameData.rpg_status_definitions import RestrictStatusEffect, StunStatusEffect
from structures.rpg_classes_skills import ActiveBuffSkillData, ActiveSkillDataSelector, ActiveToggleSkillData, AttackSkillData, CounterSkillData, EFAfterNextAttack, EFBeforeAllyAttacked, EFBeforeAttacked, EFBeforeNextAttack, EFEndTurn, EFImmediate, EFOnStatsChange, EFOnStatusApplied, EFOnToggle, EFStartTurn, EFWhenAttacked, EffectFunctionResult, SkillEffect
from rpg_consts import *
from structures.rpg_combat_entity import *
from structures.rpg_combat_state import AttackResultInfo


def waitSkill(name, timeMult):
    return SkillData(name, BasePlayerClassNames.WARRIOR, 0, True, False, "", 0, MAX_ACTION_TIMER * timeMult, False,
                         [], 0, 0, True, False)

def rollEquip(controller : CombatController, entity : CombatEntity, dropChance : float, equip : Equipment) -> Equipment | None:
    if controller._randomRoll(None, entity) < dropChance:
        return equip
    
def weaknessEffect(attribute : AttackAttribute, stacks : int) -> SkillData:
    return PassiveSkillData(f"{enumName(attribute)} Weakness x{stacks}", BasePlayerClassNames.WARRIOR, 0, False, "",
                            {}, {}, [
                                SkillEffect(f"", [EFImmediate(
                                    lambda controller, user, _1, _2: controller.addWeaknessStacks(user, attribute, stacks))], None)
                            ], False)
def resistanceEffect(attribute : AttackAttribute, stacks : int) -> SkillData:
    return PassiveSkillData(f"{enumName(attribute)} Resistance x{stacks}", BasePlayerClassNames.WARRIOR, 0, False, "",
                            {}, {}, [
                                SkillEffect(f"", [EFImmediate(
                                    lambda controller, user, _1, _2: controller.addResistanceStacks(user, attribute, stacks))], None)
                            ], False)

def getIncreaseDistanceFn(dist):
    def newFn(controller, user, target, _1, result : EffectFunctionResult):
        currentDistance = controller.checkDistance(user, target)
        if currentDistance is not None:
            reactionAttackData = controller.updateDistance(user, target, currentDistance + dist)
            [result.setBonusAttack(*reactionAttack) for reactionAttack in reactionAttackData]
    return newFn

## Training Courtyard

def basicDummy(params : dict) -> Enemy:
    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        controller.logMessage(MessageType.DIALOGUE, "The training dummy is chilling.")
        return EnemyAIAction(CombatActions.SKILL, 0, [], None, None)
    return Enemy("Basic Dummy", "Dummy",
                 "Just your average straw training dummy.", 1, {
        BaseStats.HP: 40, BaseStats.MP: 1,
        BaseStats.ATK: 1, BaseStats.DEF: 5, BaseStats.MAG: 1, BaseStats.RES: 5,
        BaseStats.ACC: 1, BaseStats.AVO: 30, BaseStats.SPD: 20
    }, {}, {}, 0, None, None, [], [waitSkill("", 1)],
    "You see a note on the training dummy...\n\"Practice the basics! Get in range of me, then Attack!\"", "",
    EnemyAI({}, decisionFn),
    lambda _1, _2: EnemyReward(1, 0, 0, None))

def skillfulDummy(params : dict) -> Enemy:
    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        controller.logMessage(MessageType.DIALOGUE, "The training dummy is chilling.")
        return EnemyAIAction(CombatActions.SKILL, 0, [], None, None)
    return Enemy("Skillful Dummy", "Dummy",
                 "A straw training dummy with a hat? How intimidating...", 1, {
        BaseStats.HP: 60, BaseStats.MP: 1,
        BaseStats.ATK: 1, BaseStats.DEF: 5, BaseStats.MAG: 1, BaseStats.RES: 5,
        BaseStats.ACC: 1, BaseStats.AVO: 30, BaseStats.SPD: 20
    }, {}, {}, 0, None, None, [], [waitSkill("", 1)],
    "You see a note on the training dummy...\n\"You've learned an Active Skill! Try it out now!\"", "",
    EnemyAI({}, decisionFn),
    lambda _1, _2: EnemyReward(1, 0, 0, None))

def trainingBoss(params : dict) -> Enemy:
    attackSkill = AttackSkillData("Storm Breaker", BasePlayerClassNames.WARRIOR, 0, False, 30, "",
                                  True, AttackType.MELEE, 5, DEFAULT_ATTACK_TIMER_USAGE, [], False)

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        playerList = controller.getTargets(enemy)
        if data["aiIdx"] == 0:
            controller.logMessage(MessageType.DIALOGUE, "Aqi: \"Don't worry, I'll go a bit easy on you~\"")
            controller.applyMultStatBonuses(enemy,
                                            {BaseStats.ATK: 50/650, BaseStats.DEF: 15/500, BaseStats.RES: 15/500,
                                             BaseStats.ACC: 50/1200, BaseStats.AVO: 60/1500, BaseStats.SPD: 30/850}
                                            )
            data["aiIdx"] = 1
            return EnemyAIAction(CombatActions.SKILL, 0, [], None, None)
        elif data["aiIdx"] == 1:
            targetIdx = None
            for pi, player in enumerate(playerList):
                if controller.checkDistanceStrict(enemy, player) == 0:
                    targetIdx = pi
                    break
            if targetIdx is None:
                targetIdx = controller.rng.randint(0, len(playerList) - 1)
                distance = controller.checkDistanceStrict(enemy, playerList[targetIdx])
                return EnemyAIAction(CombatActions.APPROACH, None, [targetIdx], min(distance, 2), None)
            else:
                mpCost = controller.getSkillManaCost(enemy, attackSkill)
                assert(mpCost is not None)
                if (controller.getCurrentMana(enemy)) >= mpCost:
                    controller.logMessage(MessageType.TELEGRAPH, f"{enemy.name} prepares a strong attack!")
                    data["target"] = targetIdx
                    data["aiIdx"] = 2
                    return EnemyAIAction(CombatActions.SKILL, 1, [], None, None)
                else:
                    return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
        else:
            targetIdx = data["target"]
            data["target"] = None
            data["aiIdx"] = 1
            if controller.checkDistanceStrict(enemy, playerList[targetIdx]) == 0:
                controller.logMessage(MessageType.DIALOGUE, "Aqi: \"Might not want to stand next to me here!\"")
            return EnemyAIAction(CombatActions.SKILL, 2, [targetIdx], None, None)
    return Enemy("Instructor Aqi", "Aqi",
                 "A roaming swordswoman who helps out new adventurers. Faintly, you sense a barely-suppressed aura radiating from her.", 1, {
        BaseStats.HP: 120, BaseStats.MP: 1000,
        BaseStats.ATK: 650, BaseStats.DEF: 500, BaseStats.MAG: 300, BaseStats.RES: 500,
        BaseStats.ACC: 1200, BaseStats.AVO: 150, BaseStats.SPD: 850
    }, {
        CombatStats.RANGE: 0
    }, {
        CombatStats.REPOSITION_ACTION_TIME_MULT: 0.5
    }, 0, None, None, [], [waitSkill("", 1), waitSkill("", 1.2), attackSkill],
    "Aqi: \"All warmed up now? Just gotta test you before seein' you off!\"",
    lambda players:
        "Aqi: \"Your form's lookin' good! Remember to check your class n' skills before tryin' the real thing!\""
            if Milestones.TUTORIAL_COMPLETE not in players[0].milestones else
        "Aqi: \"A bit easy for you now, ain't it...? Tell you what: feel free to come back any time, but I'll show you somethin' special if you get really comfy with an advanced class someday!\"",
    EnemyAI({"aiIdx": 0, "target": None}, decisionFn),
    lambda _1, _2: EnemyReward(1, 0, 0, None))

## Shared Rat Skill
ratStackBonus = 1.04
ratMarkSkill = PassiveSkillData("Ravenous Rats", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {}, [SkillEffect("", [
    EFAfterNextAttack(lambda controller, attacker, target, attackResult, _2: void((
        (
            controller.combatStateMap[target].removeStack(EffectStacks.RAT_MARK_IMPETUOUS),
            controller.combatStateMap[attacker].addStack(EffectStacks.CONSUMED_RAT_MARK_IMPETUOUS, None),
            controller.applyMultStatBonuses(attacker, {
                BaseStats.ACC: ratStackBonus,
                BaseStats.AVO: ratStackBonus
            }),
            controller.logMessage(MessageType.EFFECT, f"{attacker.name}'s ACC and AVO are increased by the mark!")
        ) if controller.combatStateMap[target].getStack(EffectStacks.RAT_MARK_IMPETUOUS) > 0 else None,
        (
            controller.combatStateMap[target].removeStack(EffectStacks.RAT_MARK_RESOLUTE),
            controller.combatStateMap[attacker].addStack(EffectStacks.CONSUMED_RAT_MARK_RESOLUTE, None),
            controller.applyMultStatBonuses(attacker, {
                BaseStats.DEF: ratStackBonus,
                BaseStats.RES: ratStackBonus
            }),
            controller.logMessage(MessageType.EFFECT, f"{attacker.name}'s DEF and RES are increased by the mark!")
        ) if controller.combatStateMap[target].getStack(EffectStacks.RAT_MARK_RESOLUTE) > 0 else None,
        (
            controller.combatStateMap[target].removeStack(EffectStacks.RAT_MARK_INTREPID),
            controller.combatStateMap[attacker].addStack(EffectStacks.CONSUMED_RAT_MARK_INTREPID, None),
            controller.applyMultStatBonuses(attacker, {
                BaseStats.ATK: ratStackBonus,
                BaseStats.SPD: ratStackBonus
            }),
            controller.logMessage(MessageType.EFFECT, f"{attacker.name}'s ATK and SPD are increased by the mark!")
        ) if controller.combatStateMap[target].getStack(EffectStacks.RAT_MARK_INTREPID) > 0 else None,
    )) if attackResult.attackHit else None)
], None)], False)

## Fresh Field

def ffSlime(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 0 }
    roomNumber = params.get('roomNumber', 0)
    if roomNumber > 0:
        maxVars = {
            BaseStats.HP: 15 if roomNumber == 1 else 40,
            BaseStats.ATK: 5,
            BaseStats.DEF: 5 if roomNumber == 1 else 10,
            BaseStats.RES: 5 if roomNumber == 1 else 10,
            BaseStats.ACC: 10,
            BaseStats.AVO: 5 if roomNumber == 1 else 20,
            BaseStats.SPD: 5 if roomNumber == 1 else 15
        }
        for stat in maxVars:
            flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        target = controller.getAggroTarget(enemy)
        targetIdx = controller.getTargets(enemy).index(target)
        if controller.checkInRange(enemy, target):
            return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
        else:
            distance = controller.checkDistanceStrict(enemy, target)
            return EnemyAIAction(CombatActions.APPROACH, None, [targetIdx], min(distance, 2), None)
    return Enemy("Slimy", "Slimy",
                 "A low-ranking slime. It's doing its best.", 2, {
        BaseStats.HP: 110, BaseStats.MP: 1,
        BaseStats.ATK: 25, BaseStats.DEF: 25, BaseStats.MAG: 1, BaseStats.RES: 25,
        BaseStats.ACC: 60, BaseStats.AVO: 60, BaseStats.SPD: 40
    }, flatStatMods, {}, 0.5, None, None, [], [],
    "The slime lets out a 'blurble'.", "",
    EnemyAI({}, decisionFn),
    lambda controller, entity:
        EnemyReward(2, 0, 0, rollEquip(controller, entity, 0.2,
                                       makeBasicCommonDrop(controller.rng, 0, 2, 0)))
        if not params.get('boss', False) else EnemyReward(1, 0, 0, None))

def ffRat(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 0 }
    roomNumber = params.get('roomNumber', 0)
    if not params.get('storehouse', False):
        if roomNumber > 0:
            maxVars = {
                BaseStats.HP: 5 if roomNumber == 1 else 20,
                BaseStats.ATK: 5 if roomNumber == 1 else 10,
                BaseStats.DEF: 5,
                BaseStats.RES: 5,
                BaseStats.ACC: 10,
                BaseStats.AVO: 5 if roomNumber == 1 else 15,
                BaseStats.SPD: 10 if roomNumber == 1 else 30
            }
            for stat in maxVars:
                flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])
    else:
        maxVarsRoomMap = {
            BaseStats.HP: [0, 30, 80],
            BaseStats.ATK: [0, 5, 20],
            BaseStats.DEF: [0, 5, 15],
            BaseStats.RES: [0, 5, 15],
            BaseStats.ACC: [0, 10, 30],
            BaseStats.AVO: [0, 5, 15, 25],
            BaseStats.SPD: [0, 5, 15]
        }
        maxVars = {
            stat: maxVarsRoomMap[stat][min(roomNumber, len(maxVarsRoomMap[stat])-1)]
            for stat in maxVarsRoomMap
        }
        for stat in maxVars:
            if maxVars[stat] > 0:
                flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])

    impetuousRatSkill = PassiveSkillData("Mark of Impetuous Rat", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {}, [SkillEffect("", [
        EFAfterNextAttack(lambda controller, _1, target, attackResult, _2: void((
            controller.logMessage(MessageType.EFFECT, f"{target.name} is marked for other rats!")
                if controller.combatStateMap[target].getStack(EffectStacks.RAT_MARK_IMPETUOUS) == 0 else None,
            controller.combatStateMap[target].addStack(EffectStacks.RAT_MARK_IMPETUOUS, 10),
            controller.combatStateMap[target].addStack(EffectStacks.RAT_MARK_IMPETUOUS, 10)
        )) if attackResult.attackHit else None)
    ], None)], False)

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        target = controller.getAggroTarget(enemy)
        targetIdx = controller.getTargets(enemy).index(target)
        if controller.checkInRange(enemy, target):
            return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
        else:
            distance = controller.checkDistanceStrict(enemy, target)
            return EnemyAIAction(CombatActions.APPROACH, None, [targetIdx], min(distance, 2), None)
        
    baseStats = {
        BaseStats.HP: 80, BaseStats.MP: 1,
        BaseStats.ATK: 20, BaseStats.DEF: 20, BaseStats.MAG: 1, BaseStats.RES: 25,
        BaseStats.ACC: 60, BaseStats.AVO: 75, BaseStats.SPD: 50
    } if not params.get('storehouse', False) else {
        BaseStats.HP: 220, BaseStats.MP: 1,
        BaseStats.ATK: 70, BaseStats.DEF: 65, BaseStats.MAG: 1, BaseStats.RES: 65,
        BaseStats.ACC: 100, BaseStats.AVO: 110, BaseStats.SPD: 85
    }
    level = 2 if not params.get('storehouse', False) else 4
    rewardExp = 2 if not params.get('storehouse', False) else 3
    minRank, maxRank, wepChance = (0, 2, 0) if not params.get('storehouse', False) else (4, 7, 0.2)
    return Enemy("Roverat", "Roverat",
                 "A field rat. Despite its size, it seeks to defy the constraints of rules.", level,
                 baseStats, flatStatMods, {}, 0.5, None, None, [ratMarkSkill, impetuousRatSkill], [],
    "\\*squeak squek\\*", "",
    EnemyAI({}, decisionFn),
    lambda controller, entity:
        EnemyReward(rewardExp, 0, 0, rollEquip(controller, entity, 0.2,
                                       makeBasicCommonDrop(controller.rng, minRank, maxRank, wepChance)))
        if not (params.get('boss', False) or params.get('summoned', False)) else EnemyReward(1, 0, 0, None))

def ffPlant(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 0 }
    roomNumber = params.get('roomNumber', 0)
    if roomNumber > 0:
        maxVars = {
            BaseStats.HP: 30 if roomNumber == 1 else 70,
            BaseStats.MP: 20 if roomNumber == 1 else 50,
            BaseStats.ATK: 5 if roomNumber == 1 else 20,
            BaseStats.MAG: 5 if roomNumber == 1 else 15,
            BaseStats.DEF: 5 if roomNumber == 1 else 10,
            BaseStats.RES: 5 if roomNumber == 1 else 15,
            BaseStats.ACC: 5 if roomNumber == 1 else 15,
            BaseStats.AVO: 5 if roomNumber == 1 else 15,
            BaseStats.SPD: 5 if roomNumber == 1 else 10
        }
        for stat in maxVars:
            flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])

    attackSkill = AttackSkillData("Petal Popper", BasePlayerClassNames.WARRIOR, 0, False, 10, "",
                                  False, AttackType.MAGIC, 1, DEFAULT_ATTACK_TIMER_USAGE, [
                                      SkillEffect("", [EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1}, {}, None, None)], 0)
                                  ], False)

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        target = controller.getAggroTarget(enemy)
        targetIdx = controller.getTargets(enemy).index(target)

        mpCost = controller.getSkillManaCost(enemy, attackSkill)
        assert(mpCost is not None)
        if (controller.getCurrentMana(enemy)) >= mpCost:
            controller.logMessage(MessageType.DIALOGUE, "*ptooo!*")
            return EnemyAIAction(CombatActions.SKILL, 0, [targetIdx], None, None)
        else:
            return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
    return Enemy("Petillery", "Petillery",
                 "A seed-slinging plant creature. Bravely holds its position to its last breath.", 3, {
        BaseStats.HP: 130, BaseStats.MP: 50,
        BaseStats.ATK: 5, BaseStats.DEF: 30, BaseStats.MAG: 40, BaseStats.RES: 35,
        BaseStats.ACC: 85, BaseStats.AVO: 30, BaseStats.SPD: 20
    }, flatStatMods, {}, 0.65, None, None, [
        weaknessEffect(MagicalAttackAttribute.FIRE, 1),
        weaknessEffect(MagicalAttackAttribute.ICE, 1),
        weaknessEffect(MagicalAttackAttribute.WIND, 1)
    ], [attackSkill],
    "", "",
    EnemyAI({}, decisionFn),
    lambda controller, entity:
        EnemyReward(3, 1 if controller._randomRoll(None, entity) <= 0.35 else 0,
                    0, rollEquip(controller, entity, 0.2,
                                       makeBasicCommonDrop(controller.rng, 1, 4, 0)))
        if not params.get('boss', False) else EnemyReward(1, 0, 0, None))


def ffSlimeBoss(params : dict) -> Enemy:
    def _slimeCannonAccMult(rangeDelta : int):
        return max(1 - ((rangeDelta ** 2) * 0.225), 0.05)
    def slimeCannonApply(controller : CombatController, attacker : CombatEntity, defender: CombatEntity, _):
        originalRange = controller.combatStateMap[defender].getStack(EffectStacks.TELEGRAPH_RANGE) - 1
        assert(originalRange >= 0)

        controller.logMessage(MessageType.EFFECT, f"The lobbed slime rains down on {defender.name}!")
        rangeDelta = abs(originalRange - controller.checkDistanceStrict(attacker, defender))
        controller.applyMultStatBonuses(attacker, {
            BaseStats.ACC: _slimeCannonAccMult(rangeDelta)
        })
        controller.combatStateMap[defender].setStack(EffectStacks.TELEGRAPH_RANGE, rangeDelta)
    def slimeCannonRevert(controller : CombatController, attacker : CombatEntity, defender : CombatEntity, _1, _2):
        rangeDelta = controller.combatStateMap[defender].getStack(EffectStacks.TELEGRAPH_RANGE)
        controller.revertMultStatBonuses(attacker, {
            BaseStats.ACC: _slimeCannonAccMult(rangeDelta)
        })
        controller.combatStateMap[defender].setStack(EffectStacks.TELEGRAPH_RANGE, 0)


    aimSkill = ActiveBuffSkillData("Glob Lob", BasePlayerClassNames.WARRIOR, 0, False, 30, "",
                                   MAX_ACTION_TIMER * 1.2, {}, {}, [
                                       SkillEffect("Slime Cannon Incoming!", [
                                           EFImmediate(lambda controller, slime, _1, _2: void((
                                               [controller.combatStateMap[target].setStack(
                                                   EffectStacks.TELEGRAPH_RANGE, controller.checkDistanceStrict(slime, target)+1)
                                                for target in controller.getTargets(slime)],
                                                controller.logMessage(MessageType.TELEGRAPH,
                                                                      "Slime is thrown high into the air in all directions!")
                                           )))
                                       ], 0)
                                   ], None, 0, True, False)
    cannonSkill = AttackSkillData("Slime Cannon!", BasePlayerClassNames.WARRIOR, 0, False, 0, "",
                                  False, AttackType.MAGIC, 1.5, 0, [
                                      SkillEffect("", [EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1}, {},
                                                                      slimeCannonApply, slimeCannonRevert)], 0)
                                  ], False)
    slamSkill = AttackSkillData("Slime Slam!", BasePlayerClassNames.WARRIOR, 0, False, 0, "",
                                  True, AttackType.MELEE, 2, 0, [], False)
    slamSkillCost = 15
    splitSkill = ActiveBuffSkillData("Slime Division!", BasePlayerClassNames.WARRIOR, 0, False, 20, "",
                                   MAX_ACTION_TIMER, {}, {}, [
                                       SkillEffect("", [
                                           EFImmediate(lambda controller, slime, _1, _2: void((
                                               controller.spawnNewEntity(ffSlime(params, controller.rng), True),
                                               controller.spawnNewEntity(ffSlime(params, controller.rng), True),
                                           )))
                                       ], 0)
                                   ], None, 0, True, False)

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        allTargets = controller.getTargets(enemy)
        currentMana = controller.getCurrentMana(enemy)

        if data["aiIdx"] == 0:
            # CD ticks
            for cdKey in ["cannonCd", "slamCd", "splitCd"]:
                data[cdKey] -= 1

            if data["cannonCd"] <= 0:
                cannonCost = controller.getSkillManaCost(enemy, aimSkill)
                assert cannonCost is not None
                if currentMana >= cannonCost:
                    data["aoeTargets"] = allTargets[:]
                    data["aiIdx"] = 1
                    return EnemyAIAction(CombatActions.SKILL, 1, [], None, None)
            if data["slamCd"] <= 0:
                proximityCheck = any([controller.checkDistanceStrict(enemy, player) == 0 for player in allTargets])
                slamCost = controller.getSkillManaCostFromValue(enemy, slamSkillCost, True)
                if proximityCheck and currentMana >= slamCost:
                    controller.logMessage(MessageType.TELEGRAPH, f"Slimoo prepares for a big leap!")
                    controller.spendMana(enemy, slamCost)
                    data["aoeTargets"] = allTargets[:]
                    data["aiIdx"] = 2
                    return EnemyAIAction(CombatActions.SKILL, 0, [], None, None)
            if data["splitCd"] <= 0:
                splitCost = controller.getSkillManaCost(enemy, splitSkill)
                assert splitCost is not None
                if len(controller.getTeammates(enemy)) < 4 and currentMana >= splitCost:
                    data["splitCd"] = 10
                    return EnemyAIAction(CombatActions.SKILL, 4, [], None, None)

            # No skills available
            defaultTarget = controller.getAggroTarget(enemy)
            targetIdx = allTargets.index(defaultTarget)
            if controller.checkInRange(enemy, defaultTarget):
                return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
            else:
                distance = controller.checkDistanceStrict(enemy, defaultTarget)
                return EnemyAIAction(CombatActions.APPROACH, None, [targetIdx], min(distance, 2), None)
                
        elif data["aiIdx"] == 1: # Slime Cannon
            aoeTargets = data["aoeTargets"]
            target = aoeTargets.pop()
            if len(aoeTargets) == 0:
                # No more targets to fire at after this one
                controller.spendActionTimer(enemy, DEFAULT_ATTACK_TIMER_USAGE)
                data["cannonCd"] = 5
                data["aiIdx"] = 0
            return EnemyAIAction(CombatActions.SKILL, 2, [allTargets.index(target)], None, None)
        if data["aiIdx"] == 2: # Slime Slam
            aoeTargets = data["aoeTargets"]
            target = aoeTargets.pop()
            if len(aoeTargets) == 0:
                # No more targets to fire at after this one
                controller.spendActionTimer(enemy, DEFAULT_ATTACK_TIMER_USAGE)
                data["slamCd"] = 3
                data["aiIdx"] = 0
            return EnemyAIAction(CombatActions.SKILL, 3, [allTargets.index(target)], None, None)
        
        controller.logMessage(MessageType.DEBUG, "<slimoo ai error, should be unreachable>")
        data["aiIdx"] = 0
        return EnemyAIAction(CombatActions.DEFEND, None, [], None, None)
    return Enemy("Slimoo", "Slimoo",
                 "A mid-ranking slime. Its work is paying off.", 4, {
        BaseStats.HP: 400, BaseStats.MP: 150,
        BaseStats.ATK: 70, BaseStats.DEF: 50, BaseStats.MAG: 80, BaseStats.RES: 70,
        BaseStats.ACC: 90, BaseStats.AVO: 60, BaseStats.SPD: 50
    }, {
        CombatStats.RANGE: 0
    }, {
        CombatStats.BASIC_MP_GAIN_MULT: 10 / BASIC_ATTACK_MP_GAIN
    }, 0.5, None, None, [], [waitSkill("", 0.4), aimSkill, cannonSkill, slamSkill, splitSkill],
    "The large slime roars a noble 'blurble'!", "",
    EnemyAI({"aiIdx": 0, "cannonCd": 0, "slamCd": 2, "splitCd": 2}, decisionFn),
    lambda controller, entity:
        EnemyReward(10, 4, 0, rollEquip(controller, entity, 1,
                                       makeBasicUncommonDrop(controller.rng, 0, 1, 0.5)
                                            if controller._randomRoll(None, entity) <= 0.1 else
                                       makeBasicCommonDrop(controller.rng, 5, 8, 0.5))))


def ffPlantBoss(params : dict) -> Enemy:
    def thrashKnockbackFn(controller : CombatController, user : CombatEntity, target : CombatEntity,
                          attackResult : AttackResultInfo, result : EffectFunctionResult):
        if not attackResult.attackHit:
            return
        currentDistance = controller.checkDistance(user, target)
        if currentDistance is not None:
            reactionAttackData = controller.updateDistance(user, target, currentDistance + 2)
            [result.setBonusAttack(*reactionAttack) for reactionAttack in reactionAttackData]
    vengeanceSkill = PassiveSkillData("Aromatic Avenger", BasePlayerClassNames.WARRIOR, 0, False, "",
                                      {}, {}, [
                                          SkillEffect("", [
                                              EFBeforeNextAttack({}, {},
                                                  lambda controller, attacker, _1, _2: controller.applyMultStatBonuses(
                                                      attacker, { BaseStats.MAG: 1.25 }
                                                  ) if len(controller.getTeammates(attacker)) == 0 else None,
                                                  lambda controller, attacker, _1, _2, _3: controller.revertMultStatBonuses(
                                                      attacker, { BaseStats.MAG: 1.25 }
                                                  ) if len(controller.getTeammates(attacker)) == 0 else None)
                                          ], None)
                                      ], False)
    shootSkill = AttackSkillData("Blossom Blaster", BasePlayerClassNames.WARRIOR, 0, False, 15, "",
                                  False, AttackType.MAGIC, 1, MAX_ACTION_TIMER, [
                                      SkillEffect("", [EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1}, {}, None, None)], 0)
                                  ], False)
    healSkill = ActiveBuffSkillData("Gardening", BasePlayerClassNames.WARRIOR, 0, False, 30, "",
                                     DEFAULT_ATTACK_TIMER_USAGE * 0.75, {}, {}, [
                                         SkillEffect("", [EFImmediate(
                                             lambda controller, enemy, targets, _: void((
                                                 controller.applyDamage(enemy, enemy, min(50, controller.getCurrentHealth(enemy))),
                                                 [controller.doHealSkill(enemy, target, 0.5) for target in targets],
                                                 [controller.gainMana(target, 30) for target in targets]
                                         )))], 0)
                                     ], None, 0, False, False)
    swingSkill = AttackSkillData("Thorny Thrash", BasePlayerClassNames.WARRIOR, 0, False, 30, "",
                                  True, AttackType.MELEE, 1, DEFAULT_ATTACK_TIMER_USAGE, [
                                      SkillEffect("", [EFAfterNextAttack(thrashKnockbackFn)], 0)
                                  ], False)
    
    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        allTargets = controller.getTargets(enemy)
        # defaultTarget = controller.getAggroTarget(enemy)
        currentMana = controller.getCurrentMana(enemy)

        # CD ticks
        for cdKey in ["gardenCd", "swingCd"]:
            data[cdKey] -= 1

        if data["gardenCd"] <= 0:
            teammates = controller.getTeammates(enemy)
            healNeeded = False
            for teammate in teammates:
                if teammate == enemy:
                    continue
                hpRatio = controller.getCurrentHealth(teammate) / controller.getMaxHealth(teammate)
                mpRatio = controller.getCurrentMana(teammate) / controller.getMaxMana(teammate)
                if hpRatio <= 0.35 or mpRatio <= 0.2:
                    healNeeded = True
                    break
            gardenCost = controller.getSkillManaCost(enemy, healSkill)
            assert gardenCost is not None
            if healNeeded and currentMana >= gardenCost:
                allAllyIndices = []
                for i in range(len(teammates)):
                    if teammates[i] != enemy:
                        allAllyIndices.append(i)
                data["gardenCd"] = 3
                return EnemyAIAction(CombatActions.SKILL, 1, allAllyIndices, None, None)
            
        defaultTarget = controller.getAggroTarget(enemy)
        targetIdx = allTargets.index(defaultTarget)
        if data["swingCd"] <= 0:
            swingCost = controller.getSkillManaCost(enemy, swingSkill)
            assert swingCost is not None
            if controller.checkInRange(enemy, defaultTarget) and currentMana >= swingCost:
                data["swingCd"] = 3
                return EnemyAIAction(CombatActions.SKILL, 2, [targetIdx], None, None)
        
        # No cd skills available
        shootMpCost = controller.getSkillManaCost(enemy, shootSkill)
        assert(shootMpCost is not None)
        if currentMana >= shootMpCost:
            controller.logMessage(MessageType.DIALOGUE, "*ba-toom!*")
            return EnemyAIAction(CombatActions.SKILL, 0, [targetIdx], None, None)
        else:
            return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
    return Enemy("Fleuricier", "Fleuricier",
                 "A decorated plant creature. The sort to sit around while others are fighting.", 4, {
        BaseStats.HP: 500, BaseStats.MP: 200,
        BaseStats.ATK: 40, BaseStats.DEF: 60, BaseStats.MAG: 100, BaseStats.RES: 85,
        BaseStats.ACC: 140, BaseStats.AVO: 30, BaseStats.SPD: 30
    }, {
        CombatStats.RANGE: 1
    }, {
        CombatStats.BASIC_MP_GAIN_MULT: 20 / BASIC_ATTACK_MP_GAIN
    }, 0.5, None, None, [
        vengeanceSkill,
        weaknessEffect(MagicalAttackAttribute.FIRE, 1),
        weaknessEffect(MagicalAttackAttribute.ICE, 1),
        weaknessEffect(MagicalAttackAttribute.WIND, 1)
    ], [shootSkill, healSkill, swingSkill],
    "The flower unit prepares to mobilize!", "",
    EnemyAI({"aiIdx": 0, "gardenCd": 2, "swingCd": 0}, decisionFn),
    lambda controller, entity:
        EnemyReward(10, 4, 0, rollEquip(controller, entity, 1,
                                       makeBasicUncommonDrop(controller.rng, 0, 1, 0.5)
                                            if controller._randomRoll(None, entity) <= 0.1 else
                                       makeBasicCommonDrop(controller.rng, 6, 8, 0.5))))

## Skylight Cave

def scRat(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 0 }
    roomNumber = params.get('roomNumber', 0)
    if not params.get('storehouse', False):
        if roomNumber > 0:
            maxVars = {
                BaseStats.HP: 10 if roomNumber == 1 else 30,
                BaseStats.ATK: 5 if roomNumber == 1 else 10,
                BaseStats.DEF: 5 if roomNumber == 1 else 10,
                BaseStats.RES: 5 if roomNumber == 1 else 10,
                BaseStats.ACC: 10,
                BaseStats.AVO: 5 if roomNumber == 1 else 10,
                BaseStats.SPD: 10 if roomNumber == 1 else 20
            }
            for stat in maxVars:
                flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])
    else:
        maxVarsRoomMap = {
            BaseStats.HP: [0, 30, 80],
            BaseStats.ATK: [0, 5, 20],
            BaseStats.DEF: [0, 5, 15],
            BaseStats.RES: [0, 5, 15],
            BaseStats.ACC: [0, 10, 30],
            BaseStats.AVO: [0, 5, 15, 25],
            BaseStats.SPD: [0, 5, 15]
        }
        maxVars = {
            stat: maxVarsRoomMap[stat][min(roomNumber, len(maxVarsRoomMap[stat])-1)]
            for stat in maxVarsRoomMap
        }
        for stat in maxVars:
            if maxVars[stat] > 0:
                flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])

    resoluteRatSkill = PassiveSkillData("Mark of Resolute Rat", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {}, [SkillEffect("", [
        EFAfterNextAttack(lambda controller, _1, target, attackResult, _2: void((
            controller.logMessage(MessageType.EFFECT, f"{target.name} is marked for other rats!")
                if controller.combatStateMap[target].getStack(EffectStacks.RAT_MARK_RESOLUTE) == 0 else None,
            controller.combatStateMap[target].addStack(EffectStacks.RAT_MARK_RESOLUTE, 10),
            controller.combatStateMap[target].addStack(EffectStacks.RAT_MARK_RESOLUTE, 10)
        )) if attackResult.attackHit else None)
    ], None)], False)

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        target = controller.getAggroTarget(enemy)
        targetIdx = controller.getTargets(enemy).index(target)
        if controller.checkInRange(enemy, target):
            return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
        else:
            distance = controller.checkDistanceStrict(enemy, target)
            return EnemyAIAction(CombatActions.APPROACH, None, [targetIdx], min(distance, 2), None)
        
    baseStats = {
        BaseStats.HP: 140, BaseStats.MP: 1,
        BaseStats.ATK: 40, BaseStats.DEF: 30, BaseStats.MAG: 1, BaseStats.RES: 35,
        BaseStats.ACC: 80, BaseStats.AVO: 90, BaseStats.SPD: 75
    } if not params.get('storehouse', False) else {
        BaseStats.HP: 220, BaseStats.MP: 1,
        BaseStats.ATK: 70, BaseStats.DEF: 65, BaseStats.MAG: 1, BaseStats.RES: 65,
        BaseStats.ACC: 100, BaseStats.AVO: 110, BaseStats.SPD: 85
    }
    level = 3 if not params.get('storehouse', False) else 4
    minRank, maxRank, wepChance = (2, 5, 0) if not params.get('storehouse', False) else (4, 7, 0.2)
    return Enemy("Spelunkerat", "Spelunkerat",
                 "A cave rat. It lives for treasure, both the friendship sort and the actual-monetary-value kind.", level,
                 baseStats, flatStatMods, {}, 0.5,None, None, [ratMarkSkill, resoluteRatSkill], [],
    "\\*squeak squok\\*", "",
    EnemyAI({}, decisionFn),
    lambda controller, entity:
        EnemyReward(3, 0, 0, rollEquip(controller, entity, 0.2,
                                       makeBasicCommonDrop(controller.rng, minRank, maxRank, wepChance)))
        if not (params.get('boss', False) or params.get('summoned', False)) else EnemyReward(1, 0, 0, None))

def scRock(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 0 }
    roomNumber = params.get('roomNumber', 0)
    if roomNumber > 0:
        maxVars = {
            BaseStats.HP: 35 if roomNumber == 1 else 100,
            BaseStats.ATK: 5 if roomNumber == 1 else 20,
            BaseStats.DEF: 10 if roomNumber == 1 else 30,
            BaseStats.RES: 15 if roomNumber == 1 else 40,
            BaseStats.ACC: 10,
            BaseStats.AVO: 5 if roomNumber == 1 else 10,
            BaseStats.SPD: 5 if roomNumber == 1 else 10
        }
        for stat in maxVars:
            flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])
    if params.get('boss', False):
        flatStatMods[BaseStats.HP] += 30

    enrageAtStacks = 6
    rageSkill = PassiveSkillData("Rueful Rocks", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {}, [
        SkillEffect("", [
            EFWhenAttacked(lambda controller, user, _1, attackResult, _2:
                           controller.combatStateMap[user].removeStack(EffectStacks.ENEMY_COUNTER_A) if attackResult.attackHit else None),
            EFEndTurn(lambda controller, user, _1, _2: void((
                controller.combatStateMap[user].addStack(EffectStacks.ENEMY_COUNTER_A, 10),
                controller.combatStateMap[user].addStack(EffectStacks.ENEMY_COUNTER_A, 10),
                controller.logMessage(MessageType.TELEGRAPH, f"Stalactun seems very upset!")
                    if controller.combatStateMap[user].getStack(EffectStacks.ENEMY_COUNTER_A) in (enrageAtStacks, enrageAtStacks+1) else None
            )) if controller.combatStateMap[user].getStack(EffectStacks.ENEMY_COUNTER_A) < 10 else None )
        ], None, None)
    ], False)

    rockSkill = AttackSkillData("Rocks Fall", BasePlayerClassNames.WARRIOR, 0, False, 0, "",
                                  True, AttackType.MELEE, 1.5, 0, [
                                      SkillEffect("", [
                                          EFBeforeNextAttack({
                                              CombatStats.RANGE: 1
                                          }, {}, None, None)
                                      ], 0, None)
                                  ], False)

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        allTargets = controller.getTargets(enemy)
        rageStacks = controller.combatStateMap[enemy].getStack(EffectStacks.ENEMY_COUNTER_A)
        isEnraged = rageStacks >= enrageAtStacks
        rockSkillCost = controller.getSkillManaCost(enemy, rockSkill)
        assert rockSkillCost is not None
        canUseSkill = isEnraged and controller.getCurrentMana(enemy) >= rockSkillCost
        targetRange = 1 if canUseSkill else 0

        target = controller.getAggroTarget(enemy)
        targetIdx = controller.getTargets(enemy).index(target)
        if controller.checkDistanceStrict(enemy, target) <= targetRange:
            if canUseSkill:
                if len(data["aoeTargets"]) == 0:
                    data["aoeTargets"] = allTargets[:]
                    controller.spendMana(enemy, rockSkillCost)

                aoeTargets = data["aoeTargets"]
                target = aoeTargets.pop()
                if len(aoeTargets) == 0:
                    controller.spendActionTimer(enemy, DEFAULT_ATTACK_TIMER_USAGE)
                    controller.combatStateMap[enemy].setStack(EffectStacks.ENEMY_COUNTER_A, rageStacks - enrageAtStacks)
                return EnemyAIAction(CombatActions.SKILL, 0, [allTargets.index(target)], None, None)
            else:
                return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
        else:
            distance = controller.checkDistanceStrict(enemy, target)
            return EnemyAIAction(CombatActions.APPROACH, None, [targetIdx], min(distance, 2), None)
        
    return Enemy("Stalactun", "Stalactun",
                 "A rocky creature. Easy to forget about, but seems to hate being ignored.", 3, {
        BaseStats.HP: 180, BaseStats.MP: 30,
        BaseStats.ATK: 50, BaseStats.DEF: 65, BaseStats.MAG: 1, BaseStats.RES: 35,
        BaseStats.ACC: 85, BaseStats.AVO: 50, BaseStats.SPD: 40
    }, flatStatMods, {}, 0.6, AttackType.MELEE, PhysicalAttackAttribute.CRUSHING, [
        weaknessEffect(PhysicalAttackAttribute.CRUSHING, 1),
        resistanceEffect(PhysicalAttackAttribute.PIERCING, 1),
        rageSkill
    ], [rockSkill],
    "", "",
    EnemyAI({"aoeTargets": []}, decisionFn),
    lambda controller, entity:
        EnemyReward(3, 1 if controller._randomRoll(None, entity) <= 0.35 else 0,
                    0, rollEquip(controller, entity, 0.2,
                                       makeBasicCommonDrop(controller.rng, 3, 6, 0.25, getWeaponClasses(MELEE_WEAPON_TYPES))))
        if not params.get('boss', False) else EnemyReward(1, 0, 0, None))

def scBat(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 0 }
    roomNumber = params.get('roomNumber', 0)
    if roomNumber > 0:
        maxVars = {
            BaseStats.HP: 20 if roomNumber == 1 else 50,
            BaseStats.ATK: 5 if roomNumber == 1 else 20,
            BaseStats.DEF: 5 if roomNumber == 1 else 15,
            BaseStats.RES: 5 if roomNumber == 1 else 15,
            BaseStats.ACC: 10 if roomNumber == 1 else 15,
            BaseStats.AVO: 10 if roomNumber == 1 else 20,
            BaseStats.SPD: 10 if roomNumber == 1 else 20
        }
        for stat in maxVars:
            flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])
    if params.get('boss', False):
        flatStatMods[BaseStats.HP] += 75

    dashSkill = AttackSkillData("Soaring Shadow", BasePlayerClassNames.WARRIOR, 0, False, 15, "",
                                  True, AttackType.MELEE, 2, DEFAULT_ATTACK_TIMER_USAGE, [
                                      SkillEffect("", [
                                          EFImmediate(
                                              lambda controller, enemy, targets, _: void(controller.updateDistance(enemy, targets[0], 0))
                                          )
                                      ], 0, None)
                                  ], False)

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        isFleeing = controller.getCurrentHealth(enemy) / controller.getMaxHealth(enemy) <= 0.5
        if isFleeing and not data["fleeState"]:
            controller.logMessage(MessageType.DIALOGUE, f"Byebat shrieks in fear!")
            data["fleeState"] = True

        dashSkillCost = controller.getSkillManaCost(enemy, dashSkill)
        assert dashSkillCost is not None
        canAffordSkill = controller.getCurrentMana(enemy) >= dashSkillCost

        target = controller.getAggroTarget(enemy)
        targetIdx = controller.getTargets(enemy).index(target)
    
        if isFleeing:
            if canAffordSkill:
                if controller.checkDistanceStrict(enemy, target) >= 2:
                    data["consecutiveRetreats"] = 0
                    return EnemyAIAction(CombatActions.SKILL, 0, [targetIdx], None, None)
                elif data["consecutiveRetreats"] >= 3:
                    data["consecutiveRetreats"] = 0
                    controller.increaseActionTimer(enemy, 0.85)
                    return EnemyAIAction(CombatActions.SKILL, 0, [targetIdx], None, None)
                else:
                    data["consecutiveRetreats"] += 1
                    return EnemyAIAction(CombatActions.RETREAT, None, [targetIdx], 2, None)
            else:
                data["consecutiveRetreats"] = 0
                return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
            
        else:
            if controller.checkInRange(enemy, target):
                return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
            else:
                distance = controller.checkDistanceStrict(enemy, target)
                return EnemyAIAction(CombatActions.APPROACH, None, [targetIdx], min(distance, 2), None)
        
    return Enemy("Byebat", "Byebat",
                 "A bat with sharp claws. Easily frightened, but it'll get over it eventually.", 3, {
        BaseStats.HP: 150, BaseStats.MP: 45,
        BaseStats.ATK: 40, BaseStats.DEF: 40, BaseStats.MAG: 1, BaseStats.RES: 40,
        BaseStats.ACC: 100, BaseStats.AVO: 100, BaseStats.SPD: 75
    }, flatStatMods, {
        CombatStats.BASIC_MP_GAIN_MULT: 10 / BASIC_ATTACK_MP_GAIN
    }, 0.4, AttackType.MELEE, PhysicalAttackAttribute.SLASHING, [
        weaknessEffect(PhysicalAttackAttribute.SLASHING, 1),
        resistanceEffect(PhysicalAttackAttribute.CRUSHING, 1),
    ], [dashSkill],
    "The bat is awoken from its slumber!", "",
    EnemyAI({"fleeState": False, "consecutiveRetreats": 0}, decisionFn),
    lambda controller, entity:
        EnemyReward(3, 1 if controller._randomRoll(None, entity) <= 0.35 else 0,
                    0, rollEquip(controller, entity, 0.2,
                                       makeBasicCommonDrop(controller.rng, 3, 6, 0.25, getWeaponClasses(MELEE_WEAPON_TYPES))))
        if not params.get('boss', False) else EnemyReward(1, 0, 0, None))


def scFairy(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 2 }
    roomNumber = params.get('roomNumber', 0)
    if roomNumber > 0:
        maxVars = {
            BaseStats.HP: 10 if roomNumber == 1 else 30,
            BaseStats.ATK: 5 if roomNumber == 1 else 15,
            BaseStats.DEF: 5 if roomNumber == 1 else 15,
            BaseStats.RES: 5 if roomNumber == 1 else 15,
            BaseStats.ACC: 10,
            BaseStats.AVO: 10 if roomNumber == 1 else 20,
            BaseStats.SPD: 5 if roomNumber == 1 else 15
        }
        for stat in maxVars:
            flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])
    if params.get('boss', False):
        flatStatMods[BaseStats.HP] += 75
    
    strafeSkill = AttackSkillData("Crystal Reflection", BasePlayerClassNames.WARRIOR, 0, False, 15, "",
        True, AttackType.RANGED, 0.8, DEFAULT_ATTACK_TIMER_USAGE * 1.2,
        [SkillEffect("", [EFAfterNextAttack(getIncreaseDistanceFn(2))], 0)], False)
    buffSkill = ActiveBuffSkillData("Crystal Refraction", BasePlayerClassNames.WARRIOR, 0, False, 15, "",
                                     DEFAULT_ATTACK_TIMER_USAGE * 0.75, {}, {}, [
                                         SkillEffect("", [EFImmediate(
                                             lambda controller, enemy, targets, _: void((
                                                 controller.logMessage(MessageType.EFFECT,
                                                                       "The light of Deposylph shines on its allies, increasing ATK, DEF, and RES!"),
                                                 [controller.applyMultStatBonuses(target, {
                                                     BaseStats.ATK: 1.1,
                                                     BaseStats.DEF: 1.1,
                                                     BaseStats.RES: 1.1
                                                 }) for target in targets]
                                         )))], 0)
                                     ], None, 0, False, False)
    unhitTracker = PassiveSkillData("Sylph Schemes", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {}, [
        SkillEffect("", [
            EFWhenAttacked(lambda controller, user, _1, attackResult, _2:
                           controller.combatStateMap[user].setStack(EffectStacks.ENEMY_COUNTER_A, 0) if attackResult.attackHit else None),
            EFEndTurn(lambda controller, user, _1, _2: void(
                controller.combatStateMap[user].addStack(EffectStacks.ENEMY_COUNTER_A, 1)
            ))
        ], None, None)
    ], False)

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        currentMana = controller.getCurrentMana(enemy)

        strafeSkillCost = controller.getSkillManaCost(enemy, strafeSkill)
        assert strafeSkillCost is not None
        buffSkillCost = controller.getSkillManaCost(enemy, buffSkill)
        assert buffSkillCost is not None

        target = controller.getAggroTarget(enemy)
        targetIdx = controller.getTargets(enemy).index(target)

        unhitCounters = controller.combatStateMap[enemy].getStack(EffectStacks.ENEMY_COUNTER_A)

        if controller.checkDistanceStrict(enemy, target) == 0 and currentMana >= strafeSkillCost:
            return EnemyAIAction(CombatActions.SKILL, 0, [targetIdx], None, None)
        else:
            if unhitCounters >= 1 and currentMana >= buffSkillCost:
                controller.combatStateMap[enemy].setStack(EffectStacks.ENEMY_COUNTER_A, -1)
                enemyAllies = controller.getTeammates(enemy)
                return EnemyAIAction(CombatActions.SKILL, 1, [i for i in range(len(enemyAllies))], None, None)
            elif controller.checkDistanceStrict(enemy, target) < 2 and currentMana >= strafeSkillCost:
                return EnemyAIAction(CombatActions.SKILL, 0, [targetIdx], None, None)
            elif controller.checkInRange(enemy, target):
                return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
            else:
                distance = controller.checkDistanceStrict(enemy, target)
                return EnemyAIAction(CombatActions.APPROACH, None, [targetIdx], min(distance, 1), None)
    return Enemy("Deposylph", "Deposylph",
                 "A spirit seemingly formed of crystal. Other creatures are drawn to its lustre, feeding its ego.", 3, {
        BaseStats.HP: 130, BaseStats.MP: 60,
        BaseStats.ATK: 60, BaseStats.DEF: 30, BaseStats.MAG: 1, BaseStats.RES: 60,
        BaseStats.ACC: 130, BaseStats.AVO: 50, BaseStats.SPD: 60
    }, flatStatMods, {
        CombatStats.BASIC_MP_GAIN_MULT: 8 / BASIC_ATTACK_MP_GAIN
    }, 0.4, AttackType.RANGED, PhysicalAttackAttribute.PIERCING, [
        weaknessEffect(PhysicalAttackAttribute.PIERCING, 1),
        resistanceEffect(PhysicalAttackAttribute.SLASHING, 1),
        unhitTracker
    ], [strafeSkill, buffSkill],
    "", "",
    EnemyAI({}, decisionFn),
    lambda controller, entity:
        EnemyReward(3, 1 if controller._randomRoll(None, entity) <= 0.35 else 0,
                    0, rollEquip(controller, entity, 0.2,
                                       makeBasicCommonDrop(controller.rng, 3, 6, 0.25, getWeaponClasses(MELEE_WEAPON_TYPES))))
        if not params.get('boss', False) else EnemyReward(1, 0, 0, None))


def scRpsBoss(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    rpsBeatsMap = {
        PhysicalAttackAttribute.CRUSHING: PhysicalAttackAttribute.PIERCING,
        PhysicalAttackAttribute.SLASHING: PhysicalAttackAttribute.CRUSHING,
        PhysicalAttackAttribute.PIERCING: PhysicalAttackAttribute.SLASHING
    }
    rpsLosesMap = {
        PhysicalAttackAttribute.CRUSHING: PhysicalAttackAttribute.SLASHING,
        PhysicalAttackAttribute.SLASHING: PhysicalAttackAttribute.PIERCING,
        PhysicalAttackAttribute.PIERCING: PhysicalAttackAttribute.CRUSHING
    }

    resistanceShifter = PassiveSkillData("Reactive Protection System", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {}, [
        SkillEffect("", [
            EFWhenAttacked(lambda controller, user, _1, attackResult, _2: void((
                controller.addResistanceStacks(user, attackResult.attackAttribute, 2),
                controller.addWeaknessStacks(user, rpsBeatsMap[attackResult.attackAttribute], 1)
             )) if attackResult.attackHit and isinstance(attackResult.attackAttribute, PhysicalAttackAttribute) else None)
        ], None, None)
    ], False)

    burstStackRequirement = 5
    rpsNameMap = {
        "CRUSHING": "Type P",
        "SLASHING": "Type S",
        "PIERCING": "Type R"
    }
    rpsEffectStrings = {
        PhysicalAttackAttribute.CRUSHING: "The Golem's rocky limbs grow weightier!",
        PhysicalAttackAttribute.SLASHING: "The Golem's flat appendages are compressed!",
        PhysicalAttackAttribute.PIERCING: "The Golem's pointed protusions are sharpened!"
    }
    burstAttack = ActiveSkillDataSelector("Adaptation Protocol", BasePlayerClassNames.WARRIOR, 0, False, 10, "", "", DEFAULT_ATTACK_TIMER_USAGE,
                            1, True, lambda attribute: AttackSkillData(
                                f"Adaptation Protocol: {rpsNameMap[attribute]}", BasePlayerClassNames.WARRIOR, 0, False, 10, "",
                                True, AttackType.MELEE, 1.75, DEFAULT_ATTACK_TIMER_USAGE, [
                                    SkillEffect("", [
                                        EFImmediate(lambda controller, user, _1, _2: void((
                                            controller.removeResistanceStacks(
                                                user, PhysicalAttackAttribute[attribute],
                                                min(controller.combatStateMap[user].resistances.count(PhysicalAttackAttribute[attribute]),
                                                    burstStackRequirement)),
                                            controller.addWeaknessStacks(user, PhysicalAttackAttribute[attribute], 2),
                                            controller.combatStateMap[user].addStack(EffectStacks.RPS_LEVEL, None)
                                          )))
                                      ], 0, None)
                                  ], False),
                            [attribute.name for attribute in PhysicalAttackAttribute], False)
    
    aoeAttackCost = 20
    aoeAttack = AttackSkillData("Factory Reset", BasePlayerClassNames.WARRIOR, 0, False, 0, "",
                                  True, AttackType.MELEE, 1, 0, [
                                      SkillEffect("", [
                                          EFBeforeNextAttack(
                                              {CombatStats.IGNORE_RANGE_CHECK: 1}, {},
                                              lambda controller, user, _1, _2: controller.applyMultStatBonuses(
                                                  user, {
                                                      BaseStats.ATK: 0.8 + (controller.combatStateMap[user].getStack(EffectStacks.RPS_LEVEL) * 0.7)
                                                  }),
                                              lambda controller, user, _1, _2, _3: controller.revertMultStatBonuses(
                                                  user, {
                                                      BaseStats.ATK: 0.8 + (controller.combatStateMap[user].getStack(EffectStacks.RPS_LEVEL) * 0.7)
                                                  }))
                                      ], 0, None)
                                  ], False)


    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        allTargets = controller.getTargets(enemy)
        currentMana = controller.getCurrentMana(enemy)
        resistStacks = {
            attribute: controller.combatStateMap[enemy].resistances.count(attribute) - controller.combatStateMap[enemy].weaknesses.count(attribute)
            for attribute in PhysicalAttackAttribute
        }
        controller.logMessage(MessageType.DEBUG, str(resistStacks))

        if data["aoeReset"]:
            controller.combatStateMap[enemy].setStack(EffectStacks.RPS_LEVEL, 0)
            for attribute in PhysicalAttackAttribute:
                controller.removeWeaknessStacks(enemy, attribute, controller.combatStateMap[enemy].weaknesses.count(attribute))
                controller.removeResistanceStacks(enemy, attribute, controller.combatStateMap[enemy].resistances.count(attribute))
                controller.addWeaknessStacks(enemy, attribute, 1)
            controller.logMessage(MessageType.EFFECT,
                                "The golem returns to its original shape!")
            data["aoeReset"] = False
            return EnemyAIAction(CombatActions.SKILL, 3, [], None, None)

        if data["aiIdx"] == 0:
            # CD ticks
            for cdKey in ["aoeCd"]:
                data[cdKey] -= 1

            if data["aoeCd"] <= 0:
                aoeCost = controller.getSkillManaCostFromValue(enemy, aoeAttackCost, True)
                if currentMana >= aoeCost:
                    controller.logMessage(MessageType.TELEGRAPH, f"The Ropasci Golem's body glows with an ominous light!")
                    controller.spendMana(enemy, aoeCost)
                    data["aoeTargets"] = allTargets[:]
                    data["aiIdx"] = 1
                    return EnemyAIAction(CombatActions.SKILL, 0, [], None, None)
                
            defaultTarget = controller.getAggroTarget(enemy)
            targetIdx = allTargets.index(defaultTarget)

            if controller.checkInRange(enemy, defaultTarget):
                burstCost = controller.getSkillManaCost(enemy, burstAttack)
                assert burstCost is not None
                if currentMana >= burstCost:
                    attributeOrder = [attribute for attribute in PhysicalAttackAttribute]
                    rng.shuffle(attributeOrder)
                    for attribute in attributeOrder:
                        if resistStacks[attribute] >= burstStackRequirement:
                            counterAttribute = rpsLosesMap[attribute]
                            enemy.basicAttackAttribute = counterAttribute
                            controller.logMessage(MessageType.EFFECT, rpsEffectStrings[counterAttribute])
                            return EnemyAIAction(CombatActions.SKILL, 1, [targetIdx], None, attribute.name)

                # No skills available
                if controller.checkInRange(enemy, defaultTarget):
                    return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
            else:
                distance = controller.checkDistanceStrict(enemy, defaultTarget) - 1
                return EnemyAIAction(CombatActions.APPROACH, None, [targetIdx], min(distance, 2), None)
                
        elif data["aiIdx"] == 1: # Factory Reset
            aoeTargets = data["aoeTargets"]
            target = aoeTargets.pop()
            if len(aoeTargets) == 0:
                # No more targets to fire at after this one
                data["aoeCd"] = 8
                data["aiIdx"] = 0
                data["aoeReset"] = True
            return EnemyAIAction(CombatActions.SKILL, 2, [allTargets.index(target)], None, None)
        
        controller.logMessage(MessageType.DEBUG, "<golem ai error, should be unreachable>")
        data["aiIdx"] = 0
        return EnemyAIAction(CombatActions.DEFEND, None, [], None, None)
    return Enemy("Ropasci Golem", "Golem",
                 "A giant artificial being. Though its body is largely made of rock, it has flat appendages and sharp protrusions hinting at the purpose for its creation.", 5, {
        BaseStats.HP: 850, BaseStats.MP: 100,
        BaseStats.ATK: 80, BaseStats.DEF: 80, BaseStats.MAG: 1, BaseStats.RES: 100,
        BaseStats.ACC: 90, BaseStats.AVO: 60, BaseStats.SPD: 60
    }, {
        CombatStats.RANGE: 1
    }, {
        CombatStats.BASIC_MP_GAIN_MULT: 7 / BASIC_ATTACK_MP_GAIN,
        CombatStats.RESISTANCE_MODIFIER: 1.25
    }, 0.4, AttackType.MELEE, PhysicalAttackAttribute.CRUSHING, [
        weaknessEffect(PhysicalAttackAttribute.PIERCING, 1),
        weaknessEffect(PhysicalAttackAttribute.SLASHING, 1),
        weaknessEffect(PhysicalAttackAttribute.CRUSHING, 1),
        resistanceShifter
    ], [waitSkill("", 0.35), burstAttack, aoeAttack, waitSkill("", 0.7)],
    "A strangely-shaped golem lumbers out of the darkness!", "",
    EnemyAI({"aiIdx": 0, "aoeCd": 8, "aoeReset": False}, decisionFn),
    lambda controller, entity:
        EnemyReward(15, 6, 0, makeBasicUncommonDrop(controller.rng, 0, 1, 1, getWeaponClasses(MELEE_WEAPON_TYPES))
                    if controller._randomRoll(None, entity) <= 0.1 else
                    makeBasicCommonDrop(controller.rng, 6, 9, 1, getWeaponClasses(MELEE_WEAPON_TYPES))))


def scSpiritBoss(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    damageReductionPerEnemy = 0.3
    def lifelinkFn(source : CombatEntity):
        def returnFn(controller : CombatController, user : CombatEntity, attacker : CombatEntity, defender : CombatEntity, _):
            if defender != source:
                return
            
            damageReduction : dict[Stats, float] = {CombatStats.DAMAGE_REDUCTION: damageReductionPerEnemy}
            controller.applyFlatStatBonuses(defender, damageReduction)
            revertEffectFn = EFAfterNextAttack(
                lambda controller_, attacker_, defender_, _1, _2: controller_.revertFlatStatBonuses(defender, damageReduction)
            )
            redirectEffectFn = EFAfterNextAttack(
                lambda controller_, attacker_, _1, attackResult, _2:
                    attackResult.addBonusAttack(attacker_, user, CounterSkillData(attackResult.isPhysical, attackResult.attackType, 1,
                            [SkillEffect("", [EFBeforeNextAttack({
                                CombatStats.IGNORE_RANGE_CHECK: 1,
                                CombatStats.FIXED_ATTACK_POWER: attackResult.damageDealt / (1 - (damageReductionPerEnemy * (len(controller_.getTeammates(user))-1))) * 0.4
                            }, {
                                CombatStats.AGGRO_MULT: 5
                            }, None, None)], 0)])) if len(controller_.getTeammates(user)) > 1 else None
            )
            followupEffect : SkillEffect = SkillEffect("", [revertEffectFn, redirectEffectFn], 0)
            controller.addSkillEffect(attacker, followupEffect)
        return returnFn
    defeatedAllyMsg = [
        "The Covairit condenses, becoming more vulnerable!",
        "The Covairit's aura cracks further!",
        "The Covairit's presence falters!"
    ]
    def allyTrackFn(source : CombatEntity):
        def returnFn(controller : CombatController, user : CombatEntity, _1, _2, _3):
            if controller.getCurrentHealth(source) <= 0:
                return
            if controller.getCurrentHealth(user) <= 0:
                remainingAllies = len(controller.getTeammates(source)) - 1
                controller.logMessage(MessageType.EFFECT, defeatedAllyMsg[remainingAllies])
                if remainingAllies == 0:
                    [controller.addWeaknessStacks(source, attribute, 1) for attribute in PhysicalAttackAttribute]
        return returnFn
    lifelinkSkill = PassiveSkillData("Limestone Fracture", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {}, [
        SkillEffect("", [EFImmediate(
            lambda controller, user, _1, _2: void(
                [(
                    controller.addSkillEffect(teammate, SkillEffect("Creeping Limestone", [EFBeforeAllyAttacked(lifelinkFn(user))], None)),
                    controller.addSkillEffect(teammate, SkillEffect("Breaking Limestone", [EFWhenAttacked(allyTrackFn(user))], None)),
                ) for teammate in controller.getTeammates(user) if teammate != user]
            ))
        ], None)
    ], False)

    attackSkill = AttackSkillData("Quartzite Ray", BasePlayerClassNames.WARRIOR, 0, False, 15, "",
                                  False, AttackType.MAGIC, 1, DEFAULT_ATTACK_TIMER_USAGE, [
                                      SkillEffect("", [EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1}, {}, None, None)], 0)
                                  ], False)
    
    rockSkill = AttackSkillData("Calcite Entombing", BasePlayerClassNames.WARRIOR, 0, False, 20, "",
                                False, AttackType.MAGIC, 1.65, DEFAULT_ATTACK_TIMER_USAGE * 1.35, [
                                    SkillEffect("", [
                                        EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1}, {}, None, None),
                                        EFAfterNextAttack(getIncreaseDistanceFn(2)),
                                        EFAfterNextAttack(
                                            lambda controller, user, target, attackResult, _: void((
                                                controller.applyMultStatBonuses(target, {
                                                    BaseStats.DEF: 0.9,
                                                    BaseStats.RES: 0.9
                                                }),
                                                controller.logMessage(MessageType.EFFECT,
                                                                      f"{target.name}'s DEF and RES are lowered by the lingering Calcite!")
                                            )) if attackResult.attackHit else None
                                        )
                                    ], 0)
                                ], False)
    batSkill = ActiveBuffSkillData("Dolomite Dust", BasePlayerClassNames.WARRIOR, 0, False, 20, "", MAX_ACTION_TIMER * 0.2, {}, {}, [
        SkillEffect("Dolomite Dust", [
            EFImmediate(
                lambda controller, user, _1, _2: void((
                    controller.applyMultStatBonuses(user, {CombatStats.ACTION_GAUGE_USAGE_MULTIPLIER: 0.5}),
                    controller.logMessage(MessageType.EFFECT, f"{user.name} diffuses swiftly through the dust cloud!")
                )) 
            ), 
            EFStartTurn(
                lambda controller, user, _: controller.applyMultStatBonuses(user, {CombatStats.ACTION_GAUGE_USAGE_MULTIPLIER: 0.5})
            ),
            EFEndTurn(
                lambda controller, user, _1, _2: controller.revertMultStatBonuses(user, {CombatStats.ACTION_GAUGE_USAGE_MULTIPLIER: 0.5})
            )
        ], 4, "Dolomite Dust wore off.")
    ], 0, 0, False, False)
    fairySkill = ActiveBuffSkillData("Gypsum Healing", BasePlayerClassNames.WARRIOR, 0, False, 20, "",
                                     MAX_ACTION_TIMER * 0.6, {}, {}, [
                                         SkillEffect("", [EFImmediate(
                                             lambda controller, enemy, targets, _: void((
                                                 controller.logMessage(MessageType.EFFECT, f"The opponents are invigorated by the pale glow! Their DEF and RES increase!"),
                                                 [controller.doHealSkill(enemy, target, 1) for target in targets],
                                                 [controller.applyMultStatBonuses(target, {
                                                     BaseStats.DEF: 1.15,
                                                     BaseStats.RES: 1.15
                                                 }) for target in targets]
                                         )))], 0)
                                     ], None, 0, False, False)

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        allTargets = controller.getTargets(enemy)
        currentMana = controller.getCurrentMana(enemy)

        allTeammates = controller.getTeammates(enemy)
        allyNames = [ally.name for ally in allTeammates if ally != enemy]
        rockAllyDead = "Stalactun" not in allyNames
        batAllyDead = "Byebat" not in allyNames
        fairyAllyDead = "Deposylph" not in allyNames

        # CD ticks
        for cdKey in ["retreatCd", "rockCd", "batCd", "fairyCd"]:
            data[cdKey] -= 1
            
        defaultTarget = controller.getAggroTarget(enemy)
        targetIdx = allTargets.index(defaultTarget)

        if data["rockCd"] <= 0 and rockAllyDead:
            rockCost = controller.getSkillManaCost(enemy, rockSkill)
            assert(rockCost is not None)
            if currentMana >= rockCost and controller.checkDistanceStrict(enemy, defaultTarget) <= 1:
                data["rockCd"] = 3
                return EnemyAIAction(CombatActions.SKILL, 1, [targetIdx], None, None)
            
        if data["batCd"] <= 0 and batAllyDead:
            batCost = controller.getSkillManaCost(enemy, batSkill)
            assert(batCost is not None)
            if currentMana >= batCost:
                data["batCd"] = 7
                return EnemyAIAction(CombatActions.SKILL, 2, [], None, None)

        if data["retreatCd"] <= 0:
            distMap = {target : controller.checkDistanceStrict(enemy, target) for target in allTargets}
            retreatTargets = [target for target in distMap if distMap[target] <= 1]
            if len(retreatTargets) > 0:
                retreatAmount = 2 if len(retreatTargets) == 1 else 1
                retreatTargetIdxs = [allTargets.index(target) for target in rng.sample(retreatTargets, min(2, len(retreatTargets)))]
                data["retreatCd"] = 3
                return EnemyAIAction(CombatActions.RETREAT, None, retreatTargetIdxs, retreatAmount, None)
            
        if data["fairyCd"] <= 0 and fairyAllyDead:
            healNeeded = False
            for teammate in allTeammates:
                hpRatio = controller.getCurrentHealth(teammate) / controller.getMaxHealth(teammate)
                if hpRatio <= 0.75:
                    healNeeded = True
                    break
            fairyCost = controller.getSkillManaCost(enemy, fairySkill)
            assert(fairyCost is not None)
            if currentMana >= fairyCost and healNeeded:
                allAllyIndices = []
                for i in range(len(allTeammates)):
                    allAllyIndices.append(i)
                data["fairyCd"] = 5
                return EnemyAIAction(CombatActions.SKILL, 3, allAllyIndices, None, None)
            
        # no cooldowns available
        attackCost = controller.getSkillManaCost(enemy, attackSkill)
        assert attackCost is not None
        if currentMana >= attackCost:
            return EnemyAIAction(CombatActions.SKILL, 0, [targetIdx], None, None)
        else:
            return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
    return Enemy("Karstic Covairit", "Covairit",
                 "A spirit associated with dissolved stone. Despite its lack of expression, a smug aura radiates from it as it hides behind other creatures.", 5, {
        BaseStats.HP: 450, BaseStats.MP: 300,
        BaseStats.ATK: 40, BaseStats.DEF: 30, BaseStats.MAG: 65, BaseStats.RES: 80,
        BaseStats.ACC: 140, BaseStats.AVO: 80, BaseStats.SPD: 75
    }, {
        CombatStats.RANGE: 0
    }, {
        CombatStats.BASIC_MP_GAIN_MULT: 13 / BASIC_ATTACK_MP_GAIN
    }, 0.3, None, None, [lifelinkSkill], [attackSkill, rockSkill, batSkill, fairySkill],
    "A spectral force lurks behind the cave's creatures!", "",
    EnemyAI({"aiIdx": 0, "retreatCd": 0, "rockCd": 0, "batCd": 0, "fairyCd": 0}, decisionFn),
    lambda controller, entity:
        EnemyReward(13, 6, 0, makeBasicUncommonDrop(controller.rng, 0, 1, 1, getWeaponClasses(MELEE_WEAPON_TYPES))
                    if controller._randomRoll(None, entity) <= 0.1 else
                    makeBasicCommonDrop(controller.rng, 6, 9, 1, getWeaponClasses(MELEE_WEAPON_TYPES))))

## Saffron Forest

def sfRat(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 0 }
    roomNumber = params.get('roomNumber', 0)
    if not params.get('storehouse', False):
        if roomNumber > 0:
            maxVars = {
                BaseStats.HP: 10 if roomNumber == 1 else 30,
                BaseStats.ATK: 5 if roomNumber == 1 else 10,
                BaseStats.DEF: 5 if roomNumber == 1 else 10,
                BaseStats.RES: 5 if roomNumber == 1 else 10,
                BaseStats.ACC: 10,
                BaseStats.AVO: 5 if roomNumber == 1 else 10,
                BaseStats.SPD: 10 if roomNumber == 1 else 20
            }
            for stat in maxVars:
                flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])
    else:
        maxVarsRoomMap = {
            BaseStats.HP: [0, 30, 80],
            BaseStats.ATK: [0, 5, 20],
            BaseStats.DEF: [0, 5, 15],
            BaseStats.RES: [0, 5, 15],
            BaseStats.ACC: [0, 10, 30],
            BaseStats.AVO: [0, 5, 15, 25],
            BaseStats.SPD: [0, 5, 15]
        }
        maxVars = {
            stat: maxVarsRoomMap[stat][min(roomNumber, len(maxVarsRoomMap[stat])-1)]
            for stat in maxVarsRoomMap
        }
        for stat in maxVars:
            if maxVars[stat] > 0:
                flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])

    intrepidRatSkill = PassiveSkillData("Mark of Intrepid Rat", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {}, [SkillEffect("", [
        EFAfterNextAttack(lambda controller, _1, target, attackResult, _2: void((
            controller.logMessage(MessageType.EFFECT, f"{target.name} is marked for other rats!")
                if controller.combatStateMap[target].getStack(EffectStacks.RAT_MARK_INTREPID) == 0 else None,
            controller.combatStateMap[target].addStack(EffectStacks.RAT_MARK_INTREPID, 10),
            controller.combatStateMap[target].addStack(EffectStacks.RAT_MARK_INTREPID, 10)
        )) if attackResult.attackHit else None)
    ], None)], False)

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        target = controller.getAggroTarget(enemy)
        targetIdx = controller.getTargets(enemy).index(target)
        if controller.checkInRange(enemy, target):
            return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
        else:
            distance = controller.checkDistanceStrict(enemy, target)
            return EnemyAIAction(CombatActions.APPROACH, None, [targetIdx], min(distance, 2), None)
        
    baseStats = {
        BaseStats.HP: 140, BaseStats.MP: 1,
        BaseStats.ATK: 40, BaseStats.DEF: 30, BaseStats.MAG: 1, BaseStats.RES: 35,
        BaseStats.ACC: 80, BaseStats.AVO: 90, BaseStats.SPD: 75
    } if not params.get('storehouse', False) else {
        BaseStats.HP: 220, BaseStats.MP: 1,
        BaseStats.ATK: 70, BaseStats.DEF: 65, BaseStats.MAG: 1, BaseStats.RES: 65,
        BaseStats.ACC: 100, BaseStats.AVO: 110, BaseStats.SPD: 85
    }
    level = 3 if not params.get('storehouse', False) else 4
    minRank, maxRank, wepChance = (2, 5, 0) if not params.get('storehouse', False) else (4, 7, 0.2)
    return Enemy("Gatherat", "Gatherat",
                 "A forest rat. Its hunger for battle is surpassed only by its hunger for food, but it's not particularly close.", level,
                 baseStats, flatStatMods, {}, 0.5, None, None, [ratMarkSkill, intrepidRatSkill], [],
    "\\*squeak squak\\*", "",
    EnemyAI({}, decisionFn),
    lambda controller, entity:
        EnemyReward(3, 0, 0, rollEquip(controller, entity, 0.2,
                                       makeBasicCommonDrop(controller.rng, minRank, maxRank, wepChance)))
        if not (params.get('boss', False) or params.get('summoned', False)) else EnemyReward(1, 0, 0, None))


def sfReaper(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 0 }
    roomNumber = params.get('roomNumber', 0)
    if roomNumber > 0:
        maxVars = {
            BaseStats.HP: 30 if roomNumber == 1 else 100,
            BaseStats.ATK: 10 if roomNumber == 1 else 40,
            BaseStats.DEF: 5 if roomNumber == 1 else 20,
            BaseStats.RES: 5 if roomNumber == 1 else 20,
            BaseStats.ACC: 10,
            BaseStats.SPD: 10
        }
        for stat in maxVars:
            flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])

    proximitySkill = PassiveSkillData("Faceless Fear", BasePlayerClassNames.WARRIOR, 0, False, "",
                                    {}, {}, [SkillEffect("", [
                                        EFBeforeAttacked(
                                            {}, {},
                                            lambda controller, user, attacker: void((
                                                controller.combatStateMap[user].setStack(
                                                    EffectStacks.ENEMY_COUNTER_A, 3 - controller.checkDistanceStrict(user, attacker)),
                                                controller.applyMultStatBonuses(user, {
                                                    BaseStats.DEF: 1 - (0.175 * controller.combatStateMap[user].getStack(EffectStacks.ENEMY_COUNTER_A)),
                                                    BaseStats.RES: 1 - (0.175 * controller.combatStateMap[user].getStack(EffectStacks.ENEMY_COUNTER_A))
                                                })
                                            )),
                                            lambda controller, user, attacker, _: void((
                                                controller.revertMultStatBonuses(user, {
                                                    BaseStats.DEF: 1 - (0.175 * controller.combatStateMap[user].getStack(EffectStacks.ENEMY_COUNTER_A)),
                                                    BaseStats.RES: 1 - (0.175 * controller.combatStateMap[user].getStack(EffectStacks.ENEMY_COUNTER_A))
                                                }),
                                                controller.combatStateMap[user].setStack(EffectStacks.ENEMY_COUNTER_A, 0)
                                            )))
                                    ], None)], False)
    attackSkill = AttackSkillData("The Decomposer", BasePlayerClassNames.WARRIOR, 0, False, 15, "",
                                  True, None, 3, MAX_ACTION_TIMER, [], False)

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        currentMana = controller.getCurrentMana(enemy)

        target = controller.getAggroTarget(enemy)
        targetIdx = controller.getTargets(enemy).index(target)
        if controller.checkInRange(enemy, target):
            attackCost = controller.getSkillManaCost(enemy, attackSkill)
            assert(attackCost is not None)
            if currentMana >= attackCost:
                return EnemyAIAction(CombatActions.SKILL, 0, [targetIdx], None, None)
            else:
                return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
        else:
            return EnemyAIAction(CombatActions.APPROACH, None, [targetIdx], 1, None)
    return Enemy("Grimycobe", "Grimycobe",
                 "A fungus with a pattern resembling a long, dark cloak. It feels like it gets closer whenever you're not looking at it.", 3, {
        BaseStats.HP: 200, BaseStats.MP: 30,
        BaseStats.ATK: 110, BaseStats.DEF: 100, BaseStats.MAG: 1, BaseStats.RES: 100,
        BaseStats.ACC: 100, BaseStats.AVO: 50, BaseStats.SPD: 30
    }, flatStatMods, {
        CombatStats.REPOSITION_ACTION_TIME_MULT: 1.65
    }, 0.85, AttackType.MELEE, PhysicalAttackAttribute.SLASHING,
    [
        proximitySkill,
        weaknessEffect(MagicalAttackAttribute.LIGHT, 1),
        resistanceEffect(MagicalAttackAttribute.DARK, 1)
    ], [attackSkill],
    "The forest seems to darken with the Grimycobe's presence...", "",
    EnemyAI({}, decisionFn),
    lambda controller, entity:
        EnemyReward(3, 1 if controller._randomRoll(None, entity) <= 0.35 else 0,
                    0, rollEquip(controller, entity, 0.2,
                                       makeBasicCommonDrop(controller.rng, 3, 6, 0.25,
                                                           getWeaponClasses(RANGED_WEAPON_TYPES) + getWeaponClasses(MAGIC_WEAPON_TYPES))))
        if not params.get('boss', False) else EnemyReward(1, 0, 0, None))


def sfNinja(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 2 }
    roomNumber = params.get('roomNumber', 0)
    if roomNumber > 0:
        maxVars = {
            BaseStats.HP: 10 if roomNumber == 1 else 30,
            BaseStats.ATK: 10 if roomNumber == 1 else 30,
            BaseStats.MAG: 10 if roomNumber == 1 else 30,
            BaseStats.DEF: 10,
            BaseStats.RES: 10,
            BaseStats.ACC: 10,
            BaseStats.AVO: 10 if roomNumber == 1 else 30,
            BaseStats.SPD: 5 if roomNumber == 1 else 15,
        }
        for stat in maxVars:
            flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])

    if params.get('boss', False):
        flatStatMods[BaseStats.HP] += 60
        flatStatMods[BaseStats.SPD] += 10

    bindSkill = AttackSkillData("Dragonfly Binding Art", BasePlayerClassNames.WARRIOR, 0, False, 30, "",
                                False, AttackType.MAGIC, 1, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect("", [
                                    EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1}, {}, None, None),
                                    EFAfterNextAttack(lambda controller, user, target, attackResult, _: void(
                                        controller.applyStatusCondition(target, RestrictStatusEffect(user, target, 3)) if attackResult.attackHit else None)),
                                    EFOnStatusApplied(
                                        lambda controller, _1, target, statusName, _2: void((
                                            controller.applyMultStatBonuses(target, {
                                                BaseStats.SPD: 0.85
                                            }),
                                            controller.logMessage(MessageType.EFFECT,
                                                                f"{target.name}'s SPD is lowered by the binding!")
                                            )) if statusName == StatusConditionNames.RESTRICT else None)
                                ], 0)], False)

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        currentMana = controller.getCurrentMana(enemy)

        # CD ticks
        for cdKey in ["repositionCd"]:
            data[cdKey] -= 1

        target = controller.getAggroTarget(enemy)
        targetIdx = controller.getTargets(enemy).index(target)

        distToTarget = controller.checkDistanceStrict(enemy, target)
        if data['repositionCd'] <= 0 and distToTarget != 2:
            data['repositionCd'] = 4
            data['repositionTarget'] = target
            distance = abs(distToTarget - 2)
            if distToTarget < 2:
                return EnemyAIAction(CombatActions.RETREAT, None, [targetIdx], min(distance, 2), None)
            else:
                return EnemyAIAction(CombatActions.APPROACH, None, [targetIdx], min(distance, 2), None) 
            
        if data['repositionTarget'] is not None:
            repositionTarget = data['repositionTarget']
            if controller.getCurrentHealth(repositionTarget) > 0:
                distToTarget = controller.checkDistanceStrict(enemy, repositionTarget)
                bindManaCost = controller.getSkillManaCost(enemy, bindSkill)
                assert bindManaCost is not None
                if distToTarget != 2 and currentMana >= bindManaCost:
                    repositionTargetIdx = controller.getTargets(enemy).index(repositionTarget)
                    data['repositionCd'] = 0
                    return EnemyAIAction(CombatActions.SKILL, 0, [repositionTargetIdx], None, None)
                
        if data['repositionCd'] <= 2:
            data['repositionTarget'] = None
           
        if controller.checkInRange(enemy, target):
            return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
        else:
            distance = controller.checkDistanceStrict(enemy, target) - controller.combatStateMap[enemy].getTotalStatValue(CombatStats.RANGE)
            return EnemyAIAction(CombatActions.APPROACH, None, [targetIdx], min(distance, 2), None)
    return Enemy("Genonata", "Genonata",
                 "A dragonfly-like creature, from what you can tell when it allows itself to be seen. Its only sounds are whispers of a ninja way.", 3, {
        BaseStats.HP: 120, BaseStats.MP: 60,
        BaseStats.ATK: 45, BaseStats.DEF: 40, BaseStats.MAG: 45, BaseStats.RES: 40,
        BaseStats.ACC: 110, BaseStats.AVO: 125, BaseStats.SPD: 70
    }, flatStatMods, {
        CombatStats.REPOSITION_ACTION_TIME_MULT: 0.7,
        CombatStats.BASIC_MP_GAIN_MULT: 8 / BASIC_ATTACK_MP_GAIN
    }, 0.5, AttackType.RANGED, PhysicalAttackAttribute.PIERCING,
    [], [bindSkill],
    "", "",
    EnemyAI({"repositionCd": 0, "repositionTarget": None}, decisionFn),
    lambda controller, entity:
        EnemyReward(3, 1 if controller._randomRoll(None, entity) <= 0.35 else 0,
                    0, rollEquip(controller, entity, 0.2,
                                       makeBasicCommonDrop(controller.rng, 3, 6, 0.25,
                                                           getWeaponClasses(RANGED_WEAPON_TYPES))))
        if not params.get('boss', False) else EnemyReward(1, 0, 0, None))


def sfElemental(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    mainElement = params.get("element", None)
    if mainElement is None:
        mainElement = random.choice([MagicalAttackAttribute.FIRE, MagicalAttackAttribute.WIND, MagicalAttackAttribute.ICE])
    weakElement = {
        MagicalAttackAttribute.FIRE: MagicalAttackAttribute.WIND,
        MagicalAttackAttribute.WIND: MagicalAttackAttribute.ICE,
        MagicalAttackAttribute.ICE: MagicalAttackAttribute.FIRE
    }[mainElement]
    colorString = {
        MagicalAttackAttribute.FIRE: "Red",
        MagicalAttackAttribute.WIND: "Green",
        MagicalAttackAttribute.ICE: "Blue"
    }[mainElement]

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 0 }
    roomNumber = params.get('roomNumber', 0)
    if roomNumber > 0:
        maxVars = {
            BaseStats.HP: 20 if roomNumber == 1 else 50,
            BaseStats.MAG: 10 if roomNumber == 1 else 20,
            BaseStats.DEF: 5 if roomNumber == 1 else 15,
            BaseStats.RES: 5 if roomNumber == 1 else 15,
            BaseStats.ACC: 5 if roomNumber == 1 else 15,
            BaseStats.AVO: 5 if roomNumber == 1 else 15,
            BaseStats.SPD: 10 if roomNumber == 1 else 20,
        }
        for stat in maxVars:
            flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])

    attackSkill = AttackSkillData(f"Violet {enumName(mainElement)}", BasePlayerClassNames.WARRIOR, 0, False, 15, "",
                                  False, AttackType.MAGIC, 1, DEFAULT_ATTACK_TIMER_USAGE, [
                                      SkillEffect("", [EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1}, {}, None, None)], 0)
                                  ], False)
    
    buffName, buffStats, debuffName, debuffStats = {
        MagicalAttackAttribute.FIRE: ("Invigorating Summer", (BaseStats.ATK, BaseStats.MAG, BaseStats.ACC),
                                      "Spirit Burn", (BaseStats.DEF, BaseStats.RES)),
        MagicalAttackAttribute.WIND: ("Liberating Spring", (BaseStats.AVO, BaseStats.SPD),
                                      "Spirit Sap", (BaseStats.ATK, BaseStats.MAG, BaseStats.ACC)),
        MagicalAttackAttribute.ICE: ("Fortifying Winter", (BaseStats.DEF, BaseStats.RES),
                                     "Spirit Chill", (BaseStats.AVO, BaseStats.SPD))
    }[mainElement]

    buffSkill = ActiveBuffSkillData(buffName, BasePlayerClassNames.WARRIOR, 0, False, 20, "",
                                     DEFAULT_ATTACK_TIMER_USAGE * 0.75, {}, {}, [
                                         SkillEffect("", [EFImmediate(
                                             lambda controller, enemy, targets, _: void((
                                                 controller.logMessage(MessageType.EFFECT,
                                                                       f"The Saffelt's aura increases its allies' {'/'.join([stat.name for stat in buffStats])}!"),
                                                 [controller.applyMultStatBonuses(target, {
                                                     stat: 1.1 for stat in buffStats
                                                 }) for target in targets]
                                         )))], 0)
                                     ], None, 0, False, False)

    debuffSkill = AttackSkillData(debuffName, BasePlayerClassNames.WARRIOR, 0, False, 20, "",
                                  False, AttackType.MAGIC, 1.2, DEFAULT_ATTACK_TIMER_USAGE, [
                                      SkillEffect("", [EFAfterNextAttack(
                                          lambda controller, user, target, attackResult, _: void((
                                              controller.logMessage(
                                                  MessageType.EFFECT, f"The Saffelt's aura drains {target.name}'s {'/'.join([stat.name for stat in debuffStats])}!"),
                                              controller.applyMultStatBonuses(target, {
                                                  stat: 0.9 for stat in debuffStats
                                              })
                                          )) if attackResult.attackHit else None
                                      )], 0)
                                  ], False)

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        currentMana = controller.getCurrentMana(enemy)

        # CD ticks
        for cdKey in ["attackCd", "buffCd", "debuffCd"]:
            data[cdKey] -= 1

        target = controller.getAggroTarget(enemy)
        targetIdx = controller.getTargets(enemy).index(target)

        if data["buffCd"] <= 0:
            buffManaCost = controller.getSkillManaCost(enemy, buffSkill)
            assert buffManaCost is not None
            if currentMana >= buffManaCost:
                enemyAllies = controller.getTeammates(enemy)
                data['buffCd'] = 5
                return EnemyAIAction(CombatActions.SKILL, 1, [i for i in range(len(enemyAllies))], None, None)

        if data["debuffCd"] <= 0:
            debuffManaCost = controller.getSkillManaCost(enemy, debuffSkill)
            assert debuffManaCost is not None
            if controller.checkInRange(enemy, target) and currentMana >= debuffManaCost:
                data['debuffCd'] = 2
                return EnemyAIAction(CombatActions.SKILL, 2, [targetIdx], None, None)

        if data["attackCd"] <= 0:
            attackManaCost = controller.getSkillManaCost(enemy, attackSkill)
            assert attackManaCost is not None
            if currentMana >= attackManaCost:
                data['attackCd'] = 2
                return EnemyAIAction(CombatActions.SKILL, 0, [targetIdx], None, None)

        # No cooldowns available
        if controller.checkInRange(enemy, target):
            return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
        else:
            distance = controller.checkDistanceStrict(enemy, target) - controller.combatStateMap[enemy].getTotalStatValue(CombatStats.RANGE)
            return EnemyAIAction(CombatActions.APPROACH, None, [targetIdx], min(distance, 2), None)
                
           
    return Enemy(f"{colorString} Saffelt", f"{colorString[0]}.Saffelt",
                 "An elemental spirit living amongst the saffron flowers. Dangerous up close, no matter how nice they smell.", 3, {
        BaseStats.HP: 150, BaseStats.MP: 150,
        BaseStats.ATK: 10, BaseStats.DEF: 40, BaseStats.MAG: 60, BaseStats.RES: 85,
        BaseStats.ACC: 100, BaseStats.AVO: 75, BaseStats.SPD: 60
    }, flatStatMods, {
        CombatStats.BASIC_MP_GAIN_MULT: 5 / BASIC_ATTACK_MP_GAIN
    }, 0.5, AttackType.MAGIC, mainElement,
    [
        weaknessEffect(weakElement, 1),
        resistanceEffect(mainElement, 1)
    ], [attackSkill, buffSkill, debuffSkill],
    "", "",
    EnemyAI({"attackCd": 0, "buffCd": 3, "debuffCd": 0}, decisionFn),
    lambda controller, entity:
        EnemyReward(3, 1 if controller._randomRoll(None, entity) <= 0.35 else 0,
                    0, rollEquip(controller, entity, 0.2,
                                       makeBasicCommonDrop(controller.rng, 3, 6, 0.25,
                                                           getWeaponClasses(MAGIC_WEAPON_TYPES))))
        if not params.get('boss', False) else EnemyReward(1, 0, 0, None))


def sfNinjaBoss(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 2 }

    kiSkill = PassiveSkillData("Floating Butterfly", BasePlayerClassNames.WARRIOR, 0, False, "",
                               {}, {}, [SkillEffect("", [
                                   EFWhenAttacked(
                                       lambda controller, user, attacker, attackResult, _: void((
                                           controller.combatStateMap[user].addStack(EffectStacks.BUTTERFLY_KI, None),
                                           controller.combatStateMap[user].addStack(EffectStacks.BUTTERFLY_KI, None)
                                       )) if (not attackResult.attackHit and attackResult.inRange) else None
                                   )
                               ], None)], False)
    
    kiCancelEffect = EFAfterNextAttack(
        lambda controller, user, _1, _2, _3: void((
            controller.combatStateMap[user].removeStack(EffectStacks.BUTTERFLY_KI),
            controller.increaseActionTimer(user, 0.4),
            controller.logMessage(MessageType.EFFECT, f"{user.name}'s inner energy surges!")
        )) if controller.combatStateMap[user].getStack(EffectStacks.BUTTERFLY_KI) > 0 else None
    )
    
    def slashResetEffect(source : CombatEntity):
        effect = SkillEffect("", [
            EFStartTurn(
                lambda controller, user, _: void((
                    controller.logMessage(MessageType.EFFECT, f"{source.name}'s assault eases up!"),
                    controller.combatStateMap[source].setStack(EffectStacks.ENEMY_COUNTER_A, 0)
                ))
            )
        ], 1)
        return effect
    slashSkill = AttackSkillData("Butterfly Art: Habataku", BasePlayerClassNames.WARRIOR, 0, False, 10, "",
                                 True, AttackType.MELEE, 1, DEFAULT_ATTACK_TIMER_USAGE * 0.65, [
                                     SkillEffect("", [
                                        EFBeforeNextAttack(
                                            { CombatStats.RANGE: -2 }, {},
                                            lambda controller, user, _1, _2: void((
                                                controller.applyMultStatBonuses(user, {
                                                    BaseStats.ATK: 0.8 + (0.3 * controller.combatStateMap[user].getStack(EffectStacks.ENEMY_COUNTER_A))
                                                }),
                                                controller.logMessage(MessageType.EFFECT, f"{user.name}'s strikes gain momentum!")
                                            )),
                                            lambda controller, user, target, attackResult, _: void((
                                                controller.revertMultStatBonuses(user, {
                                                    BaseStats.ATK: 0.8 + (0.3 * controller.combatStateMap[user].getStack(EffectStacks.ENEMY_COUNTER_A))
                                                }),
                                                controller.addSkillEffect(target, slashResetEffect(user))
                                                    if controller.combatStateMap[user].getStack(EffectStacks.ENEMY_COUNTER_A) == 0 else None,
                                                controller.combatStateMap[user].addStack(EffectStacks.ENEMY_COUNTER_A, None)
                                            ))
                                        ),
                                        kiCancelEffect
                                     ], 0)
                                 ], False)
    
    approachSkill = AttackSkillData("Butterfly Art: Tsukiga Ochiru", BasePlayerClassNames.WARRIOR, 0, False, 15, "",
                                  True, AttackType.MELEE, 1.2, DEFAULT_ATTACK_TIMER_USAGE, [
                                      SkillEffect("", [
                                          EFImmediate(
                                              lambda controller, enemy, targets, _: void(controller.updateDistance(enemy, targets[0], 0))
                                          ),
                                          EFBeforeNextAttack(
                                              {}, {},
                                              lambda controller, user, _1, _2: void((
                                                  controller.applyMultStatBonuses(user, {
                                                      BaseStats.ATK: 1.5
                                                  }),
                                                  controller.logMessage(MessageType.EFFECT, f"{user.name}'s wings glow bright!"),
                                                  controller.combatStateMap[user].removeStack(EffectStacks.BUTTERFLY_KI),
                                                  controller.combatStateMap[user].setStack(EffectStacks.ENEMY_COUNTER_B, 1)
                                              )) if controller.combatStateMap[user].getStack(EffectStacks.BUTTERFLY_KI) > 0 else None,
                                              lambda controller, user, _1, _2, _3: void((
                                                  controller.revertMultStatBonuses(user, {
                                                      BaseStats.ATK: 1.5
                                                  }),
                                                  controller.combatStateMap[user].setStack(EffectStacks.ENEMY_COUNTER_B, 0)
                                              )) if controller.combatStateMap[user].getStack(EffectStacks.ENEMY_COUNTER_B) > 0 else None
                                          ),
                                          kiCancelEffect
                                      ], 0, None)
                                  ], False)
    
    retreatSkill = AttackSkillData("Butterfly Art: Tsukiga Shutsu", BasePlayerClassNames.WARRIOR, 0, False, 15, "",
                                  False, AttackType.MAGIC, 1.2, DEFAULT_ATTACK_TIMER_USAGE, [
                                      SkillEffect("", [
                                          EFImmediate(
                                              lambda controller, enemy, targets, _: void(controller.updateDistance(enemy, targets[0], 3))
                                          ),
                                          EFBeforeNextAttack(
                                              {CombatStats.IGNORE_RANGE_CHECK: 1}, {},
                                              lambda controller, user, _1, _2: void((
                                                  controller.applyMultStatBonuses(user, {
                                                      BaseStats.MAG: 1.5
                                                  }),
                                                  controller.logMessage(MessageType.EFFECT, f"{user.name}'s wings glow bright!"),
                                                  controller.combatStateMap[user].removeStack(EffectStacks.BUTTERFLY_KI),
                                                  controller.combatStateMap[user].setStack(EffectStacks.ENEMY_COUNTER_B, 1)
                                              )) if controller.combatStateMap[user].getStack(EffectStacks.BUTTERFLY_KI) > 0 else None,
                                              lambda controller, user, _1, _2, _3: void((
                                                  controller.revertMultStatBonuses(user, {
                                                      BaseStats.MAG: 1.5
                                                  }),
                                                  controller.combatStateMap[user].setStack(EffectStacks.ENEMY_COUNTER_B, 0)
                                              )) if controller.combatStateMap[user].getStack(EffectStacks.ENEMY_COUNTER_B) > 0 else None
                                          ),
                                          kiCancelEffect
                                      ], 0, None)
                                  ], False)

    rangeSkill = AttackSkillData(
        "Butterfly Art: Chou No Hitokuchi", BasePlayerClassNames.WARRIOR, 0, False, 30, "",
        True, AttackType.RANGED, 1, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect("", [
            EFBeforeNextAttack({ CombatStats.RANGE: 1 }, { BaseStats.ACC: 1.5 },
                lambda controller, user, target, _2: void((
                    controller.applyMultStatBonuses(user, {BaseStats.ATK: 1 + (controller.checkDistanceStrict(user, target) * 0.5)}),
                    controller.applyFlatStatBonuses(user, {CombatStats.CRIT_RATE: 1})
                        if len(controller.combatStateMap[target].currentStatusEffects) > 0 else None
                )),
                lambda controller, user, target, attackResult, _: void((
                    controller.revertMultStatBonuses(user, {BaseStats.ATK: 1 + (attackResult.originalDistance * 0.5)}),
                    controller.revertFlatStatBonuses(user, {CombatStats.CRIT_RATE: 1})
                        if len(controller.combatStateMap[target].currentStatusEffects) > 0 else None
                ))
        )], 0)], False)

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        currentMana = controller.getCurrentMana(enemy)

        # CD ticks
        for cdKey in ["slashCd", "rangeCd"]:
            data[cdKey] -= 1

        target = controller.getAggroTarget(enemy) if data["holdTarget"] is None else data["holdTarget"]
        # check for restricted opponent
        if data["aiIdx"] < 3 and data["rangeCd"] < 3 and data["holdTarget"] is None:
            for checkTarget in controller.getTargets(enemy):
                if len(controller.combatStateMap[checkTarget].currentStatusEffects) > 0:
                    target = checkTarget
                    data["rangeCd"] = 0
                    break

        targetIdx = controller.getTargets(enemy).index(target)
        distToTarget = controller.checkDistanceStrict(enemy, target)

        # Initiate slash
        slashSkillCost = controller.getSkillManaCost(enemy, slashSkill)
        assert slashSkillCost is not None
        if data["aiIdx"] == 1:
            if currentMana >= slashSkillCost and distToTarget == 0:
                data["holdTarget"] = target
                data["aiIdx"] = 2
                controller.logMessage(MessageType.EFFECT, f"{enemy.name} produces a flash of silver!")
                return EnemyAIAction(CombatActions.SKILL, 3, [targetIdx], None, None)
            else:
                data["slashCd"] = 3
                data["aiIdx"] = 0
                return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
            
        # Repeat slash
        if data["aiIdx"] == 2:
            repeatSlash = controller.combatStateMap[enemy].getStack(EffectStacks.ENEMY_COUNTER_A) > 0
            if currentMana >= slashSkillCost and repeatSlash and controller.getCurrentHealth(target) > 0:
                return EnemyAIAction(CombatActions.SKILL, 3, [targetIdx], None, None)
            else:
                data["holdTarget"] = None
                data["aiIdx"] = 0
                data["slashCd"] = 6
                if controller.getCurrentHealth(target) <= 0:
                    target = controller.getAggroTarget(enemy)
                    
        # Initiate ranged attack
        rangeSkillCost = controller.getSkillManaCost(enemy, rangeSkill)
        assert rangeSkillCost is not None
        if data["aiIdx"] == 3:
            if currentMana >= slashSkillCost and distToTarget >= 2:
                data["holdTarget"] = target
                data["aiIdx"] = 4
                controller.logMessage(MessageType.TELEGRAPH, f"{enemy.name} takes aim!")
                return EnemyAIAction(CombatActions.SKILL, 0, [], None, None)
            else:
                data["rangeCd"] = 3
                data["aiIdx"] = 0
                return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
            
        # Fire ranged attack
        if data["aiIdx"] == 4:
            if controller.getCurrentHealth(target) <= 0:
                target = controller.getAggroTarget(enemy)
            data["holdTarget"] = None
            data["aiIdx"] = 0
            data["rangeCd"] = 6
            return EnemyAIAction(CombatActions.SKILL, 4, [targetIdx], None, None)

        # defaults
        if data["aiIdx"] == 0:
            if data["slashCd"] <= 0:
                data["aiIdx"] = 1
                if distToTarget > 0:
                    approachSkillCost = controller.getSkillManaCost(enemy, approachSkill)
                    assert approachSkillCost is not None
                    if currentMana >= approachSkillCost:
                        return EnemyAIAction(CombatActions.SKILL, 1, [targetIdx], None, None)
                    else:
                        data["slashCd"] = 2
                        return EnemyAIAction(CombatActions.APPROACH, None, [targetIdx], min(distToTarget, 2), None)
            if data["rangeCd"] <= 0:
                data["aiIdx"] = 3
                if distToTarget < 2:
                    retreatSkillCost = controller.getSkillManaCost(enemy, retreatSkill)
                    assert retreatSkillCost is not None
                    if currentMana >= retreatSkillCost:
                        return EnemyAIAction(CombatActions.SKILL, 2, [targetIdx], None, None)
                    else:
                        data["rangeCd"] = 2
                        retreatDist = abs(distToTarget - 2)
                        return EnemyAIAction(CombatActions.RETREAT, None, [targetIdx], min(retreatDist, 2), None)
                    
            if controller.checkInRange(enemy, target):
                return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
            else:
                distance = controller.checkDistanceStrict(enemy, target) - controller.combatStateMap[enemy].getTotalStatValue(CombatStats.RANGE)
                return EnemyAIAction(CombatActions.APPROACH, None, [targetIdx], min(distance, 2), None)
            
        controller.logMessage(MessageType.DEBUG, "<jounymphali ai error, should be unreachable>")
        data["aiIdx"] = 0
        return EnemyAIAction(CombatActions.DEFEND, None, [], None, None)
    return Enemy("Jounymphali", "Jounymphali",
                 "A large insect-like creature. Despite its bewitching butterfly wings, its movements are very difficult to track.", 3, {
        BaseStats.HP: 500, BaseStats.MP: 300,
        BaseStats.ATK: 60, BaseStats.DEF: 50, BaseStats.MAG: 60, BaseStats.RES: 50,
        BaseStats.ACC: 135, BaseStats.AVO: 175, BaseStats.SPD: 110
    }, flatStatMods, {
        CombatStats.REPOSITION_ACTION_TIME_MULT: 0.7,
        CombatStats.BASIC_MP_GAIN_MULT: 10 / BASIC_ATTACK_MP_GAIN
    }, 0.5, AttackType.RANGED, PhysicalAttackAttribute.SLASHING,
    [kiSkill], [waitSkill("", 0.4), approachSkill, retreatSkill, slashSkill, rangeSkill],
    "Butterfly wings rise; blossoming from the petals, a silent challenger.", "",
    EnemyAI({"aiIdx": 0, "holdTarget": None, "slashCd": 2, "rangeCd": 5}, decisionFn),
    lambda controller, entity:
        EnemyReward(14, 6, 0, makeBasicUncommonDrop(controller.rng, 0, 1, 1, getWeaponClasses(RANGED_WEAPON_TYPES) + getWeaponClasses(MAGIC_WEAPON_TYPES))
                    if controller._randomRoll(None, entity) <= 0.1 else
                    makeBasicCommonDrop(controller.rng, 6, 9, 1, getWeaponClasses(RANGED_WEAPON_TYPES) + getWeaponClasses(MAGIC_WEAPON_TYPES))))


def sfRuneBoss(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 0 }

    dashSkill = AttackSkillData("Runic Rampage", BasePlayerClassNames.WARRIOR, 0, False, 20, "",
                                  True, AttackType.MELEE, 1, DEFAULT_ATTACK_TIMER_USAGE, [
                                      SkillEffect("", [
                                          EFImmediate(
                                              lambda controller, enemy, targets, _: void((
                                                  controller.combatStateMap[enemy].setStack(EffectStacks.ENEMY_COUNTER_A, controller.checkDistanceStrict(enemy, targets[0])),
                                                  controller.updateDistance(enemy, targets[0], 0)
                                                ))
                                          ),
                                          EFBeforeNextAttack(
                                              {}, {},
                                              lambda controller, user, _1, _2: controller.applyMultStatBonuses(
                                                  user, { BaseStats.ATK: 0.9 + (controller.combatStateMap[user].getStack(EffectStacks.ENEMY_COUNTER_A) * 0.7 )}
                                              ),
                                              lambda controller, user, _1, _2, _3:  controller.revertMultStatBonuses(
                                                  user, { BaseStats.ATK: 0.9 + (controller.combatStateMap[user].getStack(EffectStacks.ENEMY_COUNTER_A) * 0.7 )}
                                              )
                                          )
                                      ], 0, None)
                                  ], False)
    
    elementOptions = [MagicalAttackAttribute.FIRE, MagicalAttackAttribute.ICE, MagicalAttackAttribute.WIND]
    altParams = {element: params.copy() for element in elementOptions}
    [altParams[element].update({'element': element}) for element in altParams]
    summonSkill = ActiveSkillDataSelector("Nature's Beloved", BasePlayerClassNames.WARRIOR, 0, False, 25, "", "",
                                          MAX_ACTION_TIMER * 0.2, 0, False, lambda element:
                                            ActiveBuffSkillData("Nature's Beloved", BasePlayerClassNames.WARRIOR, 0, False, 25, "",
                                                MAX_ACTION_TIMER * 0.2, {}, {}, [
                                                    SkillEffect("", [
                                                        EFImmediate(lambda controller, user, _2, _3: void((
                                                            controller.spawnNewEntity(sfElemental(altParams[MagicalAttackAttribute[element]], controller.rng), True),
                                                            controller.spawnNewEntity(sfElemental(altParams[MagicalAttackAttribute[element]], controller.rng), True)
                                                        )))
                                                    ], 0)
                                                ], None, 0, True, False),
                                        [element.name for element in elementOptions], False)
    
    burstSkill = AttackSkillData("Nature's Benighted", BasePlayerClassNames.WARRIOR, 0, False, 0, "",
                                 False, AttackType.MAGIC, 1, 0, [
                                     SkillEffect("", [
                                        EFBeforeNextAttack(
                                            {CombatStats.IGNORE_RANGE_CHECK: 1}, {},
                                            lambda controller, enemy, _1, _2: void((
                                                controller.combatStateMap[enemy].setStack(EffectStacks.ENEMY_COUNTER_B, len(controller.getTeammates(enemy)) - 1),
                                                controller.applyMultStatBonuses(
                                                    enemy, { BaseStats.MAG: 0.5 + (controller.combatStateMap[enemy].getStack(EffectStacks.ENEMY_COUNTER_B) * 1.5 )})
                                            )),
                                            lambda controller, enemy, _1, _2, _3:
                                                controller.revertMultStatBonuses(
                                                    enemy, { BaseStats.MAG: 0.5 + (controller.combatStateMap[enemy].getStack(EffectStacks.ENEMY_COUNTER_B) * 1.5 )}))
                                    ], 0) 
                                 ], False)
    burstSkillCost = 5
    
    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        currentMana = controller.getCurrentMana(enemy)

        # CD ticks
        for cdKey in ["dashCd", "summonCd", "burstCd"]:
            data[cdKey] -= 1

        allTargets = controller.getTargets(enemy)
        target = controller.getAggroTarget(enemy)
        targetIdx = allTargets.index(target)

        if data["resetBurst"]:
            selectedElement = data["selectedElement"]
            controller.removeResistanceStacks(enemy, selectedElement, 1)
            enemy.basicAttackAttribute = PhysicalAttackAttribute.CRUSHING
            controller.logMessage(MessageType.EFFECT, f"The elementals are blown away by {enemy.name}'s roar!")
            [
                controller.applyDamage(teammate, teammate, controller.getCurrentHealth(teammate))
                    for teammate in controller.getTeammates(enemy) if teammate != enemy
            ]
            data["summonActive"] = False
            data["summonCd"] = 3
            data["aiIdx"] = 0
            data["resetBurst"] = False
            return EnemyAIAction(CombatActions.SKILL, 4, [], None, None)

        # defaults
        if data["aiIdx"] == 0:
            if not data["summonActive"] and data["summonCd"] <= 0:
                summonCost = controller.getSkillManaCost(enemy, summonSkill)
                assert(summonCost is not None)
                if currentMana >= summonCost:
                    data["summonActive"] = True
                    data["burstCd"] = 4
                    selectedElement = random.choice(elementOptions)
                    data["selectedElement"] = selectedElement
                    enemy.basicAttackAttribute = selectedElement
                    controller.addResistanceStacks(enemy, selectedElement, 1)
                    return EnemyAIAction(CombatActions.SKILL, 2, [], None, selectedElement.name)
            
            if data["summonActive"] and data["burstCd"] <= 0:
                burstCost = controller.getSkillManaCostFromValue(enemy, burstSkillCost, True)
                if currentMana >= burstCost:
                    data["aiIdx"] = 1
                    controller.logMessage(MessageType.TELEGRAPH, f"{enemy.name} bristles threateningly!")
                    controller.spendMana(enemy, burstCost)
                    data["aoeTargets"] = allTargets[:]
                    return EnemyAIAction(CombatActions.SKILL, 0, [], None, None)

            if data["dashCd"] <= 0:
                dashCost = controller.getSkillManaCost(enemy, dashSkill)
                assert(dashCost is not None)
                if currentMana >= dashCost:
                    controller.logMessage(MessageType.TELEGRAPH, f"{enemy.name} paws the ground!")
                    data["aiIdx"] = 2
                    return EnemyAIAction(CombatActions.SKILL, 0, [], None, None)
            
            if controller.checkInRange(enemy, target):
                return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
            else:
                distance = controller.checkDistanceStrict(enemy, target) - controller.combatStateMap[enemy].getTotalStatValue(CombatStats.RANGE)
                return EnemyAIAction(CombatActions.APPROACH, None, [targetIdx], min(distance, 2), None)
            
        # burst
        if data["aiIdx"] == 1:
            aoeTargets = data["aoeTargets"]
            target = aoeTargets.pop()
            if len(aoeTargets) == 0:
                # No more targets to fire at after this one
                data["resetBurst"] = True
            return EnemyAIAction(CombatActions.SKILL, 3, [allTargets.index(target)], None, None)
        
        # dash
        if data["aiIdx"] == 2:
            data["aiIdx"] = 0
            data["dashCd"] = 6
            return EnemyAIAction(CombatActions.SKILL, 1, [targetIdx], None, None)
            
        controller.logMessage(MessageType.DEBUG, "<voletyle ai error, should be unreachable>")
        data["aiIdx"] = 0
        return EnemyAIAction(CombatActions.DEFEND, None, [], None, None)
    return Enemy("Voletyle", "Voletyle",
                 "A great enchanted beast, feeding off of the saffron. Recklessly tramples over the elemental spirits it attracts.", 3, {
        BaseStats.HP: 700, BaseStats.MP: 200,
        BaseStats.ATK: 80, BaseStats.DEF: 85, BaseStats.MAG: 70, BaseStats.RES: 85,
        BaseStats.ACC: 110, BaseStats.AVO: 60, BaseStats.SPD: 80
    }, flatStatMods, {
        CombatStats.BASIC_MP_GAIN_MULT: 7 / BASIC_ATTACK_MP_GAIN
    }, 0.5, AttackType.MELEE, PhysicalAttackAttribute.CRUSHING,
    [], [waitSkill("", 0.5), dashSkill, summonSkill, burstSkill, waitSkill("", 1)],
    "A giant rodent crashes through the forest!", "",
    EnemyAI({"aiIdx": 0, "dashCd": 0, "summonCd": 2, "burstCd": 0, "summonActive": False, "selectedElement": None, "resetBurst": False}, decisionFn),
    lambda controller, entity:
        EnemyReward(13, 6, 0, makeBasicUncommonDrop(controller.rng, 0, 1, 1, getWeaponClasses(RANGED_WEAPON_TYPES) + getWeaponClasses(MAGIC_WEAPON_TYPES))
                    if controller._randomRoll(None, entity) <= 0.1 else
                    makeBasicCommonDrop(controller.rng, 6, 9, 1, getWeaponClasses(RANGED_WEAPON_TYPES) + getWeaponClasses(MAGIC_WEAPON_TYPES))))


## Abandoned Storehouse

def asSpawner(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 0 }
    roomNumber = params.get('roomNumber', 0)
    maxVarsRoomMap = {
        BaseStats.HP: [0, 0, 0, 25, 75],
        BaseStats.MP: [0, 0, 0, 5, 20],
        BaseStats.DEF: [0, 0, 0, 20, 50],
        BaseStats.RES: [0, 0, 0, 20, 50],
        BaseStats.SPD: [0, 0, 0, 5, 15]
    }
    maxVars = {
        stat: maxVarsRoomMap[stat][min(roomNumber, len(maxVarsRoomMap[stat])-1)]
        for stat in maxVarsRoomMap
    }
    for stat in maxVars:
        if maxVars[stat] > 0:
            flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])

    summonParams = params.copy()
    summonParams['summoned'] = True
    ratOptions = [ffRat, scRat, sfRat, asMageRat, asStrongRat]
    summonSkill = ActiveBuffSkillData(
        "Rat Release", BasePlayerClassNames.WARRIOR, 0, False, 10, "",
            MAX_ACTION_TIMER, {}, {}, [
                SkillEffect("", [
                    EFImmediate(lambda controller, user, _2, _3: void((
                        controller.spawnNewEntity(controller.rng.choice(ratOptions)(summonParams, controller.rng), True)
                    )))
                ], 0)
            ], None, 0, True, False)
    buffSkill = ActiveBuffSkillData(
        "Rat Rave", BasePlayerClassNames.WARRIOR, 0, False, 15, "",
            MAX_ACTION_TIMER, {}, {}, [
                SkillEffect("", [EFImmediate(
                    lambda controller, enemy, targets, _: void((
                        controller.logMessage(MessageType.EFFECT,
                                              "The opponents are emboldened by the Rat Energy!"),
                        [controller.doHealSkill(enemy, target, 4) for target in targets],
                        [controller.applyMultStatBonuses(target, {
                            BaseStats.ATK: 1.07,
                            BaseStats.DEF: 1.07,
                            BaseStats.MAG: 1.07,
                            BaseStats.RES: 1.07,
                            BaseStats.ACC: 1.07,
                            BaseStats.AVO: 1.07,
                            BaseStats.SPD: 1.07,
                        }) for target in targets]
                )))], 0)
            ], None, 0, False, False)

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        currentMana = controller.getCurrentMana(enemy)
        teammates = controller.getTeammates(enemy)
        teamSize = len(teammates)

        if teamSize < 5:
            summonCost = controller.getSkillManaCost(enemy, summonSkill)
            assert summonCost is not None
            if currentMana >= summonCost:
                return EnemyAIAction(CombatActions.SKILL, 0, [], None, None)
            
        else:
            buffCost = controller.getSkillManaCost(enemy, buffSkill)
            assert buffCost is not None
            if currentMana >= buffCost:
                allAllyIndices = []
                for i in range(len(teammates)):
                    if teammates[i] != enemy:
                        allAllyIndices.append(i)
                return EnemyAIAction(CombatActions.SKILL, 1, allAllyIndices, None, None)
        
        return EnemyAIAction(CombatActions.DEFEND, None, [], None, None)
        
    baseStats = {
        BaseStats.HP: 200, BaseStats.MP: 40,
        BaseStats.ATK: 1, BaseStats.DEF: 100, BaseStats.MAG: 1, BaseStats.RES: 100,
        BaseStats.ACC: 1, BaseStats.AVO: 1, BaseStats.SPD: 25
    }
    return Enemy("Rat's Cradle", "Cradle",
                 "A summoner's tool that's been modified to serve rat-related purposes. It's unclear if the patterns that look like crayon drawings are contributing to this.", 5,
                 baseStats, flatStatMods, {}, 0.5, None, None, [], [summonSkill, buffSkill],
    "Rats surge forth from the strange object!", "",
    EnemyAI({}, decisionFn),
    lambda controller, entity:
        EnemyReward(10, 2, 0, rollEquip(controller, entity, 0.4,
                                       makeBasicCommonDrop(controller.rng, 4, 7, 0.2)))
        if not (params.get('boss', False) or params.get('summoned', False)) else EnemyReward(1, 0, 0, None))

def asMageRat(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 0 }
    roomNumber = params.get('roomNumber', 0)
    maxVarsRoomMap = {
        BaseStats.HP: [0, 0, 20, 40],
        BaseStats.ATK: [0, 0, 5, 15],
        BaseStats.MAG: [0, 0, 5, 15],
        BaseStats.DEF: [0, 0, 10],
        BaseStats.RES: [0, 0, 5, 15],
        BaseStats.ACC: [0, 0, 5, 20],
        BaseStats.AVO: [0, 0, 10, 25],
        BaseStats.SPD: [0, 0, 5, 15]
    }
    maxVars = {
        stat: maxVarsRoomMap[stat][min(roomNumber, len(maxVarsRoomMap[stat])-1)]
        for stat in maxVarsRoomMap
    }
    for stat in maxVars:
        if maxVars[stat] > 0:
            flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])
    
    stackOptions = [EffectStacks.RAT_MARK_IMPETUOUS, EffectStacks.RAT_MARK_RESOLUTE, EffectStacks.RAT_MARK_INTREPID]
    stackBuffs = {
        EffectStacks.CONSUMED_RAT_MARK_IMPETUOUS: (BaseStats.ACC, BaseStats.AVO),
        EffectStacks.CONSUMED_RAT_MARK_RESOLUTE: (BaseStats.DEF, BaseStats.RES),
        EffectStacks.CONSUMED_RAT_MARK_INTREPID: (BaseStats.ATK, BaseStats.SPD)
    }
    attackSkill = AttackSkillData("Lacerate", BasePlayerClassNames.WARRIOR, 0, False, 15, "",
                                  False, AttackType.MAGIC, 1, DEFAULT_ATTACK_TIMER_USAGE, [
                                        SkillEffect("", [EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1}, {}, None, None)], 0),
                                        SkillEffect("", [
                                            EFAfterNextAttack(lambda controller, _1, target, attackResult, _2: void((
                                                controller.logMessage(MessageType.EFFECT, f"{target.name} is marked for other rats!")
                                                    if all([controller.combatStateMap[target].getStack(stack) == 0 for stack in stackOptions]) else None,
                                                controller.combatStateMap[target].addStack(rng.choice(stackOptions), 10),
                                                controller.combatStateMap[target].addStack(rng.choice(stackOptions), 10),
                                            )) if attackResult.attackHit else None)
                                        ], None)
                                  ], False)
    buffSkill = ActiveBuffSkillData("Decorate", BasePlayerClassNames.WARRIOR, 0, False, 15, "",
                                    MAX_ACTION_TIMER / 2, {}, {}, [
                                        SkillEffect("", [
                                            EFImmediate(
                                                lambda controller, user, targets, _: void((
                                                    [[controller.applyMultStatBonuses(target, {
                                                        stat: ratStackBonus ** controller.combatStateMap[user].getStack(stack)
                                                        for stat in stackBuffs[stack]
                                                    }) for stack in stackBuffs if controller.combatStateMap[user].getStack(stack) > 0] for target in targets],
                                                    [controller.combatStateMap[user].setStack(stack, 0) for stack in stackBuffs],
                                                    controller.logMessage(MessageType.EFFECT,
                                                                          f"{user.name} shares its buffs with its teammates!")
                                                ))
                                            )
                                        ], 0)
                                    ], None, 0, False, False)

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        currentMana = controller.getCurrentMana(enemy)
        target = controller.getAggroTarget(enemy)
        targetIdx = controller.getTargets(enemy).index(target)

        totalStacks = sum([controller.combatStateMap[enemy].getStack(stack) for stack in stackBuffs])
        if totalStacks >= data["targetStackCount"]:
            buffCost = controller.getSkillManaCost(enemy, buffSkill)
            assert buffCost is not None
            teammates = controller.getTeammates(enemy)
            if currentMana >= buffCost and len(teammates) > 1:
                data["targetStackCount"] += 1
                allAllyIndices = []
                for i in range(len(teammates)):
                    if teammates[i] != enemy:
                        allAllyIndices.append(i)
                return EnemyAIAction(CombatActions.SKILL, 1, allAllyIndices, None, None)

        attackCost = controller.getSkillManaCost(enemy, attackSkill)
        assert attackCost is not None
        if currentMana >= attackCost:
            return EnemyAIAction(CombatActions.SKILL, 0, [targetIdx], None, None)

        if controller.checkInRange(enemy, target):
            return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
        else:
            distance = controller.checkDistanceStrict(enemy, target) - controller.combatStateMap[enemy].getTotalStatValue(CombatStats.RANGE)
            return EnemyAIAction(CombatActions.APPROACH, None, [targetIdx], min(distance, 2), None)
        
    baseStats = {
        BaseStats.HP: 220, BaseStats.MP: 150,
        BaseStats.ATK: 40, BaseStats.DEF: 55, BaseStats.MAG: 85, BaseStats.RES: 80,
        BaseStats.ACC: 130, BaseStats.AVO: 100, BaseStats.SPD: 75
    }
    return Enemy("Tellerat", "Tellerat",
    "A rat often sought out for its arcane knowledge. Those who have uncovered the art of Cheese Location are held in particularly high regard.", 5,
    baseStats, flatStatMods, {
        CombatStats.BASIC_MP_GAIN_MULT: 10 / BASIC_ATTACK_MP_GAIN
    }, 0.5, None, None, [ratMarkSkill], [attackSkill, buffSkill],
    "\\*squeak squyk\\*", "",
    EnemyAI({"targetStackCount": 2}, decisionFn),
    lambda controller, entity:
        EnemyReward(4, 1, 0, rollEquip(controller, entity, 0.2,
                                       makeBasicCommonDrop(controller.rng, 6, 9, 0.2)))
        if not (params.get('boss', False) or params.get('summoned', False)) else EnemyReward(1, 0, 0, None))

def asStrongRat(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 1 }
    roomNumber = params.get('roomNumber', 0)
    maxVarsRoomMap = {
        BaseStats.HP: [0, 0, 30, 80],
        BaseStats.ATK: [0, 0, 5, 15],
        BaseStats.MAG: [0, 0, 5, 15],
        BaseStats.DEF: [0, 0, 5, 15],
        BaseStats.RES: [0, 0, 10],
        BaseStats.ACC: [0, 0, 5, 20],
        BaseStats.AVO: [0, 0, 10, 25],
        BaseStats.SPD: [0, 0, 5, 20]
    }
    maxVars = {
        stat: maxVarsRoomMap[stat][min(roomNumber, len(maxVarsRoomMap[stat])-1)]
        for stat in maxVarsRoomMap
    }
    for stat in maxVars:
        if maxVars[stat] > 0:
            flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])
    
    stackOptions = [EffectStacks.RAT_MARK_IMPETUOUS, EffectStacks.RAT_MARK_RESOLUTE, EffectStacks.RAT_MARK_INTREPID]
    boostSkill = PassiveSkillData("Wrath", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {}, [
        SkillEffect("", [
            EFBeforeNextAttack(
                {}, {},
                lambda controller, user, target, _2: void((
                    controller.combatStateMap[user].setStack(EffectStacks.ENEMY_COUNTER_A, sum([
                        controller.combatStateMap[target].getStack(stack) for stack in stackOptions
                    ])),
                    controller.applyMultStatBonuses(user, {
                        BaseStats.ATK: 1 + (0.075 * controller.combatStateMap[user].getStack(EffectStacks.ENEMY_COUNTER_A))
                    }),
                    controller.logMessage(
                        MessageType.EFFECT, f"{user.name} is empowered by the hopes of their allies!")
                        if controller.combatStateMap[user].getStack(EffectStacks.ENEMY_COUNTER_A) > 0 else None
                )),
                lambda controller, user, _1, _2, _3: void((
                    controller.revertMultStatBonuses(user, {
                        BaseStats.ATK: 1 + (0.075 * controller.combatStateMap[user].getStack(EffectStacks.ENEMY_COUNTER_A))
                    }),
                    controller.combatStateMap[user].setStack(EffectStacks.ENEMY_COUNTER_A, 0)
                )))
        ], None)
    ], False)

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        target = controller.getAggroTarget(enemy)
        targetIdx = controller.getTargets(enemy).index(target)

        if controller.checkInRange(enemy, target):
            return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
        else:
            distance = controller.checkDistanceStrict(enemy, target) - controller.combatStateMap[enemy].getTotalStatValue(CombatStats.RANGE)
            return EnemyAIAction(CombatActions.APPROACH, None, [targetIdx], min(distance, 2), None)
        
    baseStats = {
        BaseStats.HP: 260, BaseStats.MP: 1,
        BaseStats.ATK: 85, BaseStats.DEF: 85, BaseStats.MAG: 1, BaseStats.RES: 60,
        BaseStats.ACC: 120, BaseStats.AVO: 120, BaseStats.SPD: 80
    }
    return Enemy("Bouncerat", "Bouncerat",
    "An unusually large rat, even for the standards of giant rats. Doesn't act particularly rat-like, but it is readly accepted nonetheless.", 5,
    baseStats, flatStatMods, {}, 0.5, None, None, [boostSkill], [],
    "\\*Squeak.\\*", "",
    EnemyAI({}, decisionFn),
    lambda controller, entity:
        EnemyReward(4, 1, 0, rollEquip(controller, entity, 0.2,
                                       makeBasicCommonDrop(controller.rng, 6, 9, 0.2)))
        if not (params.get('boss', False) or params.get('summoned', False)) else EnemyReward(1, 0, 0, None))


def asSalali(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()
        
    def _thunderAccMult(rangeDelta : int):
        return max(1 - ((rangeDelta ** 1.8) * 0.25), 0.05)
    def thunderApply(controller : CombatController, attacker : CombatEntity, defender: CombatEntity, _):
        originalRange = controller.combatStateMap[defender].getStack(EffectStacks.TELEGRAPH_RANGE) - 1
        assert(originalRange >= 0)

        controller.logMessage(MessageType.EFFECT, f"Lightning arcs towards {defender.name}!")
        rangeDelta = abs(originalRange - controller.checkDistanceStrict(attacker, defender))
        controller.applyMultStatBonuses(attacker, {
            BaseStats.ACC: _thunderAccMult(rangeDelta)
        })
        controller.combatStateMap[defender].setStack(EffectStacks.TELEGRAPH_RANGE, rangeDelta)
    def thunderRevert(controller : CombatController, attacker : CombatEntity, defender : CombatEntity, _1, _2):
        rangeDelta = controller.combatStateMap[defender].getStack(EffectStacks.TELEGRAPH_RANGE)
        controller.revertMultStatBonuses(attacker, {
            BaseStats.ACC: _thunderAccMult(rangeDelta)
        })
        controller.combatStateMap[defender].setStack(EffectStacks.TELEGRAPH_RANGE, 0)

    aimSkill = ActiveBuffSkillData("", BasePlayerClassNames.WARRIOR, 0, False, 30, "",
                                   MAX_ACTION_TIMER, {}, {}, [
                                       SkillEffect("Static Electricity", [
                                           EFImmediate(lambda controller, user, _1, _2: void((
                                               [controller.combatStateMap[target].setStack(
                                                   EffectStacks.TELEGRAPH_RANGE, controller.checkDistanceStrict(user, target)+1)
                                                for target in controller.getTargets(user)],
                                                controller.logMessage(MessageType.TELEGRAPH,
                                                                      "Salali's hair rises as she charges a big attack!")
                                           )))
                                       ], 0)
                                   ], None, 0, True, False)
    thunderSkill = AttackSkillData("Heaven's Flash", BasePlayerClassNames.WARRIOR, 0, False, 0, "",
                                  False, AttackType.MAGIC, 1.5, 0, [
                                      SkillEffect("", [
                                          EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1}, {}, thunderApply, thunderRevert),
                                          EFAfterNextAttack(
                                              lambda controller, user, target, attackResult, _: void(
                                                  controller.applyStatusCondition(
                                                      target, StunStatusEffect(user, target, 1 + (controller.combatStateMap[user].getStack(EffectStacks.ENEMY_PHASE_COUNTER))))
                                              ) if attackResult.attackHit else None
                                          )
                                      ], 0)
                                  ], False)
    
    summonParams = params.copy()
    summonParams['summoned'] = True
    summonSkill = ActiveBuffSkillData(
        "Generator", BasePlayerClassNames.WARRIOR, 0, False, 30, "",
            MAX_ACTION_TIMER * 0.5, {}, {}, [
                SkillEffect("", [
                    EFImmediate(lambda controller, user, _2, _3: void((
                        controller.spawnNewEntity(asSpawner(summonParams, controller.rng), True)
                    )))
                ], 0)
            ], None, 0, True, False)
    
    dashSkill = AttackSkillData("Short Circuit", BasePlayerClassNames.WARRIOR, 0, False, 15, "",
                                  True, AttackType.MELEE, 1, DEFAULT_ATTACK_TIMER_USAGE * 0.1, [
                                      SkillEffect("", [
                                          EFImmediate(
                                                lambda controller, enemy, targets, _: void((
                                                    controller.combatStateMap[enemy].setStack(
                                                        EffectStacks.ENEMY_COUNTER_A,
                                                        controller.combatStateMap[enemy].getStack(EffectStacks.ENEMY_COUNTER_A) + controller.checkDistanceStrict(enemy, targets[0])),
                                                    controller.logMessage(
                                                        MessageType.EFFECT, f"Salali's electic field grows stronger as she dashes towards {targets[0].name}!")
                                                        if controller.checkDistanceStrict(enemy, targets[0]) > 0 else None,
                                                    controller.updateDistance(enemy, targets[0], 0)
                                                ))
                                          ),
                                          EFBeforeNextAttack(
                                              {}, {},
                                              lambda controller, user, _1, _2: controller.applyMultStatBonuses(user, {
                                                  BaseStats.ATK: 1 + ((0.25 if (controller.combatStateMap[user].getStack(EffectStacks.ENEMY_PHASE_COUNTER) == 0) else 0.45)
                                                                      * controller.combatStateMap[user].getStack(EffectStacks.ENEMY_COUNTER_A))
                                              }),
                                              lambda controller, user, _1, _2, _3: controller.revertMultStatBonuses(user, {
                                                  BaseStats.ATK: 1 + ((0.25 if (controller.combatStateMap[user].getStack(EffectStacks.ENEMY_PHASE_COUNTER) == 0) else 0.45)
                                                                      * controller.combatStateMap[user].getStack(EffectStacks.ENEMY_COUNTER_A))
                                              })
                                          )
                                      ], 0, None)
                                  ], False)
    
    phaseThresholds = [1500]
    phaseSkill = PassiveSkillData(
        "Boss Phase HP Lock", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {}, [
            SkillEffect("", [
                EFOnStatsChange(
                    lambda controller, user, _1, newStats, _2: void((
                        (controller.gainHealth(
                            user, phaseThresholds[controller.combatStateMap[user].getStack(EffectStacks.ENEMY_PHASE_COUNTER)] - int(newStats[SpecialStats.CURRENT_HP]),
                                False, True),
                        controller.increaseActionTimer(user, 100))
                            if newStats[SpecialStats.CURRENT_HP] < phaseThresholds[controller.combatStateMap[user].getStack(EffectStacks.ENEMY_PHASE_COUNTER)]
                            else None
                    )) if SpecialStats.CURRENT_HP in newStats and
                        controller.combatStateMap[user].getStack(EffectStacks.ENEMY_PHASE_COUNTER) < len(phaseThresholds) else None
                )
            ], None)
        ], False)
    
    chargeStackPerTurn = 4
    chargeDrainPerTurn = 4
    chargeStackThreshold = 15
    baseAggroDecay = 0.4
    overdriveAggroDecay = 0.1

    overdriveEffect = SkillEffect("Overdrive Voltage", [
        EFOnToggle(
            lambda controller, user, _1, toggled, _2: void((
                controller.applyMultStatBonuses(user, {
                    CombatStats.ACTION_GAUGE_USAGE_MULTIPLIER: 0.15,
                    BaseStats.ATK: 0.85,
                    BaseStats.MAG: 0.85
                }),
                controller.logMessage(MessageType.EFFECT, f"Salali's movements become nearly impossible to track!")
            )) if toggled else void((
                controller.revertMultStatBonuses(user, {
                    CombatStats.ACTION_GAUGE_USAGE_MULTIPLIER: 0.15,
                    BaseStats.ATK: 0.85,
                    BaseStats.MAG: 0.85
                })
            ))
        ), 
        EFStartTurn(
            lambda controller, user, _: controller.applyMultStatBonuses(user, {CombatStats.ACTION_GAUGE_USAGE_MULTIPLIER: 0.1})
        ),
        EFEndTurn(
            lambda controller, user, _1, _2: void((
                controller.revertMultStatBonuses(user, {CombatStats.ACTION_GAUGE_USAGE_MULTIPLIER: 0.1}),
                [controller.combatStateMap[user].removeStack(EffectStacks.SALALI_CHARGE) for i in range(chargeDrainPerTurn)]
            ))
        )
    ], None)
    overdriveSkill = ActiveToggleSkillData(
        "Overdrive Voltage", BasePlayerClassNames.WARRIOR, 0, False, 0, "",
        MAX_ACTION_TIMER * 0.1, {}, {}, [overdriveEffect], 0, 0, True, False)
    
    voltageSkill = PassiveSkillData(
        "Rising Voltage", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {}, [
            SkillEffect("", [
                EFEndTurn(
                    lambda controller, user, _1, _2: None if controller.combatStateMap[user].getStack(EffectStacks.ENEMY_PHASE_COUNTER) == 0 else
                    void((
                        [controller.combatStateMap[user].addStack(EffectStacks.SALALI_CHARGE, None) for i in range(chargeStackPerTurn)]
                    )) if overdriveEffect not in controller.combatStateMap[user].activeSkillEffects else None
                ),
                EFWhenAttacked(
                    lambda controller, user, _1, attackResult, _2: None if controller.combatStateMap[user].getStack(EffectStacks.ENEMY_PHASE_COUNTER) == 0 else
                    void((
                        controller.combatStateMap[user].removeStack(EffectStacks.SALALI_CHARGE)
                    )) if attackResult.attackHit else None
                )
            ], None)
        ], False)
    
    warningTaunts = [
        "Hey, hey, you still awake?",
        "Hey, hey, bet you can't hit me!",
        "Hey, hey, wanna see something even cooler?"
    ]
    successTaunts = [
        "Slowpoke, slowpoke! Try it like this!",
        "Too bad, too bad! That's just the difference in our potential!"
    ]
    failureTaunts = [
        "R-rude, so rude! Stop interrupting me!",
        "Ow, ow! I-I let you get that one!"
    ]
    tauntAttackSkill = AttackSkillData(
        "Lightspeed Charge 「Power Law」", BasePlayerClassNames.WARRIOR, 0, False, 75, "",
        True, AttackType.MELEE, 4, DEFAULT_ATTACK_TIMER_USAGE, [
            SkillEffect("", [EFBeforeNextAttack({CombatStats.RANGE: 2}, {}, None, None)], 0),
            SkillEffect("", [
                EFAfterNextAttack(lambda controller, _1, target, attackResult, _2: void((
                    [controller.combatStateMap[target].addStack(EffectStacks.SALALI_CHARGE, None) for i in range(8)]
                )))
            ], None)
        ], False)
    tauntAttackerCheck = PassiveSkillData(
        "Resistors", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {}, [
            SkillEffect("", [
                EFWhenAttacked(
                    lambda controller, _1, attacker, attackResult, _2: void((
                        controller.combatStateMap[attacker].setStack(EffectStacks.TELEGRAPH_ATTACK, 1)
                    )) if attackResult.attackHit else None
                )
            ], None)
        ], False)

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        phaseCheck = phaseCheckFn(controller, enemy, data)
        if phaseCheck is not None:
            return phaseCheck

        phaseIndex = controller.combatStateMap[enemy].getStack(EffectStacks.ENEMY_PHASE_COUNTER)
        chargeStacks = controller.combatStateMap[enemy].getStack(EffectStacks.SALALI_CHARGE)
        target = controller.getAggroTarget(enemy)
        allTargets = controller.getTargets(enemy)
        targetIdx = allTargets.index(target)
        currentMana = controller.getCurrentMana(enemy)

        if phaseIndex == 1:
            if not data["overdriveActive"] and chargeStacks >= chargeStackThreshold:
                data["overdriveActive"] = True
                data["tauntCd"] += 2
                enemy.aggroDecayFactor = overdriveAggroDecay
                return EnemyAIAction(CombatActions.SKILL, 6, [], None, None)
            
            if data["overdriveActive"] and chargeStacks <= 0:
                data["overdriveActive"] = False
                enemy.aggroDecayFactor = baseAggroDecay
                return EnemyAIAction(CombatActions.SKILL, 6, [], None, None)

        if data["aiIdx"] == 0:
            # CD ticks
            for cdKey in ["summonCd", "thunderCd", "dashCd", "tauntCd"]:
                data[cdKey] -= 1

            # check for stunned opponent
            if data["tauntCd"] < 5 and phaseIndex == 1:
                for checkTarget in controller.getTargets(enemy):
                    if StatusConditionNames.STUN in controller.combatStateMap[checkTarget].currentStatusEffects:
                        target = checkTarget
                        data["rangeCd"] = 0
                        break

            if data["thunderCd"] <= 0:
                thunderCost = controller.getSkillManaCost(enemy, aimSkill)
                assert thunderCost is not None
                if currentMana >= thunderCost:
                    data["aoeTargets"] = allTargets[:]
                    data["aiIdx"] = 1
                    return EnemyAIAction(CombatActions.SKILL, 3, [], None, None)
            if data["tauntCd"] <= 0 and phaseIndex == 1:
                tauntCost = controller.getSkillManaCost(enemy, tauntAttackSkill)
                assert tauntCost is not None
                if currentMana >= tauntCost and controller.checkDistanceStrict(enemy, target) <= 1:
                    data["tauntTarget"] = target
                    data["aiIdx"] = 3
                    controller.logMessage(MessageType.TELEGRAPH, f"Salali taunts {target.name}!")
                    controller.logMessage(MessageType.DIALOGUE, f"Salali: \"{rng.choice(warningTaunts)}\"")
                    controller.combatStateMap[target].setStack(EffectStacks.TELEGRAPH_ATTACK, 0)
                    return EnemyAIAction(CombatActions.SKILL, 7, [], None, None)
            if data["dashCd"] <= 0:
                totalDashCost = controller.getSkillManaCost(enemy, dashSkill)
                assert totalDashCost is not None
                totalDashCost *=  len(allTargets)
                if currentMana >= totalDashCost:
                    controller.logMessage(MessageType.TELEGRAPH, f"Salali stretches as static electricity builds around her!")
                    data["dashTargets"] = allTargets[:]
                    data["aiIdx"] = 2
                    controller.combatStateMap[enemy].setStack(EffectStacks.ENEMY_COUNTER_A, 0)
                    return EnemyAIAction(CombatActions.SKILL, 1, [], None, None)
            if data["summonCd"] <= 0 and phaseIndex == 0:
                summonCost = controller.getSkillManaCost(enemy, summonSkill)
                assert summonCost is not None
                if len(controller.getTeammates(enemy)) < 4 and currentMana >= summonCost:
                    data["summonCd"] = 12
                    return EnemyAIAction(CombatActions.SKILL, 2, [], None, None)
                
            if controller.checkInRange(enemy, target):
                return EnemyAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
            else:
                distance = controller.checkDistanceStrict(enemy, target) - controller.combatStateMap[enemy].getTotalStatValue(CombatStats.RANGE)
                return EnemyAIAction(CombatActions.APPROACH, None, [targetIdx], min(distance, 2), None)
                
        if data["aiIdx"] == 1: # Thunder
            aoeTargets = []
            if phaseIndex == 1:
                aoeTargets = data["aoeTargets"]
                target = aoeTargets.pop()

            if len(aoeTargets) == 0:
                # No more targets to fire at after this one
                controller.spendActionTimer(enemy, DEFAULT_ATTACK_TIMER_USAGE)
                data["thunderCd"] = 7
                data["aiIdx"] = 0
            elif phaseIndex == 1:
                # refund/tax on charges until AOE done
                if data["overdriveActive"]:
                    controller.combatStateMap[enemy].setStack(EffectStacks.SALALI_CHARGE, chargeStacks + chargeDrainPerTurn)
                else:
                    controller.combatStateMap[enemy].setStack(EffectStacks.SALALI_CHARGE, chargeStacks - chargeStackPerTurn)
            return EnemyAIAction(CombatActions.SKILL, 4, [allTargets.index(target)], None, None)
        
        if data["aiIdx"] == 2: # Dash
            dashCost = controller.getSkillManaCost(enemy, dashSkill)
            assert dashCost is not None
            dashTargets = [target for target in data["dashTargets"]
                           if controller.getCurrentHealth(target) > 0]
            if len(dashTargets) > 0 and currentMana > dashCost:
                closestTargets = []
                closestTargetDistance = MAX_DISTANCE
                for checkTarget in dashTargets:
                    checkDistance = controller.checkDistanceStrict(enemy, checkTarget)
                    if checkDistance == closestTargetDistance:
                        closestTargets.append(checkTarget)
                    elif checkDistance < closestTargetDistance:
                        closestTargetDistance = checkDistance
                        closestTargets = [checkTarget]

                target = max(closestTargets, key=lambda target: controller.combatStateMap[enemy].aggroMap.get(target, 0))
                dashTargets.remove(target)
                data["dashTargets"] = dashTargets
                        
                if phaseIndex == 1:
                    # partial refund/tax on charges for lower action time
                    if data["overdriveActive"]:
                        controller.combatStateMap[enemy].setStack(EffectStacks.SALALI_CHARGE, chargeStacks + (chargeDrainPerTurn // 3))
                    else:
                        controller.combatStateMap[enemy].setStack(EffectStacks.SALALI_CHARGE, chargeStacks - chargeStackPerTurn)

                return EnemyAIAction(CombatActions.SKILL, 5, [allTargets.index(target)], None, None)
            else:
                # No more targets or mana
                data["dashCd"] = 7
                data["aiIdx"] = 0
                if phaseIndex == 0:
                    controller.logMessage(MessageType.EFFECT, "Salali comes to a stop as her static field dissipates!")
                else:
                    controller.logMessage(MessageType.EFFECT, "Salali comes to a stop as she absorbs the energy from her static field!")
                    totalMovement = controller.combatStateMap[enemy].getStack(EffectStacks.ENEMY_COUNTER_A)
                    controller.combatStateMap[enemy].setStack(EffectStacks.SALALI_CHARGE, chargeStacks + (totalMovement // 2))
                return EnemyAIAction(CombatActions.SKILL, 1, [], None, None)
        
        if data["aiIdx"] == 3: # Taunt
            target = data["tauntTarget"]
            data["aiIdx"] = 0
            data["tauntCd"] = 10
            targetAttacked = controller.combatStateMap[target].getStack(EffectStacks.TELEGRAPH_ATTACK) == 1
            if targetAttacked:
                controller.logMessage(MessageType.EFFECT, f"Salali's attack was disrupted!")
                controller.logMessage(MessageType.DIALOGUE, f"Salali: \"{rng.choice(failureTaunts)}\"")
                controller.combatStateMap[enemy].setStack(EffectStacks.SALALI_CHARGE, max(chargeStacks - chargeStackPerTurn, 0))
                return EnemyAIAction(CombatActions.SKILL, 7, [], None, None)
            else:
                controller.logMessage(MessageType.DIALOGUE, f"Salali: \"{rng.choice(successTaunts)}\"")
                return EnemyAIAction(CombatActions.SKILL, 8, [allTargets.index(target)], None, None)
        
        controller.logMessage(MessageType.DEBUG, "<salali ai error, should be unreachable>")
        data["aiIdx"] = 0
        return EnemyAIAction(CombatActions.DEFEND, None, [], None, None)
    def phaseCheckFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction | None:
        phaseIndex = controller.combatStateMap[enemy].getStack(EffectStacks.ENEMY_PHASE_COUNTER)
        if phaseIndex < len(phaseThresholds) and controller.getCurrentHealth(enemy) <= phaseThresholds[phaseIndex]:
            phaseIndex += 1
            controller.combatStateMap[enemy].setStack(EffectStacks.ENEMY_PHASE_COUNTER, phaseIndex)
            controller.combatStateMap[enemy].phaseReset(controller, set([EffectStacks.ENEMY_PHASE_COUNTER]))
            if phaseIndex == 1:
                thunderSkill.skillName = "Charge Sign 「Kite-Chasing Spear」"
                dashSkill.skillName = "Charge Sign 「Path of Least Resistance」"
                enemy.baseStats.update({
                    BaseStats.ATK: 125, BaseStats.DEF: 105, BaseStats.MAG: 125, BaseStats.RES: 105,
                    BaseStats.ACC: 200, BaseStats.AVO: 215, BaseStats.SPD: 145
                })
                enemy.name = "Salali, The Supercharged Sciuridae"
                controller.logMessage(MessageType.DIALOGUE,
                                      "Salali: \"Hey, hey, you're kinda fun after all! You won't mind if I go a bit further, right, right?\"\n" +
                                      "__**Salali activates her *Charge Signature*!**__\n" +
                                      "Electrical energy crackles around her as she starts bouncing even faster!")
                data["aiIdx"] = 0
                data["thunderCd"] = 4
                data["dashCd"] = 0
                data["tauntCd"] = 4
                data["overdriveActive"] = False
                return EnemyAIAction(CombatActions.SKILL, 0, [], None, None)
        
    baseStats = {
        BaseStats.HP: 3000, BaseStats.MP: 1000,
        BaseStats.ATK: 100, BaseStats.DEF: 90, BaseStats.MAG: 100, BaseStats.RES: 90,
        BaseStats.ACC: 150, BaseStats.AVO: 175, BaseStats.SPD: 110
    }
    return Enemy("Salali", "Salali",
    "A squirrel-person with far too much energy. Seems like the type to be distracted easily, but it feels as though you're standing in for someone else she spends all her time talking to.",
    8, baseStats, {
        CombatStats.RANGE: 0
    }, {
        CombatStats.BASIC_MP_GAIN_MULT: 10 / BASIC_ATTACK_MP_GAIN,
        CombatStats.REPOSITION_ACTION_TIME_MULT: 0.7
    }, baseAggroDecay, AttackType.MELEE, MagicalAttackAttribute.WIND, [
        resistanceEffect(MagicalAttackAttribute.WIND, 2),
        phaseSkill,
        voltageSkill,
        tauntAttackerCheck
    ], [waitSkill("", 0.3), waitSkill("", 0.5), summonSkill, aimSkill, thunderSkill, dashSkill,
        overdriveSkill, waitSkill("", 1.5), tauntAttackSkill],
    lambda players:
        "Salali: \"Hey, hey! I don't see anyone else coming down here often! Aren't these guys cool? " +
        "Aren't these cradle thingies *cool* cool? They're super super fun, I found them around--\"\n" +
        "Salali: \"...Huh, huh? I'm not a rat! Even if you're just here to mess things up, you don't have to be so rude about it!\""
            if all([Milestones.ABANDONED_STOREHOUSE_COMPLETE not in player.milestones for player in players]) else
        "Salali: \"Hey, hey! You're back again? Looking for a rematch, aren't you, aren't you?\"\n" +
        "Salali: \"...Wait, wait, the cradles keep making rats even if I don't do anything, remember? " +
        "That means it's not my fault, yup yup! Even if I keep playing with them!\"",
    lambda players:
        "Salali: \"Fine, fine, I give up! Hmph, bet you wouldn't stand a chance if Riri were here...\"\n" +
        "Salali: \"...but really, I have no idea how these cradle thingies work. It'd be mean to keep all the rats locked up in here, right, right? " +
        "But I'll do my best to keep an eye on it, I guess.\""
            if all([Milestones.ABANDONED_STOREHOUSE_COMPLETE not in player.milestones for player in players]) else
        "Salali: \"Fine, fine, I give up!\"\n" +
        "Salali: \"...Hey, hey, you're not trying to avoid me when I'm with Riri, are you? " +
        "I can't use my full power alone, so this still doesn't count, doesn't count~\"",
    EnemyAI({"aiIdx": 0, "summonCd": 0, "thunderCd": 3, "dashCd": 8, "tauntCd": 10}, decisionFn),
    lambda controller, entity:
        EnemyReward(20, 10, 1, makeBasicUncommonDrop(controller.rng, 3, 6, 0.25)))