from __future__ import annotations

from rpg_consts import *
from rpg_combat_entity import *
import rpg_classes
import random
import math

class EntityCombatState(object):
    def __init__(self, entity : CombatEntity) -> None:
        self.entity : CombatEntity = entity

        self.currentHP : int = entity.getStatValue(BaseStats.HP)
        self.currentMP : int = entity.getStatValue(BaseStats.MP)

        self.flatStatMod : dict[Stats, float] = {}
        self.multStatMod : dict[Stats, float] = {}

        self.actionTimer : float = 0

        self.activeSkillEffects: dict[SkillEffect, int] = {}

    def getTotalStatValue(self, stat : Stats) -> int:
        base : int = self.entity.getStatValue(stat)
        flatMod : float = self.flatStatMod.get(stat, 0)
        multMod : float = self.multStatMod.get(stat, 1)
        return round((base + flatMod) * multMod)

    def getTotalStatValueFloat(self, stat : CombatStats) -> float:
        base : float = self.entity.getStatValueFloat(stat)
        flatMod : float = self.flatStatMod.get(stat, 0)
        multMod : float = self.multStatMod.get(stat, 1)
        return (base + flatMod) * multMod

    def getStateOverviewString(self) -> str:
        return f"{self.entity.name}: {self.currentHP}/{self.getTotalStatValue(BaseStats.HP)} HP, {self.currentMP}/{self.getTotalStatValue(BaseStats.MP)} MP"

    def getFullStatusString(self) -> str:
        statString = {stat: self.getFullStatusStatString(stat) for stat in BaseStats}
        return f"""{self.getStateOverviewString()}
ATK: {statString[BaseStats.ATK]}, DEF: {statString[BaseStats.DEF]}, MAG: {statString[BaseStats.MAG]}, RES: {statString[BaseStats.RES]}
ACC: {statString[BaseStats.ACC]}, AVO: {statString[BaseStats.AVO]}, SPD: {statString[BaseStats.SPD]}"""

    def getFullStatusStatString(self, stat : BaseStats) -> str:
        baseStatValue = self.entity.getStatValue(stat)
        totalStatValue = self.getTotalStatValue(stat)
        if baseStatValue == totalStatValue:
            return str(totalStatValue)
        else:
            return f"{totalStatValue} ({baseStatValue})"

    """ Given that action timer fills at a rate speed ** 0.5, gets time until it reaches the maximum. """
    def getTimeToFullAction(self) -> float:
        return (MAX_ACTION_TIMER - self.actionTimer) / (self.getTotalStatValue(BaseStats.SPD) ** 0.5)

    """ As above, increases the actionTimer to reflect some amount of time passing. """
    def increaseActionTimer(self, timePassed : float) -> float:
        self.actionTimer += timePassed * (self.getTotalStatValue(BaseStats.SPD) ** 0.5)
        return self.actionTimer

    def applyFlatStatBonuses(self, flatStatMap : dict[Stats, float]) -> None:
        for stat in flatStatMap:
            self.flatStatMod[stat] = self.flatStatMod.get(stat, 0) + flatStatMap[stat]

    def applyMultStatBonuses(self, multStatMap : dict[Stats, float]) -> None:
        for stat in multStatMap:
            self.multStatMod[stat] = self.multStatMod.get(stat, 1) * multStatMap[stat]

    def revertFlatStatBonuses(self, flatStatMap : dict[Stats, float]) -> None:
        for stat in flatStatMap:
            self.flatStatMod[stat] -= flatStatMap[stat]

    def revertMultStatBonuses(self, multStatMap : dict[Stats, float]) -> None:
        for stat in multStatMap:
            self.multStatMod[stat] /= multStatMap[stat]

    """
        Increments the amount of time skills have been active. Returns the set of expiring effects.
    """
    def durationTick(self) -> set[SkillEffect]:
        result = set()
        for effect in self.activeSkillEffects:
            self.activeSkillEffects[effect] += 1
            if effect.effectDuration is None:
                continue
            if self.activeSkillEffects[effect] >= effect.effectDuration:
                result.add(effect)
        return result

    def getEffectFunctions(self, effectTiming : EffectTimings) -> list:
        result = []
        for skillEffect in self.activeSkillEffects:
            result += list(filter(lambda effectFunction : effectFunction.effectTiming == effectTiming, skillEffect.effectFunctions))
        return result

class CombatController(object):
    def __init__(self, playerTeam : list[CombatEntity], opponentTeam : list[CombatEntity]) -> None:
        self.playerTeam : list[CombatEntity] = playerTeam[:]
        self.opponentTeam : list[CombatEntity] = opponentTeam[:]

        self.distanceMap : dict[CombatEntity, dict[CombatEntity, int]] = {}
        for player in self.playerTeam:
            self.distanceMap[player] = {}
            for opponent in self.opponentTeam:
                self.distanceMap[player][opponent] = 2 #TODO: some way to modify starting positions

        self.combatStateMap : dict[CombatEntity, EntityCombatState] = {}
        for team in [self.playerTeam, self.opponentTeam]:
            for entity in team:
                self.combatStateMap[entity] = EntityCombatState(entity)
                self.combatStateMap[entity].activeSkillEffects

        self.rng : random.Random = random.Random()

    # Internal function; figures out which of two given entities expected to belong to separate teams is which
    def _separateTeamValidator(self, entity1 : CombatEntity, entity2 : CombatEntity) -> tuple[CombatEntity, CombatEntity] | None:
        player, opponent = (entity1, entity2) if entity1 in self.playerTeam else (entity2, entity1)
        if not (player in self.playerTeam) or not (opponent in self.opponentTeam):
            return None
        return (player, opponent)

    """
        Gets the list of living entities on the opposing team that can be targeted.
    """
    def getTargets(self, entity : CombatEntity) -> list[CombatEntity]:
        if entity in self.playerTeam:
            return list(filter(lambda entity: self.combatStateMap[entity].currentHP > 0, self.opponentTeam[:]))
        else:
            return list(filter(lambda entity: self.combatStateMap[entity].currentHP > 0, self.playerTeam[:]))

    def getCombatOverviewString(self) -> str:
        playerTeamOverview : str = "\n".join([f"[{idx+1}] {self.combatStateMap[player].getStateOverviewString()}"
            for idx, player in enumerate(self.playerTeam)])
        opponentTeamOverview : str = "\n".join([f"[{idx+1}] {self.combatStateMap[opponent].getStateOverviewString()}"
            for idx, opponent in enumerate(self.opponentTeam)])
        return f"{playerTeamOverview}\n\n{opponentTeamOverview}"

    def getFullStatusStringFor(self, target : CombatEntity) -> str:
        return self.combatStateMap[target].getFullStatusString()

    def getTimeToFullAction(self, entity : CombatEntity) -> float:
        return self.combatStateMap[entity].getTimeToFullAction()

    """
        Updates all action timers according to current entity speeds, returning the player who gets to move next.
        Entities with 0 HP are ignored.
        In the case of a tie, a random selection is made.
    """
    def advanceToNextPlayer(self) -> CombatEntity:
        actionTimeMap : dict[CombatEntity, float] = {entity : self.combatStateMap[entity].getTimeToFullAction() for entity in self.combatStateMap}
        livingEntities = list(filter(lambda entity: self.combatStateMap[entity].currentHP > 0, self.combatStateMap.keys()))
        nextEntity : CombatEntity = min(livingEntities, key = lambda entity: actionTimeMap[entity])
        for entity in livingEntities:
            self.combatStateMap[entity].increaseActionTimer(actionTimeMap[nextEntity])
        return nextEntity

    """
        Given two separate entities on opposing teams, returns the current distance between them.
        Returns None if the given entities are invalid.
    """
    def checkDistance(self, entity1 : CombatEntity, entity2 : CombatEntity) -> int | None:
        teamValidator = self._separateTeamValidator(entity1, entity2)
        if teamValidator is None:
            return None
        player, opponent = teamValidator
        return self.distanceMap[player][opponent]

    """
        Given two separate entities on opposing teams, changes and then returns the distance between them.
        Returns None if the given entities are invalid.
    """
    def updateDistance(self, entity1 : CombatEntity, entity2 : CombatEntity, newDistance : int) -> int | None:
        teamValidator = self._separateTeamValidator(entity1, entity2)
        if teamValidator is None:
            return None
        player, opponent = teamValidator
        self.distanceMap[player][opponent] = newDistance
        return self.distanceMap[player][opponent]

    """
        Checks if an attacker hits a defender. Distance modifier treated as 1x if they're on the same team (for debugging).
    """
    def rollForHit(self, attacker : CombatEntity, defender : CombatEntity) -> bool:
        distance : int | None = self.checkDistance(attacker, defender)
        distanceMod : float = 1
        if distance is not None:
            distanceMod = 1.1 - (0.1 * (distance ** 2))

        attackerAcc : float = self.combatStateMap[attacker].getTotalStatValue(BaseStats.ACC)
        defenderAvo : float = self.combatStateMap[defender].getTotalStatValue(BaseStats.AVO)
        hitChance : float = ((attackerAcc * distanceMod)/defenderAvo) ** 0.5
        return self.rng.random() <= hitChance

    """
        Checks for the damage inflicted by the attacker on the defender.
        Returns a tuple containing the damage and whether or not the hit was critical.
    """
    def rollForDamage(self, attacker : CombatEntity, defender : CombatEntity, isPhysical : bool) -> tuple[int, bool]:
        offenseStat : BaseStats = BaseStats.ATK if isPhysical else BaseStats.MAG
        defenseStat : BaseStats = BaseStats.DEF if isPhysical else BaseStats.RES
        attackerOS : float = self.combatStateMap[attacker].getTotalStatValue(offenseStat)
        defenderDS : float = self.combatStateMap[defender].getTotalStatValue(defenseStat)

        critChance : float = self.combatStateMap[attacker].getTotalStatValueFloat(CombatStats.CRIT_RATE)
        critDamage : float = self.combatStateMap[attacker].getTotalStatValueFloat(CombatStats.CRIT_DAMAGE)
        isCrit : bool = self.rng.random() <= critChance
        critFactor : float = critDamage if isCrit else 1

        damageReduction : float = self.combatStateMap[defender].getTotalStatValueFloat(CombatStats.DAMAGE_REDUCTION)

        statRatio : float = attackerOS/defenderDS
        damageFactor : float = 1 - math.exp((statRatio ** DAMAGE_FORMULA_C) * math.log(1 - DAMAGE_FORMULA_K))
        variationFactor : float = self.rng.uniform(0.9, 1.1)
        return (math.ceil(attackerOS * damageFactor * variationFactor * critFactor * (1 - damageReduction)), isCrit)

    """
        Makes a target take damage. Returns actual damage taken.
    """
    def applyDamage(self, attacker : CombatEntity, defender : CombatEntity, damageTaken : int) -> int:
        originalHP : int = self.combatStateMap[defender].currentHP
        self.combatStateMap[defender].currentHP = max(0, originalHP - damageTaken)
        return originalHP - self.combatStateMap[defender].currentHP

    """
        Makes a target spend mana. Returns actual mana spent.
    """
    def spendMana(self, entity : CombatEntity, mpCost : int) -> int:
        originalMP : int = self.combatStateMap[entity].currentMP
        self.combatStateMap[entity].currentMP = max(0, originalMP - mpCost)
        return originalMP - self.combatStateMap[entity].currentMP

    """
        Makes a target gain mana. Returns actual mana gained.
    """
    def gainMana(self, entity : CombatEntity, mpGain : int) -> int:
        originalMP : int = self.combatStateMap[entity].currentMP
        self.combatStateMap[entity].currentMP = min(self.combatStateMap[entity].getTotalStatValue(BaseStats.MP), originalMP + mpGain)
        return self.combatStateMap[entity].currentMP - originalMP

    def getCurrentHealth(self, entity : CombatEntity) -> int:
        return self.combatStateMap[entity].currentHP

    def getCurrentMana(self, entity : CombatEntity) -> int:
        return self.combatStateMap[entity].currentMP

    """
        Reduce an entity's action timer. Returns updated timer amount.
    """
    def spendActionTimer(self, entity : CombatEntity, amount : float) -> float:
        self.combatStateMap[entity].actionTimer = max(0, self.combatStateMap[entity].actionTimer - amount)
        return self.combatStateMap[entity].actionTimer

    """
        Adds a skill effect for an entity.
    """
    def addSkillEffect(self, entity : CombatEntity, skillEffect : SkillEffect) -> None:
        if skillEffect not in self.combatStateMap[entity].activeSkillEffects:
            self.combatStateMap[entity].activeSkillEffects[skillEffect] = 0

    """
        Removes a skill effect from an entity.
    """
    def removeSkillEffect(self, entity : CombatEntity, skillEffect : SkillEffect) -> None:
        self.combatStateMap[entity].activeSkillEffects.pop(skillEffect)

    """
        Checks to see if all entities have been defeated.
        Returns None if not; otherwise, returns true iff the player team was victorious.
    """
    def checkPlayerVictory(self) -> bool | None:
        livingPlayers : int = len(list(filter(lambda entity: self.combatStateMap[entity].currentHP > 0, self.playerTeam)))
        livingOpponents : int = len(list(filter(lambda entity: self.combatStateMap[entity].currentHP > 0, self.opponentTeam)))

        if livingPlayers > 0 and livingOpponents > 0:
            return None
        return livingPlayers > 0

    """
        Stat changing methods for effect hooks
    """
    def applyFlatStatBonuses(self, entity : CombatEntity, flatStatMap : dict[Stats, float]) -> None:
        self.combatStateMap[entity].applyFlatStatBonuses(flatStatMap)

    def applyMultStatBonuses(self, entity : CombatEntity, multStatMap : dict[Stats, float]) -> None:
        self.combatStateMap[entity].applyMultStatBonuses(multStatMap)

    def revertFlatStatBonuses(self, entity : CombatEntity, flatStatMap : dict[Stats, float]) -> None:
        self.combatStateMap[entity].revertFlatStatBonuses(flatStatMap)

    def revertMultStatBonuses(self, entity : CombatEntity, multStatMap : dict[Stats, float]) -> None:
        self.combatStateMap[entity].revertMultStatBonuses(multStatMap)

    """-
        Performs an active skill. Indicates if an attack should begin; otherwise, performs end of action/turn cleanup.
    """
    def performActiveSkill(self, user : CombatEntity, target : CombatEntity, skill : SkillData) -> ActionResultInfo:
        # TODO: also do range check here

        if skill.mpCost is not None:
            if self.combatStateMap[user].currentMP < skill.mpCost:
                return ActionResultInfo(ActionSuccessState.FAILURE_MANA, False)
            else:
                self.spendMana(user, skill.mpCost)

        immediateEffects = filter(lambda effectFunction : effectFunction.effectTiming == EffectTimings.IMMEDIATE, skill.getAllEffectFunctions())
        for effectFunction in immediateEffects:
            assert(isinstance(effectFunction, rpg_classes.EFImmediate))
            effectFunction.applyEffect(self, user, target)

        # add skill effects to active
        for effect in skill.skillEffects:
            self.addSkillEffect(user, effect)

        if skill.actionTime is not None:
            self.spendActionTimer(user, skill.actionTime)
        if not skill.causesAttack:
            self._endPlayerTurn(user)

        return ActionResultInfo(ActionSuccessState.SUCCESS, skill.causesAttack)

    """
        Performs all steps of an attack, modifying HP, Action Timers, etc. as needed.
    """
    def performAttack(self, attacker : CombatEntity, defender : CombatEntity, isPhysical : bool, isBasic : bool) -> AttackResultInfo:
        # TODO: range check here?

        for effectFunction in self.combatStateMap[attacker].getEffectFunctions(EffectTimings.BEFORE_ATTACK):
            assert(isinstance(effectFunction, rpg_classes.EFBeforeNextAttack))
            effectFunction.applyEffect(self, attacker, defender)

        checkHit : bool = self.rollForHit(attacker, defender)
        damageDealt : int = 0
        isCritical : bool = False
        if checkHit:
            damage, isCritical = self.rollForDamage(attacker, defender, isPhysical)
            damageDealt = self.applyDamage(attacker, defender, damage)

        attackResultInfo = AttackResultInfo(checkHit, damageDealt, isCritical)

        actionTimerUsage : float = DEFAULT_ATTACK_TIMER_USAGE
        actionTimeMult : float = 1
        for effectFunction in self.combatStateMap[attacker].getEffectFunctions(EffectTimings.AFTER_ATTACK):
            if isinstance(effectFunction, rpg_classes.EFAfterNextAttack):
                effectResult = effectFunction.applyEffect(self, attacker, defender, attackResultInfo)
                if effectResult.actionTime is not None:
                    actionTimerUsage = effectResult.actionTime
                if effectResult.actionTimeMult is not None:
                    actionTimeMult = effectResult.actionTimeMult
            elif isinstance(effectFunction, rpg_classes.EFBeforeNextAttack_Revert):
                effectFunction.applyEffect(self, attacker, defender)

        if isBasic:
            self.gainMana(attacker, BASIC_ATTACK_MP_GAIN)
            self.spendActionTimer(attacker, actionTimerUsage * actionTimeMult)

        self._endPlayerTurn(attacker)

        return attackResultInfo

    """
        Cleanup for end of turn. At the moment, just decreases effect durations.
    """
    def _endPlayerTurn(self, player) -> None:
        for expiredEffect in self.combatStateMap[player].durationTick():
            self.removeSkillEffect(player, expiredEffect)

class ActionResultInfo(object):
    def __init__(self, success : ActionSuccessState, startAttack : bool) -> None:
        self.success : ActionSuccessState = success
        self.startAttack : bool = startAttack

class AttackResultInfo(object):
    def __init__(self, attackHit : bool, damageDealt : int, isCritical : bool) -> None:
        self.attackHit : bool = attackHit
        self.damageDealt : int = damageDealt
        self.isCritical : bool = isCritical