from __future__ import annotations
from typing import Callable
import random

from gameData.rpg_item_data import *
from structures.rpg_classes_skills import ActiveBuffSkillData, ActiveSkillDataSelector, AttackSkillData, CounterSkillData, EFAfterNextAttack, EFBeforeAllyAttacked, EFBeforeNextAttack, EFEndTurn, EFImmediate, EFStartTurn, EFWhenAttacked, EffectFunctionResult, SkillEffect
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
    "Aqi: \"All warmed up now? Just gotta test you before sendin' you out!\"",
    "Aqi: \"Your form's lookin' good! Remember to check your class n' skills before tryin' the real thing!\"",
    EnemyAI({"aiIdx": 0, "target": None}, decisionFn),
    lambda _1, _2: EnemyReward(1, 0, 0, None))

## Shared Rat Skill

ratMarkSkill = PassiveSkillData("Ravenous Rats", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {}, [SkillEffect("", [
    EFAfterNextAttack(lambda controller, attacker, target, attackResult, _2: void((
        (
            controller.combatStateMap[target].removeStack(EffectStacks.RAT_MARK_IMPETUOUS),
            controller.applyMultStatBonuses(attacker, {
                BaseStats.ACC: 1.05,
                BaseStats.AVO: 1.05
            }),
            controller.logMessage(MessageType.EFFECT, f"{attacker.name}'s ACC and AVO are increased by the mark!")
        ) if controller.combatStateMap[target].getStack(EffectStacks.RAT_MARK_IMPETUOUS) > 0 else None,
        (
            controller.combatStateMap[target].removeStack(EffectStacks.RAT_MARK_RESOLUTE),
            controller.applyMultStatBonuses(attacker, {
                BaseStats.DEF: 1.05,
                BaseStats.RES: 1.05
            }),
            controller.logMessage(MessageType.EFFECT, f"{attacker.name}'s DEF and RES are increased by the mark!")
        ) if controller.combatStateMap[target].getStack(EffectStacks.RAT_MARK_RESOLUTE) > 0 else None,
        (
            controller.combatStateMap[target].removeStack(EffectStacks.RAT_MARK_INTREPID),
            controller.applyMultStatBonuses(attacker, {
                BaseStats.ATK: 1.05,
                BaseStats.SPD: 1.05
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
                                       makeBasicCommonDrop(controller.rng, 0, 2, 0))))

def ffRat(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 0 }
    roomNumber = params.get('roomNumber', 0)
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
    return Enemy("Roverat", "Roverat",
                 "A field rat. Despite its size, it seeks to defy the constraints of rules.", 2, {
        BaseStats.HP: 80, BaseStats.MP: 1,
        BaseStats.ATK: 20, BaseStats.DEF: 20, BaseStats.MAG: 1, BaseStats.RES: 25,
        BaseStats.ACC: 60, BaseStats.AVO: 75, BaseStats.SPD: 50
    }, flatStatMods, {}, 0.5, None, None, [ratMarkSkill, impetuousRatSkill], [],
    "\\*squeak squek\\*", "",
    EnemyAI({}, decisionFn),
    lambda controller, entity:
        EnemyReward(2, 0, 0, rollEquip(controller, entity, 0.2,
                                       makeBasicCommonDrop(controller.rng, 0, 2, 0))))

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
                                       makeBasicCommonDrop(controller.rng, 1, 4, 0))))


def ffSlimeBoss(params : dict) -> Enemy:
    def _slimeCannonAccMult(rangeDelta : int):
        return max(1 - ((rangeDelta ** 2) * 0.225), 0.05)
    def slimeCannonApply(controller : CombatController, attacker : CombatEntity, defender: CombatEntity):
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
        EnemyReward(6, 3, 0, rollEquip(controller, entity, 1,
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
                                                  lambda controller, attacker, _: controller.applyMultStatBonuses(
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
        EnemyReward(6, 2, 0, rollEquip(controller, entity, 1,
                                       makeBasicUncommonDrop(controller.rng, 0, 1, 0.5)
                                            if controller._randomRoll(None, entity) <= 0.1 else
                                       makeBasicCommonDrop(controller.rng, 6, 8, 0.5))))

## Skylight Cave

def scRat(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 0 }
    roomNumber = params.get('roomNumber', 0)
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
    return Enemy("Spelunkerat", "Spelunkerat",
                 "A cave rat. It lives for treasure, both the friendship sort and the actual-monetary-value kind.", 3, {
        BaseStats.HP: 140, BaseStats.MP: 1,
        BaseStats.ATK: 40, BaseStats.DEF: 30, BaseStats.MAG: 1, BaseStats.RES: 35,
        BaseStats.ACC: 80, BaseStats.AVO: 90, BaseStats.SPD: 75
    }, flatStatMods, {}, 0.5,None, None, [ratMarkSkill, resoluteRatSkill], [],
    "\\*squeak squok\\*", "",
    EnemyAI({}, decisionFn),
    lambda controller, entity:
        EnemyReward(3, 0, 0, rollEquip(controller, entity, 0.2,
                                       makeBasicCommonDrop(controller.rng, 2, 5, 0))))

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
                                       makeBasicCommonDrop(controller.rng, 3, 6, 0.25, getWeaponClasses(MELEE_WEAPON_TYPES)))))

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
                                       makeBasicCommonDrop(controller.rng, 3, 6, 0.25, getWeaponClasses(MELEE_WEAPON_TYPES)))))


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
                                       makeBasicCommonDrop(controller.rng, 3, 6, 0.25, getWeaponClasses(MELEE_WEAPON_TYPES)))))


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
                                              lambda controller, user, _: controller.applyMultStatBonuses(
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
                lambda controller, user, _: controller.applyMultStatBonuses(user, {CombatStats.ACTION_GAUGE_USAGE_MULTIPLIER: 0.6})
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
        EnemyReward(5, 4, 0, makeBasicUncommonDrop(controller.rng, 0, 1, 1, getWeaponClasses(MELEE_WEAPON_TYPES))
                    if controller._randomRoll(None, entity) <= 0.1 else
                    makeBasicCommonDrop(controller.rng, 6, 9, 1, getWeaponClasses(MELEE_WEAPON_TYPES))))

## Saffron Forest

def sfRat(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 0 }
    roomNumber = params.get('roomNumber', 0)
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

    resoluteRatSkill = PassiveSkillData("Mark of Intrepid Rat", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {}, [SkillEffect("", [
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
    return Enemy("Gatherat", "Gatherat",
                 "A forest rat. Its hunger for battle is surpassed only by its hunger for food, but it's not particularly close.", 3, {
        BaseStats.HP: 140, BaseStats.MP: 1,
        BaseStats.ATK: 40, BaseStats.DEF: 30, BaseStats.MAG: 1, BaseStats.RES: 35,
        BaseStats.ACC: 80, BaseStats.AVO: 90, BaseStats.SPD: 75
    }, flatStatMods, {}, 0.5,None, None, [ratMarkSkill, resoluteRatSkill], [],
    "\\*squeak squak\\*", "",
    EnemyAI({}, decisionFn),
    lambda controller, entity:
        EnemyReward(3, 0, 0, rollEquip(controller, entity, 0.2,
                                       makeBasicCommonDrop(controller.rng, 2, 5, 0))))