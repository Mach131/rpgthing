from __future__ import annotations
from typing import Callable
import random

from gameData.rpg_item_data import makeBasicCommonDrop
from structures.rpg_classes_skills import ActiveBuffSkillData, AttackSkillData, EFAfterNextAttack, EFBeforeNextAttack, EFImmediate, EffectFunctionResult, SkillEffect
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
                                SkillEffect([EFImmediate(
                                    lambda controller, user, _1, _2: controller.addWeaknessStacks(user, attribute, stacks))], None)
                            ], False)

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
    }, {}, {}, 0, [], [waitSkill("", 1)],
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
    }, {}, {}, 0, [], [waitSkill("", 1)],
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
                                            {BaseStats.ATK: 50/650, BaseStats.DEF: 18/500, BaseStats.RES: 18/500,
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
    }, 0, [], [waitSkill("", 1), waitSkill("", 1.2), attackSkill],
    "Aqi: \"All warmed up now? Just gotta test you before sendin' you out!\"",
    "Your form's lookin' good! Remember to check your class n' skills before tryin' the real thing!",
    EnemyAI({"aiIdx": 0, "target": None}, decisionFn),
    lambda _1, _2: EnemyReward(1, 0, 0, None))


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
    }, flatStatMods, {}, 0.5, [], [],
    "The slime lets out a 'blurble'.", "",
    EnemyAI({}, decisionFn),
    lambda controller, entity:
        EnemyReward(2, 0, 0, rollEquip(controller, entity, 0.2,
                                       makeBasicCommonDrop(controller.rng, 0, 2, False))))

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
    }, flatStatMods, {}, 0.5, [], [],
    "\\*squeak squek\\*", "",
    EnemyAI({}, decisionFn),
    lambda controller, entity:
        EnemyReward(2, 0, 0, rollEquip(controller, entity, 0.2,
                                       makeBasicCommonDrop(controller.rng, 0, 2, False))))

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
                                      SkillEffect([EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1}, {}, None, None)], 0)
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
    }, flatStatMods, {}, 0.65, [
        weaknessEffect(MagicalAttackAttribute.FIRE, 1),
        weaknessEffect(MagicalAttackAttribute.ICE, 1),
        weaknessEffect(MagicalAttackAttribute.WIND, 1)
    ], [attackSkill],
    "", "",
    EnemyAI({}, decisionFn),
    lambda controller, entity:
        EnemyReward(3, 1 if controller._randomRoll(None, entity) <= 0.35 else 0,
                    0, rollEquip(controller, entity, 0.2,
                                       makeBasicCommonDrop(controller.rng, 1, 4, False))))


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
                                       SkillEffect([
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
                                      SkillEffect([EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1}, {},
                                                                      slimeCannonApply, slimeCannonRevert)], 0)
                                  ], False)
    slamSkill = AttackSkillData("Slime Slam!", BasePlayerClassNames.WARRIOR, 0, False, 15, "",
                                  True, AttackType.MELEE, 2, 0, [], False)
    splitSkill = ActiveBuffSkillData("Slime Division!", BasePlayerClassNames.WARRIOR, 0, False, 20, "",
                                   MAX_ACTION_TIMER, {}, {}, [
                                       SkillEffect([
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
                slamCost = controller.getSkillManaCost(enemy, slamSkill)
                assert slamCost is not None
                if proximityCheck and currentMana >= slamCost:
                    controller.logMessage(MessageType.TELEGRAPH, f"Slimoo prepares for a big leap!")
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
    }, 0.5, [], [waitSkill("", 0.4), aimSkill, cannonSkill, slamSkill, splitSkill],
    "The large slime roars a noble 'blurble'!", "",
    EnemyAI({"aiIdx": 0, "cannonCd": 0, "slamCd": 2, "splitCd": 2}, decisionFn),
    lambda controller, entity:
        EnemyReward(5, 3, 0, rollEquip(controller, entity, 1,
                                       makeBasicCommonDrop(controller.rng, 5, 8, True))))


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
                                          SkillEffect([
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
                                      SkillEffect([EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1}, {}, None, None)], 0)
                                  ], False)
    healSkill = ActiveBuffSkillData("Gardening", BasePlayerClassNames.WARRIOR, 0, False, 30, "",
                                     DEFAULT_ATTACK_TIMER_USAGE * 0.75, {}, {}, [
                                         SkillEffect([EFImmediate(
                                             lambda controller, enemy, targets, _: void((
                                                 controller.applyDamage(enemy, enemy, min(50, controller.getCurrentHealth(enemy))),
                                                 [controller.doHealSkill(enemy, target, 0.5) for target in targets],
                                                 [controller.gainMana(target, 30) for target in targets]
                                         )))], 0)
                                     ], None, 0, False, False)
    swingSkill = AttackSkillData("Thorny Thrash", BasePlayerClassNames.WARRIOR, 0, False, 30, "",
                                  True, AttackType.MELEE, 1, DEFAULT_ATTACK_TIMER_USAGE, [
                                      SkillEffect([EFAfterNextAttack(thrashKnockbackFn)], 0)
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
    }, 0.5, [
        vengeanceSkill,
        weaknessEffect(MagicalAttackAttribute.FIRE, 1),
        weaknessEffect(MagicalAttackAttribute.ICE, 1),
        weaknessEffect(MagicalAttackAttribute.WIND, 1)
    ], [shootSkill, healSkill, swingSkill],
    "The flower unit prepares to mobilize!", "",
    EnemyAI({"aiIdx": 0, "gardenCd": 2, "swingCd": 0}, decisionFn),
    lambda controller, entity:
        EnemyReward(5, 2, 0, rollEquip(controller, entity, 1,
                                       makeBasicCommonDrop(controller.rng, 6, 8, True))))