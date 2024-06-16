from __future__ import annotations

from structures.rpg_classes_skills import AttackSkillData
from rpg_consts import *
from structures.rpg_combat_entity import *

def waitSkill(name, timeMult):
    return SkillData(name, BasePlayerClassNames.WARRIOR, 0, True, False, "", 0, MAX_ACTION_TIMER * timeMult, False,
                         [], 0, 0, True, False)

## Training Courtyard

def basicDummy() -> Enemy:
    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        controller.logMessage(MessageType.DIALOGUE, "The training dummy is chilling.")
        return EnemyAIAction(CombatActions.SKILL, 0, [], None, None)
    return Enemy("Basic Dummy", "Dummy", 1, {
        BaseStats.HP: 40, BaseStats.MP: 1,
        BaseStats.ATK: 1, BaseStats.DEF: 5, BaseStats.MAG: 1, BaseStats.RES: 5,
        BaseStats.ACC: 1, BaseStats.AVO: 30, BaseStats.SPD: 20
    }, {}, {}, [], [waitSkill("", 1)],
    "You see a note on the training dummy...\n\"Practice the basics! Get in range of me, then Attack!\"", "",
    EnemyAI({}, decisionFn),
    lambda _1, _2: EnemyReward(1, 0, 0, None))

def skillfulDummy() -> Enemy:
    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        controller.logMessage(MessageType.DIALOGUE, "The training dummy is chilling.")
        return EnemyAIAction(CombatActions.SKILL, 0, [], None, None)
    return Enemy("Skillful Dummy", "Dummy", 1, {
        BaseStats.HP: 60, BaseStats.MP: 1,
        BaseStats.ATK: 1, BaseStats.DEF: 5, BaseStats.MAG: 1, BaseStats.RES: 5,
        BaseStats.ACC: 1, BaseStats.AVO: 30, BaseStats.SPD: 20
    }, {}, {}, [], [waitSkill("", 1)],
    "You see a note on the training dummy...\n\"You've learned an Active Skill! Try it out now!\"", "",
    EnemyAI({}, decisionFn),
    lambda _1, _2: EnemyReward(1, 0, 0, None))

def trainingBoss() -> Enemy:
    attackSkill = AttackSkillData("Storm Breaker", BasePlayerClassNames.WARRIOR, 0, False, 30, "",
                                  True, AttackType.MELEE, 3, DEFAULT_ATTACK_TIMER_USAGE, [], False)

    def decisionFn(controller : CombatController, enemy : CombatEntity, data : dict) -> EnemyAIAction:
        playerList = controller.getTargets(enemy)
        if data["aiIdx"] == 0:
            controller.logMessage(MessageType.DIALOGUE, "Aqi: \"Don't worry, I'll go a bit easy on you~\"")
            controller.applyMultStatBonuses(enemy,
                                            {BaseStats.ATK: 50/650, BaseStats.DEF: 20/500, BaseStats.RES: 20/500,
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
                if (controller.getCurrentMana(enemy)) >= 30:
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
    return Enemy("Instructor Aqi", "Aqi", 1, {
        BaseStats.HP: 100, BaseStats.MP: 1000,
        BaseStats.ATK: 650, BaseStats.DEF: 500, BaseStats.MAG: 300, BaseStats.RES: 500,
        BaseStats.ACC: 1200, BaseStats.AVO: 150, BaseStats.SPD: 850
    }, {
        CombatStats.RANGE: 0
    }, {
        CombatStats.REPOSITION_ACTION_TIME_MULT: 0.5
    }, [], [waitSkill("", 1), waitSkill("", 1.2), attackSkill],
    "Aqi: \"All warmed up now? Just gotta test you before sendin' you out!\"",
    "Your form's lookin' good! Remember to check your class n' skills before tryin' the real thing!",
    EnemyAI({"aiIdx": 0, "target": None}, decisionFn),
    lambda _1, _2: EnemyReward(1, 0, 0, None))