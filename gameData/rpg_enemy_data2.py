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
