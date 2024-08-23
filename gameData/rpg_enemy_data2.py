from __future__ import annotations
from typing import Any, Callable
import random

from gameData.rpg_enemy_data_common import *

## Training Courtyard

def damageTestDummy(params : dict, rng : random.Random | None = None) -> Enemy:
    dummyLevel = params.get("level", 5)
    dummyDef = params.get("def", 50)
    dummyRes = params.get("res", 50)
    dummyAvo = params.get("avo", 50)
    dummyTurns = params.get("turns", 10)
    dummySpd = params.get("spd", 25)

    def timeTrackerFn(controller : CombatController, user, time : float):
        user.ai.data["time"] += time
    initializerSkill = PassiveSkillData("Commence", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {}, [
        SkillEffect("", [
            EFOnAdvanceTurn(
                lambda controller, user, previousPlayer, _1, time, _2: void((
                    controller.combatStateMap[user].setStack(EffectStacks.ENEMY_COUNTER_A, 1) ,
                    controller.increaseActionTimer(user, 1)
                ) if previousPlayer != user else None) if controller.combatStateMap[user].getStack(EffectStacks.ENEMY_COUNTER_A) == 0 else void((
                    timeTrackerFn(controller, user, time)
                ))
            )
        ], None)
    ], False)

    def damageTrackerFn(controller : CombatController, attacker : CombatEntity, target, damage : int):
        target.ai.data["damageMap"][attacker] = target.ai.data["damageMap"].get(attacker, 0) + damage
        controller.gainHealth(target, damage, silent=True)
    trackingSkill = PassiveSkillData("Analyze", BasePlayerClassNames.WARRIOR, 0, False, "", {}, {}, [
        SkillEffect("", [
            EFWhenAttacked(
                lambda controller, user, attacker, attackResult, _: damageTrackerFn(controller, attacker, user, attackResult.damageDealt)
                    if user != attacker else None
            )
        ], None)
    ], False)

    def dotTrackerFn(controller : CombatController, attacker : CombatEntity, target, damage : int):
        target.ai.data["dotMap"][attacker] = target.ai.data["dotMap"].get(attacker, 0) + damage
        controller.gainHealth(target, damage, silent=True)
    dotTrackerEffect = SkillEffect("", [
        EFOnOpponentDotDamage(
            lambda controller, user, target, damage, _: dotTrackerFn(controller, user, target, damage)
        )
    ], None)

    
    def getAnalysisMessage(time : float, damageMap : dict[CombatEntity, int], dotMap : dict[CombatEntity, int]) -> str:
        totalDamage = 0
        attackerStrings = {}
        attackerTotalDamage = {}
        dummyTime = time * ACTION_TIME_DISPLAY_MULTIPLIER
        
        for attacker in damageMap:
            totalDamage += damageMap[attacker]
            attackerTotalDamage[attacker] = damageMap[attacker]
        for attacker in dotMap:
            totalDamage += dotMap[attacker]
            attackerTotalDamage[attacker] = attackerTotalDamage.get(attacker, 0) + dotMap[attacker]

        for attacker in attackerTotalDamage:
            attackerStrings[attacker] = f"{attacker.shortName}: {attackerTotalDamage[attacker]} Total Damage "
            if attacker in dotMap:
                attackerStrings[attacker] += f"({dotMap[attacker]} from DOT) "
            attackerStrings[attacker] += f"| {attackerTotalDamage[attacker] / dummyTime:.2f} per Time Unit"
        
        settingString = f'{dummyTime:.3f} Time Unit Analysis ({dummyTurns} Turns | Level {dummyLevel} | {dummyDef} DEF | {dummyRes} RES | {dummyAvo} AVO | {dummySpd} SPD)'
        overallDamageString = f'Total Damage: {totalDamage} | {totalDamage / dummyTime:.2f} per Time Unit'
        fullAttackerString = '\n'.join(attackerStrings.values())
        return f'---\n{settingString}\n{overallDamageString}\n{fullAttackerString}\n---'
    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EntityAIAction:
        if not data["started"]:
            if controller.combatStateMap[enemy].getStack(EffectStacks.ENEMY_COUNTER_A) == 0:
                controller.logMessage(MessageType.DIALOGUE, "The training dummy is chilling.")
            else:
                for target in controller.getTargets(enemy):
                    controller.addSkillEffect(target, dotTrackerEffect)
                controller.logMessage(MessageType.DIALOGUE, "The training dummy begins its analysis.")
                data["started"] = True

        else:
            data["turns"] += 1
            if data["turns"] >= dummyTurns:
                controller.logMessage(MessageType.DIALOGUE, "The training dummy completes its analysis.")
                controller.logMessage(MessageType.BASIC, getAnalysisMessage(data["time"], data["damageMap"], data["dotMap"]))
                controller.applyDamage(enemy, enemy, controller.getMaxHealth(enemy), silent=True)
            else:
                controller.logMessage(MessageType.DIALOGUE, f"Analysis completion: {data['turns'] * 100 / dummyTurns:.1f}%.")

        return EntityAIAction(CombatActions.SKILL, 0, [], None, None)
    return Enemy("Damage Test Dummy", "Dummy",
                 "An extremely high-tech straw training dummy.", dummyLevel, {
        BaseStats.HP: 999999, BaseStats.MP: 1,
        BaseStats.ATK: 1, BaseStats.DEF: dummyDef, BaseStats.MAG: 1, BaseStats.RES: dummyRes,
        BaseStats.ACC: 1, BaseStats.AVO: dummyAvo, BaseStats.SPD: dummySpd
    }, {}, {}, 0, None, None, [
        initializerSkill, trackingSkill
    ], 
    [waitSkill("", 1)],
    f"You see a note on the training dummy...\n\"Use this to test out your damage and skills! You have {dummyTurns} of the dummy's turns, starting after your first turn.\"", "",
    EntityAI({"started": False, "time": 0, "turns": 0, "damageMap": {}, "dotMap": {}}, decisionFn),
    lambda _1, _2: EnemyReward(1, 0, 0, None))



## Arena I

def arenaMercenary(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 1 }
    roomNumber = params.get('roomNumber', 0)
    maxVarsRoomMap = {
        BaseStats.HP: [0, 30, 30, 70, 150],
        BaseStats.MP: [0, 10, 10, 20, 40],
        BaseStats.ATK: [0, 10, 10, 20, 50],
        BaseStats.DEF: [0, 5, 5, 15, 30],
        BaseStats.RES: [0, 5, 5, 15, 30],
        BaseStats.ACC: [0, 10, 10, 20, 40],
        BaseStats.AVO: [0, 5, 5, 10, 20],
        BaseStats.SPD: [0, 5, 5, 15, 30]
    }
    maxVars = {
        stat: maxVarsRoomMap[stat][min(roomNumber, len(maxVarsRoomMap[stat])-1)]
        for stat in maxVarsRoomMap
    }
    for stat in maxVars:
        if maxVars[stat] > 0:
            flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])
    adjective = "Rookie"
    adverb = ""
    if roomNumber >= 2:
        adjective = rng.choice(DESCRIPTIVE_ADJECTIVES)
    if roomNumber >= 4:
        adverb = rng.choice(DESCRIPTIVE_ADVERBS) + " "
    teamCall = "" if roomNumber < 4 else f"A particularly {adjective.lower()} team approaches!"

    warriorSkills = PlayerClassData.PLAYER_CLASS_DATA_MAP[BasePlayerClassNames.WARRIOR].rankSkills
    mercenarySkills = PlayerClassData.PLAYER_CLASS_DATA_MAP[AdvancedPlayerClassNames.MERCENARY].rankSkills

    swingSkill = warriorSkills[2]
    enduranceSkill = warriorSkills[3]
    sweepSkill = mercenarySkills[2]
    frenzySkill = mercenarySkills[4]
    berserkSkill = mercenarySkills[5]

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EntityAIAction:
        target = controller.getAggroTarget(enemy)
        targetIdx = controller.getTargets(enemy).index(target)
        currentMana = controller.getCurrentMana(enemy)

        if not data["berserkActive"]:
            hpFraction = controller.getCurrentHealth(enemy) / controller.getMaxHealth(enemy)
            berserkCost = controller.getSkillManaCost(enemy, berserkSkill)
            assert berserkCost is not None
            if hpFraction < 0.5 and currentMana >= berserkCost:
                data["berserkActive"] = True
                return EntityAIAction(CombatActions.SKILL, 2, [], None, None)

        if controller.checkInRange(enemy, target):
            timesHitTarget = data["attackCounts"].get(target, 0)

            if timesHitTarget == 1:
                sweepCost = controller.getSkillManaCost(enemy, sweepSkill)
                assert sweepCost is not None
                targetHealthRatio = controller.getCurrentHealth(target) / controller.getMaxHealth(target)
                if currentMana >= sweepCost and targetHealthRatio >= 0.4:
                    data["attackCounts"][target] = 2
                    return EntityAIAction(CombatActions.SKILL, 1, [targetIdx], None, None)

            elif timesHitTarget >= 2:
                swingCost = controller.getSkillManaCost(enemy, swingSkill)
                assert swingCost is not None
                if currentMana >= swingCost:
                    return EntityAIAction(CombatActions.SKILL, 0, [targetIdx], None, None)

            data["attackCounts"][target] = max(timesHitTarget, 1)
            return EntityAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
        else:
            distance = controller.checkDistanceStrict(enemy, target) - controller.combatStateMap[enemy].getTotalStatValue(CombatStats.RANGE)
            return EntityAIAction(CombatActions.APPROACH, None, [targetIdx], min(distance, 2), None)
        
    baseStats = {
        BaseStats.HP: 350, BaseStats.MP: 30,
        BaseStats.ATK: 150, BaseStats.DEF: 30, BaseStats.MAG: 30, BaseStats.RES: 30,
        BaseStats.ACC: 160, BaseStats.AVO: 60, BaseStats.SPD: 100
    }
    return Enemy(f"{adverb}{adjective} Mercenary", "Mercenary",
    "A sword-wielding fellow adventurer. They have one job, and they're fairly good at it.", 6,
    baseStats, flatStatMods, {}, 0.5, AttackType.MELEE, PhysicalAttackAttribute.SLASHING,
    [ enduranceSkill, frenzySkill ],
    [ swingSkill, sweepSkill, berserkSkill ],
    teamCall, "",
    EntityAI({ "attackCounts": {}, "berserkActive": False}, decisionFn),
    lambda controller, entity:
        EnemyReward(6, 0, 0, None))


def arenaKnight(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 0 }
    roomNumber = params.get('roomNumber', 0)
    maxVarsRoomMap = {
        BaseStats.HP: [0, 50, 50, 100, 300],
        BaseStats.MP: [0, 10, 10, 20, 40],
        BaseStats.ATK: [0, 5, 5, 15, 30],
        BaseStats.DEF: [0, 10, 10, 20, 40],
        BaseStats.RES: [0, 10, 10, 20, 40],
        BaseStats.ACC: [0, 5, 5, 10, 20],
        BaseStats.AVO: [0, 5, 5, 10, 15],
        BaseStats.SPD: [0, 5, 5, 10, 15]
    }
    maxVars = {
        stat: maxVarsRoomMap[stat][min(roomNumber, len(maxVarsRoomMap[stat])-1)]
        for stat in maxVarsRoomMap
    }
    for stat in maxVars:
        if maxVars[stat] > 0:
            flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])
    adjective = "Rookie"
    adverb = ""
    if roomNumber >= 2:
        adjective = rng.choice(DESCRIPTIVE_ADJECTIVES)
    if roomNumber >= 4:
        adverb = rng.choice(DESCRIPTIVE_ADVERBS) + " "
    teamCall = "" if roomNumber < 4 else f"A particularly {adjective.lower()} team approaches!"

    warriorSkills = PlayerClassData.PLAYER_CLASS_DATA_MAP[BasePlayerClassNames.WARRIOR].rankSkills
    knightSkills = PlayerClassData.PLAYER_CLASS_DATA_MAP[AdvancedPlayerClassNames.KNIGHT].rankSkills

    swingSkill = warriorSkills[2]
    enduranceSkill = warriorSkills[3]
    challengeSkill = knightSkills[2]
    chivalrySkill = knightSkills[3]
    parrySkill = knightSkills[5] # use clearParryType on next turn

    exChallengeSkill = AttackSkillData("Challenge EX", AdvancedPlayerClassNames.KNIGHT, 2, False, 0, "",
        True, AttackType.MELEE, 2.5, DEFAULT_ATTACK_TIMER_USAGE, [SkillEffect("", [EFBeforeNextAttack({}, {CombatStats.AGGRO_MULT: 3}, None, None)], 0)], False)
    
    def challengeCheckFn(controller : CombatController, user, attacker : CombatEntity, attackResult : AttackResultInfo):
        if user.ai.data["challengeTarget"] == attacker:
            controller.combatStateMap[user].setStack(EffectStacks.ENEMY_COUNTER_A, 0)
        if attackResult.attackHit:
            hitType, hitCount = user.ai.data["takenHitHistory"]
            if hitType != attackResult.attackType :
                hitType = attackResult.attackType
            else:
                hitCount += 1
            user.ai.data["takenHitHistory"] = (hitType, hitCount)
    challengeCheck = PassiveSkillData("Please Respond", AdvancedPlayerClassNames.KNIGHT, 2, False, "", {}, {}, [
        SkillEffect("", [
            EFImmediate(
                lambda controller, user, _1, _2: void([
                    controller.addSkillEffect(ally, getAggroShareEffect(user))
                    for ally in controller.getTeammates(user)
                ])
            ),
            EFWhenAttacked(
                lambda controller, user, attacker, attackResult, _: void((
                    challengeCheckFn(controller, user, attacker, attackResult)
                ))
            )
        ], None)
    ], False)

    def getAggroShareEffect(source : CombatEntity):
        return SkillEffect("", [
            EFWhenAttacked(
                lambda controller, user, attacker, attackResult, _: void((
                    controller._applyAggro(attacker, source, attackResult.damageDealt * 0.25)
                )) if controller.getCurrentHealth(source) > 0 else None
            )], None)

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EntityAIAction:
        target = controller.getAggroTarget(enemy) if data["challengeTarget"] is None else data["challengeTarget"]
        targetIdx = controller.getTargets(enemy).index(target)
        currentMana = controller.getCurrentMana(enemy)

        if controller.combatStateMap[enemy].activeParrySkillEffect is not None:
            controller.logMessage(MessageType.EFFECT, f"{enemy.shortName} gives up on the parry attempt.")
            controller.combatStateMap[enemy].clearParryType()

        for cdKey in ["challengeCd"]:
            data[cdKey] -= 1

        if controller.checkInRange(enemy, target):
            if data["challengeTarget"] is not None:
                data["challengeCd"] = 4
                challengeTarget = data["challengeTarget"]
                data["challengeTarget"] = None
                exChallengeCost = controller.getSkillManaCost(enemy, exChallengeSkill)
                assert exChallengeCost is not None
                if currentMana >= exChallengeCost and controller.combatStateMap[enemy].getStack(EffectStacks.ENEMY_COUNTER_A) > 0:
                    controller.logMessage(
                        MessageType.DIALOGUE, f"{enemy.shortName} is annoyed that {challengeTarget.shortName} ignored their Challenge!")
                    return EntityAIAction(CombatActions.SKILL, 3, [targetIdx], None, None)

            elif data["challengeCd"] <= 0:
                challengeCost = controller.getSkillManaCost(enemy, challengeSkill)
                assert challengeCost is not None
                if currentMana >= challengeCost:
                    data["challengeTarget"] = target
                    controller.combatStateMap[enemy].setStack(EffectStacks.ENEMY_COUNTER_A, 1)
                    return EntityAIAction(CombatActions.SKILL, 1, [targetIdx], None, None)
                
            if data["takenHitHistory"][1] > 7:
                parryCost = controller.getSkillManaCost(enemy, parrySkill)
                assert parryCost is not None
                if currentMana > parryCost:
                    parryType : AttackType = data["takenHitHistory"][0]
                    assert parryType is not None
                    data["takenHitHistory"] = (None, 0)
                    return EntityAIAction(CombatActions.SKILL, 2, [], None, parryType.name)

            return EntityAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
        else:
            distance = controller.checkDistanceStrict(enemy, target) - controller.combatStateMap[enemy].getTotalStatValue(CombatStats.RANGE)
            return EntityAIAction(CombatActions.APPROACH, None, [targetIdx], min(distance, 2), None)
        
    baseStats = {
        BaseStats.HP: 700, BaseStats.MP: 40,
        BaseStats.ATK: 90, BaseStats.DEF: 120, BaseStats.MAG: 30, BaseStats.RES: 50,
        BaseStats.ACC: 130, BaseStats.AVO: 60, BaseStats.SPD: 70
    }
    return Enemy(f"{adverb}{adjective} Knight", "Knight",
    "A shield-bearing fellow adventurer. They've been trying to get better at asserting themselves.", 6,
    baseStats, flatStatMods, {}, 0.5, AttackType.MELEE, PhysicalAttackAttribute.SLASHING,
    [ enduranceSkill, chivalrySkill, challengeCheck ],
    [ swingSkill, challengeSkill, parrySkill, exChallengeSkill ],
    teamCall, "",
    EntityAI({ "challengeCd": 2, "challengeTarget": None, "takenHitHistory": (None, 0) }, decisionFn),
    lambda controller, entity:
        EnemyReward(6, 0, 0, None))


def arenaSniper(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 3 }
    roomNumber = params.get('roomNumber', 0)
    maxVarsRoomMap = {
        BaseStats.HP: [0, 30, 30, 70, 150],
        BaseStats.MP: [0, 10, 10, 20, 40],
        BaseStats.ATK: [0, 5, 5, 15, 30],
        BaseStats.DEF: [0, 5, 5, 10, 20],
        BaseStats.RES: [0, 5, 5, 10, 20],
        BaseStats.ACC: [0, 10, 10, 20, 40],
        BaseStats.AVO: [0, 5, 5, 15, 30],
        BaseStats.SPD: [0, 5, 5, 15, 30]
    }
    maxVars = {
        stat: maxVarsRoomMap[stat][min(roomNumber, len(maxVarsRoomMap[stat])-1)]
        for stat in maxVarsRoomMap
    }
    for stat in maxVars:
        if maxVars[stat] > 0:
            flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])
    adjective = "Rookie"
    adverb = ""
    if roomNumber >= 2:
        adjective = rng.choice(DESCRIPTIVE_ADJECTIVES)
    if roomNumber >= 4:
        adverb = rng.choice(DESCRIPTIVE_ADVERBS) + " "
    teamCall = "" if roomNumber < 4 else f"A particularly {adjective.lower()} team approaches!"

    rangerSkills = PlayerClassData.PLAYER_CLASS_DATA_MAP[BasePlayerClassNames.RANGER].rankSkills
    sniperSkills = PlayerClassData.PLAYER_CLASS_DATA_MAP[AdvancedPlayerClassNames.SNIPER].rankSkills

    strafeSkill = rangerSkills[2]
    eyeSkill = rangerSkills[3]
    steadySkill = sniperSkills[3]
    suppressiveSkill = sniperSkills[4]
    perfectSkill = sniperSkills[5]

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EntityAIAction:
        target = controller.getAggroTarget(enemy)
        if data["perfectTarget"] is not None:
            target = data["perfectTarget"]
        targetIdx = controller.getTargets(enemy).index(target)
        currentMana = controller.getCurrentMana(enemy)

        distanceToTarget = controller.checkDistanceStrict(enemy, target)
        
        for cdKey in ["perfectCd"]:
            data[cdKey] -= 1

        if data["perfectCd"] <= 0:
            needStrafe = distanceToTarget < 3 and not data["didStrafe"]

            # MP check
            strafeCost = controller.getSkillManaCost(enemy, strafeSkill)
            perfectCost = controller.getSkillManaCost(enemy, perfectSkill)
            assert strafeCost is not None
            assert perfectCost is not None
            comboCost = strafeCost + perfectCost if needStrafe else perfectCost
            if currentMana >= comboCost:
                if needStrafe:
                    data["didStrafe"] = True
                    data["perfectTarget"] = target
                    return EntityAIAction(CombatActions.SKILL, 0, [targetIdx], None, None)
                else:
                    data["didStrafe"] = False
                    data["perfectTarget"] = None
                    data["perfectCd"] = 4
                    return EntityAIAction(CombatActions.SKILL, 1, [targetIdx], None, None)

        elif distanceToTarget < 1:
            return EntityAIAction(CombatActions.RETREAT, None, [targetIdx], min(3 - distanceToTarget, 2), None)
        
        return EntityAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
        
    baseStats = {
        BaseStats.HP: 250, BaseStats.MP: 50,
        BaseStats.ATK: 110, BaseStats.DEF: 60, BaseStats.MAG: 30, BaseStats.RES: 60,
        BaseStats.ACC: 180, BaseStats.AVO: 90, BaseStats.SPD: 110
    }
    return Enemy(f"{adverb}{adjective} Sniper", "Sniper",
    "A gun-wielding fellow adventurer. They act as if they'd prefer not to be noticed.", 6,
    baseStats, flatStatMods, {}, 0.5, AttackType.RANGED, PhysicalAttackAttribute.PIERCING,
    [ eyeSkill, steadySkill, suppressiveSkill ],
    [ strafeSkill, perfectSkill ],
    teamCall, "",
    EntityAI({ "perfectCd": 2, "didStrafe": False, "perfectTarget": None }, decisionFn),
    lambda controller, entity:
        EnemyReward(6, 0, 0, None))


def arenaHunter(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 3 }
    roomNumber = params.get('roomNumber', 0)
    maxVarsRoomMap = {
        BaseStats.HP: [0, 30, 30, 70, 150],
        BaseStats.MP: [0, 15, 15, 30, 60],
        BaseStats.ATK: [0, 5, 5, 15, 30],
        BaseStats.DEF: [0, 5, 5, 10, 20],
        BaseStats.RES: [0, 5, 5, 10, 20],
        BaseStats.ACC: [0, 10, 10, 20, 30],
        BaseStats.AVO: [0, 5, 5, 10, 20],
        BaseStats.SPD: [0, 5, 5, 10, 20]
    }
    maxVars = {
        stat: maxVarsRoomMap[stat][min(roomNumber, len(maxVarsRoomMap[stat])-1)]
        for stat in maxVarsRoomMap
    }
    for stat in maxVars:
        if maxVars[stat] > 0:
            flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])
    adjective = "Rookie"
    adverb = ""
    if roomNumber >= 2:
        adjective = rng.choice(DESCRIPTIVE_ADJECTIVES)
    if roomNumber >= 4:
        adverb = rng.choice(DESCRIPTIVE_ADVERBS) + " "
    teamCall = "" if roomNumber < 4 else f"A particularly {adjective.lower()} team approaches!"

    rangerSkills = PlayerClassData.PLAYER_CLASS_DATA_MAP[BasePlayerClassNames.RANGER].rankSkills
    hunterSkills = PlayerClassData.PLAYER_CLASS_DATA_MAP[AdvancedPlayerClassNames.HUNTER].rankSkills

    strafeSkill = rangerSkills[2]
    eyeSkill = rangerSkills[3]
    lacedSkill = hunterSkills[2]

    def coveredTracksFn(controller : CombatController, user : CombatEntity, target : CombatEntity, userMoved : bool,
                        oldDistance : int, newDistance : int, effectResult : EffectFunctionResult):
        if not userMoved and newDistance < oldDistance:
            counterData = CounterSkillData(True, None, 0.7,
                                        [SkillEffect("", [
                                            EFBeforeNextAttack({CombatStats.IGNORE_RANGE_CHECK: 1}, {}, None, None),
                                            EFAfterNextAttack(lambda controller, user, target, attackResult, _: void(
                            controller.applyStatusCondition(target, ExhaustionStatusEffect(user, target, 3, 1.3)) if attackResult.attackHit else None))
                                            ], 0)])
            effectResult.setBonusAttack(user, target, counterData)
    tracksSkill = ActiveBuffSkillData(
        "Briefly Covered Tracks", AdvancedPlayerClassNames.HUNTER, 4, False, 20, "",
        MAX_ACTION_TIMER * 0.5, {}, {}, [SkillEffect("Covered Tracks", [EFOnDistanceChange(coveredTracksFn)], 4)],
        0, 0, False, False)
    
    def stunAggroUpdateFn(controller : CombatController, user : CombatEntity, target : CombatEntity):
        if len(controller.getTeammates(user)) > 1:
            allyAggroGain = controller.combatStateMap[user].aggroMap.get(target, 0) * 0.5
            for ally in controller.getTeammates(user):
                if ally != user:
                    controller.combatStateMap[ally].aggroMap[target] = controller.combatStateMap[ally].aggroMap.get(target, 0) + allyAggroGain
            controller.combatStateMap[user].aggroMap[target] = 0
            controller.logMessage(MessageType.EFFECT, f"{user.shortName} calls out the stunned target!")
    stunSkill = PassiveSkillData(
        "Clean Em Up", AdvancedPlayerClassNames.HUNTER, 5, False, "", {}, {}, [
            SkillEffect("", [
                EFOnStatusApplied(
                    lambda controller, user, target, status, _: stunAggroUpdateFn(controller, user, target)
                        if status == StatusConditionNames.STUN else None
                )
            ], None)
        ], False
    )

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EntityAIAction:
        target = controller.getAggroTarget(enemy)
        targetIdx = controller.getTargets(enemy).index(target)
        currentMana = controller.getCurrentMana(enemy)

        distanceToTarget = controller.checkDistanceStrict(enemy, target)
        
        for cdKey in ["lacedCd", "tracksCd"]:
            data[cdKey] -= 1

        if data["tracksCd"] <= 0:
            targetRange = controller.combatStateMap[target].getTotalStatValue(CombatStats.RANGE)
            needStrafe = targetRange < 3 and controller.checkInRange(target, enemy) and not data["didStrafe"]

            # MP check
            strafeCost = controller.getSkillManaCost(enemy, strafeSkill)
            tracksCost = controller.getSkillManaCost(enemy, tracksSkill)
            assert strafeCost is not None
            assert tracksCost is not None
            comboCost = strafeCost + tracksCost if needStrafe else tracksCost
            if currentMana >= comboCost:
                if needStrafe:
                    data["didStrafe"] = True
                    return EntityAIAction(CombatActions.SKILL, 0, [targetIdx], None, None)
                else:
                    data["didStrafe"] = False
                    data["tracksCd"] = 8
                    return EntityAIAction(CombatActions.SKILL, 2, [], None, None)
        
        if data["lacedCd"] <= 0 or len(controller.combatStateMap[target].currentStatusEffects) == 0:
            lacedCost = controller.getSkillManaCost(enemy, lacedSkill)
            assert lacedCost is not None
            if currentMana >= lacedCost:
                data["lacedCd"] = 4
                return EntityAIAction(CombatActions.SKILL, 1, [targetIdx], None, rng.choice(["POISON", "BLIND", "STUN"]))

        minDistance = 2 if tracksSkill.skillEffects[0] in controller.combatStateMap[enemy].activeSkillEffects else 1
        if distanceToTarget < minDistance:
            return EntityAIAction(CombatActions.RETREAT, None, [targetIdx], min(3 - distanceToTarget, 2), None)
        
        return EntityAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
    baseStats = {
        BaseStats.HP: 300, BaseStats.MP: 70,
        BaseStats.ATK: 80, BaseStats.DEF: 70, BaseStats.MAG: 30, BaseStats.RES: 70,
        BaseStats.ACC: 170, BaseStats.AVO: 80, BaseStats.SPD: 80
    }
    return Enemy(f"{adverb}{adjective} Hunter", "Hunter",
    "A crossbow-wielding fellow adventurer. Doesn't care about winning so much as making other people lose.", 6,
    baseStats, flatStatMods, {}, 0.5, AttackType.RANGED, PhysicalAttackAttribute.PIERCING,
    [ eyeSkill, stunSkill ],
    [ strafeSkill, lacedSkill, tracksSkill ],
    teamCall, "",
    EntityAI({ "lacedCd": 2, "tracksCd": 2, "didStrafe": False }, decisionFn),
    lambda controller, entity:
        EnemyReward(6, 0, 0, None))


def arenaAssassin(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 0 }
    roomNumber = params.get('roomNumber', 0)
    maxVarsRoomMap = {
        BaseStats.HP: [0, 25, 25, 50, 100],
        BaseStats.MP: [0, 10, 10, 20, 40],
        BaseStats.ATK: [0, 5, 5, 15, 30],
        BaseStats.DEF: [0, 5, 5, 10, 20],
        BaseStats.RES: [0, 5, 5, 10, 20],
        BaseStats.ACC: [0, 10, 10, 20, 30],
        BaseStats.AVO: [0, 10, 10, 20, 40],
        BaseStats.SPD: [0, 15, 15, 25, 50]
    }
    maxVars = {
        stat: maxVarsRoomMap[stat][min(roomNumber, len(maxVarsRoomMap[stat])-1)]
        for stat in maxVarsRoomMap
    }
    for stat in maxVars:
        if maxVars[stat] > 0:
            flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])
    adjective = "Rookie"
    adverb = ""
    if roomNumber >= 2:
        adjective = rng.choice(DESCRIPTIVE_ADJECTIVES)
    if roomNumber >= 4:
        adverb = rng.choice(DESCRIPTIVE_ADVERBS) + " "
    teamCall = "" if roomNumber < 4 else f"A particularly {adjective.lower()} team approaches!"

    rogueSkills = PlayerClassData.PLAYER_CLASS_DATA_MAP[BasePlayerClassNames.ROGUE].rankSkills
    assassinSkills = PlayerClassData.PLAYER_CLASS_DATA_MAP[AdvancedPlayerClassNames.ASSASSIN].rankSkills

    swiftSkill = rogueSkills[2]
    illusionSkill = rogueSkills[3]
    shadowingSkill = assassinSkills[2]
    eyesSkill = assassinSkills[4]
    ambushSkill = assassinSkills[5]

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EntityAIAction:
        target = controller.getAggroTarget(enemy)
        targetIdx = controller.getTargets(enemy).index(target)
        currentMana = controller.getCurrentMana(enemy)

        for cdKey in ["shadowingCd", "swiftCd"]:
            data[cdKey] -= 1

        lowHealth = controller.getCurrentHealth(enemy) <= controller.getMaxHealth(enemy) * 0.4

        if not data["didCallout"] and controller.checkDistanceStrict(enemy, target) < 3:
            if lowHealth and len(controller.getTeammates(enemy)) > 1:
                data["didCallout"] = True
                allyAggroGain = controller.combatStateMap[enemy].aggroMap.get(target, 0) * 0.8
                controller.combatStateMap[enemy].aggroMap[target] = 0
                for ally in controller.getTeammates(enemy):
                    controller.combatStateMap[ally].aggroMap[target] = controller.combatStateMap[ally].aggroMap.get(target, 0) + allyAggroGain
                controller.logMessage(MessageType.EFFECT, f"{enemy.shortName} signals their allies for assistance!")
                return EntityAIAction(CombatActions.RETREAT, None, [targetIdx], min(3 - controller.checkDistanceStrict(enemy, target), 2), None)

        shadowingCost = controller.getSkillManaCost(enemy, shadowingSkill)
        swiftCost = controller.getSkillManaCost(enemy, swiftSkill)
        ambushCost = controller.getSkillManaCost(enemy, ambushSkill)
        assert shadowingCost is not None
        assert swiftCost is not None
        assert ambushCost is not None

        targetStacks = controller.combatStateMap[target].getStack(EffectStacks.EYES_OF_THE_DARK)
        wantAmbush = targetStacks >= 5


        if controller.checkInRange(enemy, target):
            if data["swiftCd"] <= 0 and currentMana >= swiftCost + ambushCost:
                data["swiftCd"] = 3
                return EntityAIAction(CombatActions.SKILL, 0, [targetIdx], None, None)
            
            if wantAmbush and currentMana >= ambushCost:
                ambushMode = "EXECUTE"
                if not lowHealth:
                    targetLowHealth = controller.getCurrentHealth(target) <= controller.getMaxHealth(target) * 0.4
                    if targetLowHealth and not data["didInterrogate"]:
                        data["didInterrogate"] = True
                        ambushMode = "INTERROGATE"
                    elif not targetLowHealth and target not in data["disabledSet"]:
                        data["disabledSet"].add(target)
                        ambushMode = "DISABLE"
                return EntityAIAction(CombatActions.SKILL, 2, [targetIdx], None, ambushMode)

            return EntityAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
        else:
            if data["shadowingCd"] <= 0 and currentMana >= shadowingCost + ambushCost:
                data["shadowingCd"] = 3
                return EntityAIAction(CombatActions.SKILL, 1, [targetIdx], None, None)

            distance = controller.checkDistanceStrict(enemy, target) - controller.combatStateMap[enemy].getTotalStatValue(CombatStats.RANGE)
            return EntityAIAction(CombatActions.APPROACH, None, [targetIdx], min(distance, 2), None)
        
    baseStats = {
        BaseStats.HP: 200, BaseStats.MP: 70,
        BaseStats.ATK: 100, BaseStats.DEF: 30, BaseStats.MAG: 30, BaseStats.RES: 30,
        BaseStats.ACC: 120, BaseStats.AVO: 150, BaseStats.SPD: 160
    }
    return Enemy(f"{adverb}{adjective} Assassin", "Assassin",
    "A dagger-wielding fellow adventurer. The type to hold on to a grudge.", 6,
    baseStats, flatStatMods, {}, 0.9, AttackType.MELEE, PhysicalAttackAttribute.SLASHING,
    [ illusionSkill, eyesSkill ],
    [ swiftSkill, shadowingSkill, ambushSkill ],
    teamCall, "",
    EntityAI({ "shadowingCd": 0, "swiftCd": 2, "didCallout": False, "didInterrogate": False, "disabledSet": set() }, decisionFn),
    lambda controller, entity:
        EnemyReward(6, 0, 0, None))


def arenaAcrobat(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 1 }
    roomNumber = params.get('roomNumber', 0)
    maxVarsRoomMap = {
        BaseStats.HP: [0, 30, 30, 70, 150],
        BaseStats.MP: [0, 10, 10, 20, 40],
        BaseStats.ATK: [0, 5, 5, 15, 30],
        BaseStats.DEF: [0, 5, 5, 10, 20],
        BaseStats.RES: [0, 5, 5, 10, 20],
        BaseStats.ACC: [0, 10, 10, 20, 30],
        BaseStats.AVO: [0, 15, 15, 25, 50],
        BaseStats.SPD: [0, 5, 5, 15, 30]
    }
    maxVars = {
        stat: maxVarsRoomMap[stat][min(roomNumber, len(maxVarsRoomMap[stat])-1)]
        for stat in maxVarsRoomMap
    }
    for stat in maxVars:
        if maxVars[stat] > 0:
            flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])
    adjective = "Rookie"
    adverb = ""
    if roomNumber >= 2:
        adjective = rng.choice(DESCRIPTIVE_ADJECTIVES)
    if roomNumber >= 4:
        adverb = rng.choice(DESCRIPTIVE_ADVERBS) + " "
    teamCall = "" if roomNumber < 4 else f"A particularly {adjective.lower()} team approaches!"

    rogueSkills = PlayerClassData.PLAYER_CLASS_DATA_MAP[BasePlayerClassNames.ROGUE].rankSkills
    acrobatSkills = PlayerClassData.PLAYER_CLASS_DATA_MAP[AdvancedPlayerClassNames.ACROBAT].rankSkills

    swiftSkill = rogueSkills[2]
    illusionSkill = rogueSkills[3]
    bedazzleSkill = acrobatSkills[2]
    wakeSkill = acrobatSkills[4]
    sidestepSkill = acrobatSkills[5]

    def hitHistoryFn(controller : CombatController, user, attacker : CombatEntity, attackResult : AttackResultInfo):
        if attackResult.inRange:
            hitType, hitCount = user.ai.data["takenHitHistory"]
            if hitType != attackResult.attackType:
                hitType = attackResult.attackType
            else:
                hitCount += 1
            user.ai.data["takenHitHistory"] = (hitType, hitCount)
    aggroSkill = PassiveSkillData("I'll Help", AdvancedPlayerClassNames.ACROBAT, 2, False, "", {}, {}, [
        SkillEffect("", [
            EFImmediate(
                lambda controller, user, _1, _2: void([
                    controller.addSkillEffect(ally, getAggroShareEffect(user))
                    for ally in controller.getTeammates(user)
                ])
            ),
            EFWhenAttacked(
                lambda controller, user, attacker, attackResult, _: void((
                    hitHistoryFn(controller, user, attacker, attackResult)
                ))
            )
        ], None)
    ], False)
    def getAggroShareEffect(source : CombatEntity):
        return SkillEffect("", [
            EFWhenAttacked(
                lambda controller, user, attacker, attackResult, _: void((
                    controller._applyAggro(attacker, source, attackResult.damageDealt * 0.25)
                )) if controller.getCurrentHealth(source) > 0 else None
            )], None)
    

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EntityAIAction:
        target = controller.getAggroTarget(enemy)
        targetIdx = controller.getTargets(enemy).index(target)
        currentMana = controller.getCurrentMana(enemy)

        if controller.combatStateMap[enemy].activeParrySkillEffect is not None:
            if data["sidestepTurns"] > 1:
                controller.logMessage(MessageType.EFFECT, f"{enemy.shortName} gives up on the sidestep attempt.")
                controller.combatStateMap[enemy].clearParryType()
            else:
                data["sidestepTurns"] += 1

        for cdKey in ["bedazzleCd", "swiftCd"]:
            data[cdKey] -= 1

        if controller.checkInRange(enemy, target):
            sidestepCost = controller.getSkillManaCost(enemy, sidestepSkill)
            assert sidestepCost is not None
            reservedCost = 0 if data["takenHitHistory"][1] < 3 else sidestepCost

            if data["bedazzleCd"] <= 0:
                bedazzleCost = controller.getSkillManaCost(enemy, bedazzleSkill)
                assert bedazzleCost is not None
                if currentMana >= bedazzleCost + reservedCost and StatusConditionNames.BLIND not in controller.combatStateMap[target].currentStatusEffects:
                    data["bedazzleCd"] = 3
                    return EntityAIAction(CombatActions.SKILL, 1, [targetIdx], None, None)
                
            if data["swiftCd"] <= 0:
                swiftCost = controller.getSkillManaCost(enemy, swiftSkill)
                assert swiftCost is not None
                if currentMana >= swiftCost + reservedCost:
                    data["swiftCd"] = 4
                    return EntityAIAction(CombatActions.SKILL, 0, [targetIdx], None, None)
                
            if data["takenHitHistory"][1] > 5:
                if currentMana > sidestepCost:
                    parryType : AttackType = data["takenHitHistory"][0]
                    assert parryType is not None
                    data["takenHitHistory"] = (None, 0)
                    data["sidestepTurns"] = 0
                    return EntityAIAction(CombatActions.SKILL, 2, [], None, parryType.name)

            return EntityAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
        else:
            distance = controller.checkDistanceStrict(enemy, target) - controller.combatStateMap[enemy].getTotalStatValue(CombatStats.RANGE)
            return EntityAIAction(CombatActions.APPROACH, None, [targetIdx], min(distance, 2), None)
        
    baseStats = {
        BaseStats.HP: 200, BaseStats.MP: 50,
        BaseStats.ATK: 95, BaseStats.DEF: 30, BaseStats.MAG: 30, BaseStats.RES: 30,
        BaseStats.ACC: 130, BaseStats.AVO: 200, BaseStats.SPD: 130
    }
    return Enemy(f"{adverb}{adjective} Acrobat", "Acrobat",
    "A naginata-bearing fellow adventurer. Unclear if they're aware of the tournament, but they seem to be having fun.", 6,
    baseStats, flatStatMods, {}, 0.5, AttackType.MELEE, PhysicalAttackAttribute.PIERCING,
    [ illusionSkill, aggroSkill, wakeSkill ],
    [ swiftSkill, bedazzleSkill, sidestepSkill ],
    teamCall, "",
    EntityAI({ "swiftCd": 3, "bedazzleCd": 2, "takenHitHistory": (None, 0), "sidestepTurns": 0 }, decisionFn),
    lambda controller, entity:
        EnemyReward(6, 0, 0, None))


def _findBlessingTarget(controller : CombatController, enemy : CombatEntity, rng : random.Random, attackerPrio : bool):
    if len(controller.combatStateMap[enemy].activeEnchantments) == 0 and attackerPrio:
        return enemy
    
    availableAllies = [ally for ally in controller.getTeammates(enemy)
                        if len(controller.combatStateMap[ally].activeEnchantments) == 0]
    if len(availableAllies) == 0:
        return None
    
    attackers = [ally for ally in availableAllies
                    if any([attackerClass in ally.name for attackerClass in ["Mercenary", "Sniper", "Assassin", "Wizard"]])]
    defenders = [ally for ally in availableAllies
                    if any([defenderClass in ally.name for defenderClass in ["Knight", "Acrobat"]])]
    
    checkOrder = [attackers, defenders] if attackerPrio else [defenders, attackers]
    for allySet in checkOrder:
        if len(allySet) > 0:
            return rng.choice(allySet)
    
    return rng.choice(availableAllies)
    
def arenaWizard(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 0 }
    roomNumber = params.get('roomNumber', 0)
    maxVarsRoomMap = {
        BaseStats.HP: [0, 30, 30, 70, 150],
        BaseStats.MP: [0, 15, 15, 25, 50],
        BaseStats.MAG: [0, 10, 10, 20, 50],
        BaseStats.DEF: [0, 5, 5, 10, 20],
        BaseStats.RES: [0, 5, 5, 15, 30],
        BaseStats.ACC: [0, 10, 10, 20, 40],
        BaseStats.AVO: [0, 5, 5, 10, 20],
        BaseStats.SPD: [0, 5, 5, 15, 30]
    }
    maxVars = {
        stat: maxVarsRoomMap[stat][min(roomNumber, len(maxVarsRoomMap[stat])-1)]
        for stat in maxVarsRoomMap
    }
    for stat in maxVars:
        if maxVars[stat] > 0:
            flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])
    adjective = "Rookie"
    adverb = ""
    if roomNumber >= 2:
        adjective = rng.choice(DESCRIPTIVE_ADJECTIVES)
    if roomNumber >= 4:
        adverb = rng.choice(DESCRIPTIVE_ADVERBS) + " "
    teamCall = "" if roomNumber < 4 else f"A particularly {adjective.lower()} team approaches!"

    mageSkills = PlayerClassData.PLAYER_CLASS_DATA_MAP[BasePlayerClassNames.MAGE].rankSkills
    wizardSkills = PlayerClassData.PLAYER_CLASS_DATA_MAP[AdvancedPlayerClassNames.WIZARD].rankSkills

    missileSkill = mageSkills[2]
    manaSkill = mageSkills[3]
    blessingSkill = wizardSkills[2]
    serendipitySkill = wizardSkills[3]
    flowSkill = wizardSkills[4]

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EntityAIAction:
        target = controller.getAggroTarget(enemy)
        targetIdx = controller.getTargets(enemy).index(target)
        currentMana = controller.getCurrentMana(enemy)

        for cdKey in ["blessingCd"]:
            data[cdKey] -= 1

        missileCost = controller.getSkillManaCost(enemy, missileSkill)
        assert missileCost is not None

        if data["blessingCd"] <= 0:
            blessingTarget = _findBlessingTarget(controller, enemy, rng, True)
            blessingCost = controller.getSkillManaCost(enemy, blessingSkill)
            assert blessingCost is not None
            if blessingTarget is not None and currentMana >= blessingCost + (2 * missileCost):
                if blessingTarget == enemy:
                    data["blessingCd"] = rng.randint(1, 6)
                else:
                    data["blessingCd"] = 6
                return EntityAIAction(CombatActions.SKILL, 1, [controller.getTeammates(enemy).index(blessingTarget)],
                                      None, rng.choice(["FIRE", "ICE", "WIND"]))

        if currentMana >= missileCost:
            return EntityAIAction(CombatActions.SKILL, 0, [targetIdx], None, None)

        if controller.checkInRange(enemy, target):
            return EntityAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
        else:
            distance = 3 - controller.checkDistanceStrict(enemy, target)
            return EntityAIAction(CombatActions.RETREAT, None, [targetIdx], min(distance, 2), None)
        
    baseStats = {
        BaseStats.HP: 250, BaseStats.MP: 150,
        BaseStats.ATK: 30, BaseStats.DEF: 50, BaseStats.MAG: 130, BaseStats.RES: 80,
        BaseStats.ACC: 160, BaseStats.AVO: 60, BaseStats.SPD: 80
    }
    return Enemy(f"{adverb}{adjective} Wizard", "Wizard",
    "A wand-wielding fellow adventurer. Generally stoic, but panics badly under pressure.", 6,
    baseStats, flatStatMods, {}, 0.5, AttackType.MELEE, PhysicalAttackAttribute.CRUSHING,
    [ manaSkill, serendipitySkill, flowSkill ],
    [ missileSkill, blessingSkill ],
    teamCall, "",
    EntityAI({ "blessingCd": 1 }, decisionFn),
    lambda controller, entity:
        EnemyReward(6, 0, 0, None))
    
def arenaSaint(params : dict, rng : random.Random | None = None) -> Enemy:
    if rng is None:
        rng = random.Random()

    flatStatMods : dict[Stats, float] = { CombatStats.RANGE: 1 }
    roomNumber = params.get('roomNumber', 0)
    maxVarsRoomMap = {
        BaseStats.HP: [0, 30, 30, 70, 150],
        BaseStats.MP: [0, 15, 15, 25, 50],
        BaseStats.MAG: [0, 10, 10, 20, 40],
        BaseStats.DEF: [0, 5, 5, 10, 20],
        BaseStats.RES: [0, 10, 10, 20, 40],
        BaseStats.ACC: [0, 10, 10, 15, 30],
        BaseStats.AVO: [0, 5, 5, 10, 20],
        BaseStats.SPD: [0, 5, 5, 10, 25]
    }
    maxVars = {
        stat: maxVarsRoomMap[stat][min(roomNumber, len(maxVarsRoomMap[stat])-1)]
        for stat in maxVarsRoomMap
    }
    for stat in maxVars:
        if maxVars[stat] > 0:
            flatStatMods[stat] = rng.choice([0, rng.randint(1, maxVars[stat])])
    adjective = "Rookie"
    adverb = ""
    if roomNumber >= 2:
        adjective = rng.choice(DESCRIPTIVE_ADJECTIVES)
    if roomNumber >= 4:
        adverb = rng.choice(DESCRIPTIVE_ADVERBS) + " "
    teamCall = "" if roomNumber < 4 else f"A particularly {adjective.lower()} team approaches!"

    mageSkills = PlayerClassData.PLAYER_CLASS_DATA_MAP[BasePlayerClassNames.MAGE].rankSkills
    saintSkills = PlayerClassData.PLAYER_CLASS_DATA_MAP[AdvancedPlayerClassNames.SAINT].rankSkills

    missileSkill = mageSkills[2]
    manaSkill = mageSkills[3]
    healSkill = saintSkills[2]
    auraSkill = saintSkills[4]
    blessingSkill = saintSkills[5]

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EntityAIAction:
        target = controller.getAggroTarget(enemy)
        targetIdx = controller.getTargets(enemy).index(target)
        currentMana = controller.getCurrentMana(enemy)

        for cdKey in ["blessingCd"]:
            data[cdKey] -= 1

        missileCost = controller.getSkillManaCost(enemy, missileSkill)
        assert missileCost is not None
        healCost = controller.getSkillManaCost(enemy, healSkill)
        assert healCost is not None
        healThreshold = 3.5 * ((controller.combatStateMap[enemy].getTotalStatValue(BaseStats.MAG) *
                             controller.combatStateMap[enemy].getTotalStatValue(BaseStats.RES)) ** 0.5)

        for ally in controller.getTeammates(enemy):
            currentHealth = controller.getCurrentHealth(ally)
            maxHealth = controller.getMaxHealth(ally)
            if maxHealth - currentHealth >= healThreshold or currentHealth/maxHealth <= 0.5:
                return EntityAIAction(CombatActions.SKILL, 1, [controller.getTeammates(enemy).index(ally)], None, None)

        if data["blessingCd"] <= 0:
            blessingTarget = _findBlessingTarget(controller, enemy, rng, False)
            blessingCost = controller.getSkillManaCost(enemy, blessingSkill)
            assert blessingCost is not None
            if blessingTarget is not None and currentMana >= blessingCost + (3 * healCost):
                if blessingTarget == enemy:
                    data["blessingCd"] = rng.randint(1, 6)
                else:
                    data["blessingCd"] = 6
                return EntityAIAction(CombatActions.SKILL, 2, [controller.getTeammates(enemy).index(blessingTarget)],
                                      None, rng.choice(["LIGHT", "DARK"]))

        if controller.checkInRange(enemy, target):
            return EntityAIAction(CombatActions.ATTACK, None, [targetIdx], None, None)
        else:
            if currentMana >= missileCost + (3 * healCost):
                return EntityAIAction(CombatActions.SKILL, 0, [targetIdx], None, None)
            
            distance = controller.checkDistanceStrict(enemy, target) - controller.combatStateMap[enemy].getTotalStatValue(CombatStats.RANGE)
            return EntityAIAction(CombatActions.APPROACH, None, [targetIdx], min(distance, 2), None)
        
    baseStats = {
        BaseStats.HP: 250, BaseStats.MP: 150,
        BaseStats.ATK: 30, BaseStats.DEF: 50, BaseStats.MAG: 90, BaseStats.RES: 110,
        BaseStats.ACC: 130, BaseStats.AVO: 60, BaseStats.SPD: 75
    }
    return Enemy(f"{adverb}{adjective} Saint", "Saint",
    "An amulet-wielding fellow adventurer. Their biggest weakness is that they try to be too helpful.", 6,
    baseStats, flatStatMods, {}, 0.5, AttackType.MAGIC, MagicalAttackAttribute.NEUTRAL,
    [ manaSkill, auraSkill ],
    [ missileSkill, healSkill, blessingSkill ],
    teamCall, "",
    EntityAI({ "blessingCd": 1 }, decisionFn),
    lambda controller, entity:
        EnemyReward(6, 0, 0, None))