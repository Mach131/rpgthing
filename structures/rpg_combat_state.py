from __future__ import annotations
from typing import TYPE_CHECKING, Callable
import random
import math

from rpg_consts import *
from structures.rpg_classes_skills import EFBeforeAttacked, EFBeforeAttacked_Revert, EFOnAdvanceTurn, EFOnAttackSkill, EFOnHealSkill, EFOnStatusApplied, EFStartTurn, EnchantmentSkillEffect, SkillData, AttackSkillData, ActiveToggleSkillData, SkillEffect, \
    EFImmediate, EFBeforeNextAttack, EFBeforeNextAttack_Revert, EFAfterNextAttack, EFWhenAttacked, \
    EFOnDistanceChange, EFOnStatsChange, EFOnParry, EFBeforeAllyAttacked, EFEndTurn
from structures.rpg_messages import MessageCollector, makeTeamString
from gameData.rpg_status_definitions import StatusEffect

if TYPE_CHECKING:
    from structures.rpg_combat_entity import CombatEntity

class EntityCombatState(object):
    def __init__(self, entity : CombatEntity) -> None:
        self.entity : CombatEntity = entity

        self.currentHP : int = entity.getStatValue(BaseStats.HP)
        self.currentMP : int = entity.getStatValue(BaseStats.MP)

        self.flatStatMod : dict[Stats, float] = {}
        self.multStatMod : dict[Stats, float] = {}

        self.weaknesses : list[AttackAttribute] = []
        self.resistances : list[AttackAttribute] = []

        self.actionTimer : float = 0

        self.activeSkillEffects: dict[SkillEffect, int] = {}
        self.activeToggleSkills: set[ActiveToggleSkillData] = set()
        self.effectStacks : dict[EffectStacks, int] = {}
        self.activeEnchantments : list[EnchantmentSkillEffect] = []
        self.inactiveEnchantmentDurations : dict[EnchantmentSkillEffect, int] = {}

        self.defendActive : bool = False
        self.parryType : AttackType | None = None
        self.activeParrySkillEffect: SkillEffect | None = None

        defaultStatusTolerance = BASE_DEFAULT_STATUS_TOLERANCE + (PER_LEVEL_DEFAULT_STATUS_TOLERANCE * self.entity.level)
        self.maxStatusTolerance : dict[StatusConditionNames, float] = {status : defaultStatusTolerance for status in StatusConditionNames}
        self.currentStatusTolerance : dict[StatusConditionNames, float] = {status : defaultStatusTolerance for status in StatusConditionNames}
        self.currentStatusEffects : dict[StatusConditionNames, StatusEffect] = {}

        self.aggroMap : dict[CombatEntity, float] = {}
        
    def addStack(self, stack : EffectStacks, maxStacks : int | None):
        if maxStacks is not None:
            self.effectStacks[stack] = min(self.effectStacks.get(stack, 0) + 1, maxStacks)
        else:
            self.effectStacks[stack] = self.effectStacks.get(stack, 0) + 1
        
    def setStack(self, stack : EffectStacks, val : int):
        self.effectStacks[stack] = val

    def getStack(self, stack : EffectStacks) -> int:
        return self.effectStacks.get(stack, 0)

    def _adjustCurrentValues(self):
        if self.currentHP > self.getTotalStatValue(BaseStats.HP):
            self.currentHP = self.getTotalStatValue(BaseStats.HP)
        if self.currentMP > self.getTotalStatValue(BaseStats.MP):
            self.currentMP = self.getTotalStatValue(BaseStats.MP)

    def getTotalStatValue(self, stat : Stats) -> int:
        base : int = self.entity.getStatValue(stat)
        flatMod : float = self.flatStatMod.get(stat, 0)
        multMod : float = self.multStatMod.get(stat, 1)
        return round((base + flatMod) * multMod)

    def getTotalStatValueFloat(self, stat : Stats) -> float:
        base : float = self.entity.getStatValueFloat(stat)
        flatMod : float = self.flatStatMod.get(stat, 0)
        multMod : float = self.multStatMod.get(stat, 1)
        return (base + flatMod) * multMod

    def getStateOverviewString(self) -> str:
        baseStatusString = f"**{self.entity.name}**: {self.currentHP}/{self.getTotalStatValue(BaseStats.HP)} HP, {self.currentMP}/{self.getTotalStatValue(BaseStats.MP)} MP"
        return baseStatusString

    def getFullStatusString(self) -> str:
        statString = {stat: self.getFullStatusStatString(stat) for stat in BaseStats}
        return f"{self.currentHP}/{self.getTotalStatValue(BaseStats.HP)} **HP**  \\||  {self.currentMP}/{self.getTotalStatValue(BaseStats.MP)} **MP**\n" + \
        f"**ATK**: {statString[BaseStats.ATK]}  \\||  **DEF**: {statString[BaseStats.DEF]}  \\||  **MAG**: {statString[BaseStats.MAG]}  \\||  **RES**: {statString[BaseStats.RES]}\n" + \
        f"**ACC**: {statString[BaseStats.ACC]}  \\||  **AVO**: {statString[BaseStats.AVO]}  \\||  **SPD**: {statString[BaseStats.SPD]}\n" + \
        f"**Range**: {self.getFullStatusStatString(CombatStats.RANGE)}  \\||  **Crit Rate**: {self.getFullStatusPercentStatString(CombatStats.CRIT_RATE)}  \\||  **Crit Damage**: {self.getFullStatusPercentStatString(CombatStats.CRIT_DAMAGE)}"
    
    def getStackBuffString(self) -> str:
        stackStringList = [f"{EFFECT_STACK_NAMES[stack]} x{self.getStack(stack)}" for stack in self.effectStacks
                                if self.getStack(stack) > 0 and stack in EFFECT_STACK_NAMES]
        stackString = '\n'.join(stackStringList)

        if len(stackString) > 0:
            stackString += "\n[TODO: add buff names]"
        return stackString

    def getFullStatusStatString(self, stat : Stats) -> str:
        baseStatValue = self.entity.getStatValue(stat)
        totalStatValue = self.getTotalStatValue(stat)
        if baseStatValue == totalStatValue:
            return str(totalStatValue)
        else:
            return f"*{totalStatValue}* ({baseStatValue})"
        
    def getFullStatusPercentStatString(self, stat : CombatStats) -> str:
        baseStatValue = self.entity.getStatValueFloat(stat)
        totalStatValue = self.getTotalStatValueFloat(stat)
        if baseStatValue == totalStatValue:
            return f"{totalStatValue*100:.1f}%"
        else:
            return f"*{totalStatValue*100:.1f}%* ({baseStatValue*100:.1f}%)"

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
        self._adjustCurrentValues()

    def applyMultStatBonuses(self, multStatMap : dict[Stats, float]) -> None:
        for stat in multStatMap:
            self.multStatMod[stat] = self.multStatMod.get(stat, 1) * multStatMap[stat]
        self._adjustCurrentValues()

    def revertFlatStatBonuses(self, flatStatMap : dict[Stats, float]) -> None:
        for stat in flatStatMap:
            if stat not in self.flatStatMod:
                assert(flatStatMap[stat] == 0)
                self.flatStatMod[stat] = 0
            self.flatStatMod[stat] -= flatStatMap[stat]
        self._adjustCurrentValues()

    def revertMultStatBonuses(self, multStatMap : dict[Stats, float]) -> None:
        for stat in multStatMap:
            if stat not in self.multStatMod:
                assert(multStatMap[stat] == 1)
                self.multStatMod[stat] = 1
            self.multStatMod[stat] /= multStatMap[stat]
        self._adjustCurrentValues()

    """
        Removes effects with no duration. Returns the set of expiring effects.
    """
    def durationCheck(self) -> set[SkillEffect]:
        result = set()
        for effect in self.activeSkillEffects:
            if effect.effectDuration is None:
                continue
            if self.activeSkillEffects[effect] >= effect.effectDuration:
                result.add(effect)
        return result

    """
        Increments the amount of time skills have been active. Returns the set of expiring effects.
        Also automatically removes inactive enchatments.
    """
    def durationTick(self, controller : CombatController) -> set[SkillEffect]:
        for effect in self.activeSkillEffects:
            self.activeSkillEffects[effect] += 1
        
        removeEnchantments = []
        for enchantment in self.inactiveEnchantmentDurations:
            self.inactiveEnchantmentDurations[enchantment] += 1
            if enchantment.effectDuration is not None and self.inactiveEnchantmentDurations[enchantment] >= enchantment.effectDuration:
                removeEnchantments.append(enchantment)
        [self.removeEnchantmentEffect(enchantment, controller) for enchantment in removeEnchantments]
        return self.durationCheck()

    def getEffectFunctions(self, effectTiming : EffectTimings) -> list:
        result = []
        for skillEffect in self.activeSkillEffects:
            result += list(filter(lambda effectFunction : effectFunction.effectTiming == effectTiming, skillEffect.effectFunctions))
        return result
    
    """
        Updates the current weapon attribute (previous enchantments are remembered, but not expressed.)
        Assumes that the enchantment skill effect has been added normally already.
    """
    def addEnchantmentEffect(self, enchantmentEffect : EnchantmentSkillEffect) -> None:
        if len(self.activeEnchantments) > 0:
            # Disable previously active enchantment
            previousEnchantment = self.activeEnchantments[-1]
            self.inactiveEnchantmentDurations[previousEnchantment] = self.activeSkillEffects.pop(previousEnchantment)
            self.revertFlatStatBonuses(previousEnchantment.flatStatBonuses)
            self.revertMultStatBonuses(previousEnchantment.multStatBonuses)
            
        self.activeEnchantments.append(enchantmentEffect)
        self.applyFlatStatBonuses(enchantmentEffect.flatStatBonuses)
        self.applyMultStatBonuses(enchantmentEffect.multStatBonuses)

    """
        Removes an enchantment associated with the given skill.
        Assumes that the enchantment skill effect has been removed normally already.
    """
    def removeEnchantmentEffect(self, enchantmentEffect : EnchantmentSkillEffect, controller : CombatController) -> None:
        wasActiveEnchantment = enchantmentEffect == self.activeEnchantments[-1]
        self.activeEnchantments.remove(enchantmentEffect)
        self.inactiveEnchantmentDurations.pop(enchantmentEffect, None)
        
        newEnchantmentStr = ""
        if wasActiveEnchantment:
            self.revertFlatStatBonuses(enchantmentEffect.flatStatBonuses)
            self.revertMultStatBonuses(enchantmentEffect.multStatBonuses)
            if len(self.activeEnchantments) > 0:
                # Reactivate next enchantment on stack
                newEnchantment = self.activeEnchantments[-1]
                self.activeSkillEffects[newEnchantment] = self.inactiveEnchantmentDurations.pop(newEnchantment)
                self.applyFlatStatBonuses(newEnchantment.flatStatBonuses)
                self.applyMultStatBonuses(newEnchantment.multStatBonuses)
                newEnchantmentStr = f" (The {newEnchantment.enchantmentAttribute.name} enchantment is now active.)"
        controller.logMessage(MessageType.EXPIRATION,
                              f"{self.entity.name}'s {enchantmentEffect.enchantmentAttribute.name} enchantment wore off.{newEnchantmentStr}")
            
    def getCurrentAttackAttribute(self, isPhysical : bool) -> AttackAttribute:
        if len(self.activeEnchantments) > 0:
            return self.activeEnchantments[-1].enchantmentAttribute
        weaponAttribute = self.entity.basicAttackAttribute
        # Use neutral magic if weapon has a physical attribute
        if isinstance(weaponAttribute, PhysicalAttackAttribute) and not isPhysical:
            weaponAttribute = MagicalAttackAttribute.NEUTRAL
        return weaponAttribute
    
    def getDefaultAttackType(self) -> AttackType:
        return self.entity.basicAttackType
    
    """
        Sets an attack type as the parry target for a specific skill effect.
        Only one parry skill effect can be set at a time.
    """
    def setParryType(self, parryType : AttackType, skillEffect : SkillEffect):
        self.clearParryType()
        self.parryType = parryType
        self.activeParrySkillEffect = skillEffect

    def clearParryType(self):
        if self.activeParrySkillEffect is not None:
            self.activeSkillEffects.pop(self.activeParrySkillEffect)
        self.activeParrySkillEffect = None
        self.parryType = None
    
    """
        Accounts for weaknesses and resistances.
    """
    def getAttributeDamageMultiplier(self, attackAttribute : AttackAttribute, bonusWeaknessDamageMult : float, ignoreResistanceMult : float) -> float:
        weaknessInstances : int = self.weaknesses.count(attackAttribute)
        weaknessModifier : float = self.getTotalStatValueFloat(CombatStats.WEAKNESS_MODIFIER) * bonusWeaknessDamageMult
        weaknessMultiplier : float = (1 + weaknessModifier) ** weaknessInstances

        resistanceInstances : int = self.resistances.count(attackAttribute)
        resistanceModifier : float = self.getTotalStatValueFloat(CombatStats.RESISTANCE_MODIFIER) * ignoreResistanceMult
        if resistanceModifier < 0: resistanceModifier = 0
        resistanceMultiplier : float = (1 + resistanceModifier) ** -resistanceInstances

        return weaknessMultiplier * resistanceMultiplier
    
    def getStatusResistChance(self, statusName : StatusConditionNames) -> float:
        toleranceRatio = self.currentStatusTolerance[statusName] / MAX_RESIST_STATUS_TOLERANCE
        return toleranceRatio * self.getTotalStatValueFloat(CombatStats.STATUS_RESISTANCE_MULTIPLIER)
    
    """
        Attempts to apply a status effect. Returns true if successful (or if the status was already present, in which case it is amplified).
    """
    def applyStatusCondition(self, statusCondition : StatusEffect, controller : CombatController):
        randomRoll = controller._randomRoll(statusCondition.inflicter, self.entity)
        statusName : StatusConditionNames = statusCondition.statusName
        if statusName in self.currentStatusEffects:
            durationExtension = self.currentStatusEffects[statusName].amplifyStatus(controller, self.entity, statusCondition, randomRoll)
            self.activeSkillEffects[self.currentStatusEffects[statusName]] -= durationExtension
            
            durationStr = " Its duration was extended!" if durationExtension > 0 else ""
            controller.logMessage(MessageType.EFFECT,
                                  f"{self.entity.name}'s {statusName.name} was amplified!{durationStr}")
            return True
        else:
            statusResistance = self.getStatusResistChance(statusName)
            statusResistance *= controller.combatStateMap[statusCondition.inflicter].getTotalStatValueFloat(CombatStats.STATUS_APPLICATION_TOLERANCE_MULTIPLIER)
            controller.logMessage(MessageType.PROBABILITY,
                                  f"{self.entity.name}'s {statusName.name} resistance chance: {statusResistance * 100:.1f}%")
            if randomRoll >= statusResistance:
                controller.logMessage(MessageType.EFFECT,
                                      f"{self.entity.name} was inflicted with {statusName.name}!")
                self.currentStatusEffects[statusName] = statusCondition

                immediateEffects = filter(lambda effectFunction : effectFunction.effectTiming == EffectTimings.IMMEDIATE, statusCondition.effectFunctions)
                for effectFunction in immediateEffects:
                    if isinstance(effectFunction, EFImmediate):
                        effectFunction.applyEffect(controller, self.entity, [])
                self.activeSkillEffects[statusCondition] = 0
                return True
            else:
                controller.logMessage(MessageType.EFFECT,
                                      f"{self.entity.name} resisted the {statusName.name}!")
                self.reduceTolerance(statusName, STATUS_TOLERANCE_RESIST_DECREASE)
                return False
            
    def reduceTolerance(self, statusName : StatusConditionNames, amount : int):
        self.currentStatusTolerance[statusName] -= amount
        if self.currentStatusTolerance[statusName] < 0:
            self.currentStatusTolerance[statusName] = 0
        
    def removeStatusCondition(self, statusName : StatusConditionNames, controller : CombatController):
        if statusName not in self.currentStatusEffects:
            return
        
        controller.logMessage(MessageType.EFFECT,
                              f"{self.entity.name}'s {statusName.name} wore off.")
        self.currentStatusEffects.pop(statusName)
        self.maxStatusTolerance[statusName] *= STATUS_TOLERANCE_RECOVERY_INCREASE_FACTOR
        self.currentStatusTolerance[statusName] = self.maxStatusTolerance[statusName]


class CombatController(object):
    def __init__(self, playerTeam : list[CombatEntity], opponentTeam : list[CombatEntity],
                startingPlayerTeamDistances : dict[CombatEntity, int], loggers : dict[CombatEntity, MessageCollector],
                spawnerCallback : Callable[[CombatEntity, bool], None]) -> None:
        self.playerTeam : list[CombatEntity] = playerTeam[:]
        self.opponentTeam : list[CombatEntity] = opponentTeam[:]
        self.loggers : dict[CombatEntity, MessageCollector] = loggers
        self.spawnerCallback : Callable[[CombatEntity, bool], None] = spawnerCallback

        self.opponentNameCount = {}
        self.namedOpponentMemory = {}
        for opponent in self.opponentTeam:
            self._removeDuplicateOpponentNames(opponent)

        self.distanceMap : dict[CombatEntity, dict[CombatEntity, int]] = {}
        for player in self.playerTeam:
            self.distanceMap[player] = {}
            for opponent in self.opponentTeam:
                startingDistance = startingPlayerTeamDistances.get(player, DEFAULT_STARTING_DISTANCE)
                self.distanceMap[player][opponent] = startingDistance

        self.combatStateMap : dict[CombatEntity, EntityCombatState] = {}
        for team in [self.playerTeam, self.opponentTeam]:
            for entity in team:
                self.combatStateMap[entity] = EntityCombatState(entity)
                for skill in entity.availablePassiveSkills:
                    self._activateImmediateEffects(entity, [], skill)
                    [self.addSkillEffect(entity, skillEffect) for skillEffect in skill.skillEffects]

                if entity in startingPlayerTeamDistances:
                    displacement = abs(startingPlayerTeamDistances[entity] - DEFAULT_STARTING_DISTANCE)
                    self.combatStateMap[entity].actionTimer -= FORMATION_ACTION_TIMER_PENALTY * displacement

        self.previousTurnEntity : CombatEntity | None = None
        self.rng : random.Random = random.Random()

        plural = "" if len(playerTeam) > 1 else "es"
        self.logMessage(MessageType.BASIC,
                        f"*{makeTeamString(playerTeam)} approach{plural} {makeTeamString(opponentTeam)}.*")
        for opponent in self.opponentTeam:
            if len(opponent.encounterMessage) > 0:
                self.logMessage(MessageType.DIALOGUE, opponent.encounterMessage)
                break
        self.logMessage(MessageType.BASIC, "**COMBAT START!**")

    def _removeDuplicateOpponentNames(self, newOpponent : CombatEntity):
        opponentName = newOpponent.name
        nameCount = self.opponentNameCount.get(opponentName, 0)
        if nameCount > 0:
            newOpponent.name += f" ({nameCount+1})"
            newOpponent.shortName += f" ({nameCount+1})"
            if nameCount == 1:
                self.namedOpponentMemory[opponentName].name += " (1)"
                self.namedOpponentMemory[opponentName].shortName += " (1)"
        self.opponentNameCount[opponentName] = nameCount + 1
        self.namedOpponentMemory[opponentName] = newOpponent

    def logMessage(self, messageType : MessageType, messageText : str):
        [log.addMessage(messageType, messageText) for log in self.loggers.values()]
    
    def spawnNewEntity(self, entity : CombatEntity, enemyTeam : bool):
        self.spawnerCallback(entity, enemyTeam)
        if enemyTeam:
            self.opponentTeam.append(entity)
            for player in self.playerTeam:
                self.distanceMap[player][entity] = DEFAULT_STARTING_DISTANCE
            self._removeDuplicateOpponentNames(entity)
        else:
            self.playerTeam.append(entity)
            for opponent in self.opponentTeam:
                self.distanceMap[entity][opponent] = DEFAULT_STARTING_DISTANCE

        self.combatStateMap[entity] = EntityCombatState(entity)
        for skill in entity.availablePassiveSkills:
            self._activateImmediateEffects(entity, [], skill)
            [self.addSkillEffect(entity, skillEffect) for skillEffect in skill.skillEffects]
        self.logMessage(MessageType.BASIC, f"*{entity.name} joins the battle!*")

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
        
    def getTeammates(self, entity : CombatEntity) -> list[CombatEntity]:
        if entity in self.playerTeam:
            return list(filter(lambda entity: self.combatStateMap[entity].currentHP > 0, self.playerTeam[:]))
        else:
            return list(filter(lambda entity: self.combatStateMap[entity].currentHP > 0, self.opponentTeam[:]))

    def getCombatOverviewString(self) -> str:
        playerTeamOverview : str = "\n".join([f"[{idx+1}] {self.combatStateMap[player].getStateOverviewString()}"
            for idx, player in enumerate(self.playerTeam)])
        opponentTeamOverview : str = "\n".join([f"[{idx+1}] {self.combatStateMap[opponent].getStateOverviewString()}"
            for idx, opponent in enumerate(self.opponentTeam)])
        return f"{playerTeamOverview}\n\n{opponentTeamOverview}"

    def getFullStatusStringFor(self, target : CombatEntity) -> str:
        return self.combatStateMap[target].getFullStatusString()
    
    def getBuffStatusStringFor(self, target : CombatEntity) -> str:
        return self.combatStateMap[target].getStackBuffString()

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

        # Time-stop consistency
        if self.previousTurnEntity in livingEntities and actionTimeMap[self.previousTurnEntity] == 0:
            nextEntity = self.previousTurnEntity

        for entity in livingEntities:
            self.combatStateMap[entity].increaseActionTimer(actionTimeMap[nextEntity])
            if self.previousTurnEntity is not None:
                for effectFunction in self.combatStateMap[entity].getEffectFunctions(EffectTimings.ADVANCE_TURN):
                    assert(isinstance(effectFunction, EFOnAdvanceTurn))
                    effectFunction.applyEffect(self, entity, self.previousTurnEntity, nextEntity)

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
    
    def checkDistanceStrict(self, entity1 : CombatEntity, entity2 : CombatEntity) -> int:
        teamValidator = self._separateTeamValidator(entity1, entity2)
        assert(teamValidator is not None)
        player, opponent = teamValidator
        return self.distanceMap[player][opponent]

    """
        Given two separate entities on opposing teams, changes the distance between them.
        Assumes that entity1 is the one initiating the reposition; it may fail if they are RESTRICTED.
        Returns None if the given entities are invalid; otherwise, returns data for any activated bonus attacks.
    """
    def updateDistance(self, entity1 : CombatEntity, entity2 : CombatEntity,
                       newDistance : int) -> list[tuple[CombatEntity, CombatEntity, AttackSkillData]]:
        if newDistance > MAX_DISTANCE:
            newDistance = MAX_DISTANCE
        if newDistance < 0:
            newDistance = 0

        teamValidator = self._separateTeamValidator(entity1, entity2)
        if teamValidator is None:
            return []
        player, opponent = teamValidator
        oldDistance = self.distanceMap[player][opponent]

        if StatusConditionNames.RESTRICT in self.combatStateMap[entity1].currentStatusEffects:
            newDistance = oldDistance
        self.distanceMap[player][opponent] = newDistance

        if oldDistance != newDistance:
            self.logMessage(MessageType.POSITIONING,
                            f"{entity1.name} repositions to distance {newDistance} from {entity2.name}!")

        reactionAttackData : list[tuple[CombatEntity, CombatEntity, AttackSkillData]] = []
        for effectFunction in self.combatStateMap[entity1].getEffectFunctions(EffectTimings.ON_REPOSITION):
            assert(isinstance(effectFunction, EFOnDistanceChange))
            effectResult = effectFunction.applyEffect(self, entity1, entity2, True, oldDistance, newDistance)
            if effectResult.bonusAttacks is not None:
                reactionAttackData += effectResult.bonusAttacks
        for effectFunction in self.combatStateMap[entity2].getEffectFunctions(EffectTimings.ON_REPOSITION):
            assert(isinstance(effectFunction, EFOnDistanceChange))
            effectResult = effectFunction.applyEffect(self, entity2, entity1, False, oldDistance, newDistance)
            if effectResult.bonusAttacks is not None:
                reactionAttackData += effectResult.bonusAttacks

        return reactionAttackData

    """
        Gets a random float from 0 to 1, accounting for luck values.
        The Positive player's luck favors higher rolls, and the Negative player's favors low rolls.
    """
    def _randomRoll(self, positiveEntity : CombatEntity | None, negativeEntity : CombatEntity | None) -> float:
        totalLuck = 0
        if positiveEntity is not None:
            totalLuck += self.combatStateMap[positiveEntity].getTotalStatValue(CombatStats.LUCK)
        if negativeEntity is not None:
            totalLuck -= self.combatStateMap[negativeEntity].getTotalStatValue(CombatStats.LUCK)

        rolls = [self.rng.random() for i in range(1 + abs(totalLuck))]
        if totalLuck > 0:
            return max(rolls)
        else:
            return min(rolls)
    
    """
        The above, but for a uniform distribution.
    """
    def _randomRollUniform(self, a : float, b : float, positiveEntity : CombatEntity | None, negativeEntity : CombatEntity | None) -> float:
        totalLuck = 0
        if positiveEntity is not None:
            totalLuck += self.combatStateMap[positiveEntity].getTotalStatValue(CombatStats.LUCK)
        if negativeEntity is not None:
            totalLuck -= self.combatStateMap[negativeEntity].getTotalStatValue(CombatStats.LUCK)

        rolls = [self.rng.uniform(a, b) for i in range(1 + abs(totalLuck))]
        if totalLuck > 0:
            return max(rolls)
        else:
            return min(rolls)

    """
        Checks if an attacker hits a defender. Distance modifier treated as 1x if they're on the same team (for debugging).
    """
    def rollForHit(self, attacker : CombatEntity, defender : CombatEntity) -> bool:
        distance : int | None = self.checkDistance(attacker, defender)
        distanceMod : float = 1
        if distance is not None:
            distance += self.combatStateMap[attacker].getTotalStatValue(CombatStats.ACC_EFFECTIVE_DISTANCE_MOD)
            if (distance < 0): distance = 0
            if (distance > MAX_DISTANCE): distance = MAX_DISTANCE
            distanceMod = 1.1 - (0.1 * (distance ** self.combatStateMap[attacker].getTotalStatValueFloat(CombatStats.ACCURACY_DISTANCE_MOD)))

        attackerAcc : float = self.combatStateMap[attacker].getTotalStatValue(BaseStats.ACC)
        defenderAvo : float = self.combatStateMap[defender].getTotalStatValue(BaseStats.AVO)
       
        accAvoRatio : float = attackerAcc/defenderAvo
        distanceMultiplier : float = 2 * (distanceMod ** 0.5)
        domainScaleTerm : float = math.tan(math.pi * (1 - (2 ** (1 - accAvoRatio))) / 2)
        hitChance : float = distanceMultiplier / (1 + math.exp(-ACCURACY_FORMULA_C * domainScaleTerm))
        self.logMessage(MessageType.PROBABILITY,
                        f"{attacker.name}'s chance to hit {defender.name}: {hitChance*100:.3f}%")

        return self._randomRoll(defender, attacker) <= hitChance

    """
        Checks for the damage inflicted by the attacker on the defender.
        Returns a tuple containing the damage and whether or not the hit was critical.
    """
    def rollForDamage(self, attacker : CombatEntity, defender : CombatEntity, isPhysical : bool) -> tuple[int, bool]:
        offenseStat : BaseStats = BaseStats.ATK if isPhysical else BaseStats.MAG
        defenseStat : BaseStats = BaseStats.DEF if isPhysical else BaseStats.RES
        attackerOS : float = self.combatStateMap[attacker].getTotalStatValue(offenseStat)
        defenderDS : float = self.combatStateMap[defender].getTotalStatValue(defenseStat)

        # Targeting lower defensive stat
        if self.combatStateMap[attacker].getTotalStatValue(CombatStats.OPPORTUNISM) == 1:
            defenderDS = min(self.combatStateMap[defender].getTotalStatValue(BaseStats.DEF),
                             self.combatStateMap[defender].getTotalStatValue(BaseStats.RES))

        # attack power override
        if self.combatStateMap[attacker].getTotalStatValue(CombatStats.FIXED_ATTACK_POWER) > 0:
            attackerOS = self.combatStateMap[attacker].getTotalStatValue(CombatStats.FIXED_ATTACK_POWER)

        critChance : float = self.combatStateMap[attacker].getTotalStatValueFloat(CombatStats.CRIT_RATE)
        critDamage : float = self.combatStateMap[attacker].getTotalStatValueFloat(CombatStats.CRIT_DAMAGE)
        isCrit : bool = self._randomRoll(defender, attacker) <= critChance
        critFactor : float = critDamage if isCrit else 1

        attackAttribute : AttackAttribute = self.combatStateMap[attacker].getCurrentAttackAttribute(isPhysical)
        bonusWeaknessDamage : float = self.combatStateMap[attacker].getTotalStatValueFloat(CombatStats.BONUS_WEAKNESS_DAMAGE_MULT)
        ignoreResistance : float = self.combatStateMap[attacker].getTotalStatValueFloat(CombatStats.IGNORE_RESISTANCE_MULT)
        attributeMultiplier : float = self.combatStateMap[defender].getAttributeDamageMultiplier(
            attackAttribute, bonusWeaknessDamage, ignoreResistance)

        damageReduction : float = self.combatStateMap[defender].getTotalStatValueFloat(CombatStats.DAMAGE_REDUCTION)
        defenseReduction : float = 1
        if self.combatStateMap[defender].defendActive:
            defenseReduction *= DEFEND_DAMAGE_MULTIPLIER
            self.gainMana(defender, DEFEND_HIT_MP_GAIN)
            self.combatStateMap[defender].defendActive = False

        statRatio : float = attackerOS/defenderDS
        damageFactor : float = 1 - math.exp((statRatio ** DAMAGE_FORMULA_C) * math.log(1 - DAMAGE_FORMULA_K))
        variationFactor : float = self._randomRollUniform(0.9, 1.1, attacker, defender)
        return (math.ceil(attackerOS * damageFactor * variationFactor * critFactor * attributeMultiplier
                          * (1 - damageReduction) * defenseReduction), isCrit)

    """
        Makes a target take damage. Returns actual damage taken.
    """
    def applyDamage(self, attacker : CombatEntity, defender : CombatEntity, damageTaken : int,
                    isCritical : bool = False, silent : bool = False) -> int:
        # If doing anything with attacker, first ensure it's not the same as the defender (e.g. weapon curse)
        originalHP : int = self.combatStateMap[defender].currentHP
        newHP : int = max(0, originalHP - damageTaken)
        self.combatStateMap[defender].currentHP = newHP

        if originalHP != newHP:
            if not silent:
                critString = " (Critical)" if isCritical else ""
                self.logMessage(MessageType.DAMAGE_COMBAT,
                            f"{defender.name} takes **{damageTaken} damage{critString}**!")
                
            aggroMult = self.combatStateMap[attacker].getTotalStatValueFloat(CombatStats.AGGRO_MULT)
            self.combatStateMap[defender].aggroMap[attacker] = self.combatStateMap[defender].aggroMap.get(attacker, 0) + \
                                                                damageTaken * aggroMult
            
            # TODO: may need to do something with result
            for effectFunction in self.combatStateMap[defender].getEffectFunctions(EffectTimings.ON_STAT_CHANGE):
                assert(isinstance(effectFunction, EFOnStatsChange))
                effectFunction.applyEffect(self, defender, {SpecialStats.CURRENT_HP: originalHP}, {SpecialStats.CURRENT_HP: newHP})
        
        if newHP == 0 and not silent:
            self.logMessage(MessageType.BASIC,
                            f"**{defender.name} is defeated!**")

        return originalHP - self.combatStateMap[defender].currentHP

    """
        Makes a target gain health, subject to healing effectiveness. Returns actual health gained.
    """
    def gainHealth(self, entity : CombatEntity, hpGain : int, isCritical : bool = False, silent : bool = False) -> int:
        originalHP : int = self.combatStateMap[entity].currentHP

        healingEffectiveness = self.combatStateMap[entity].getTotalStatValueFloat(CombatStats.HEALING_EFFECTIVENESS)
        hpGain = max(0, math.ceil(hpGain * healingEffectiveness))

        self.combatStateMap[entity].currentHP = min(self.getMaxHealth(entity), originalHP + hpGain)
        healthGained : int = self.combatStateMap[entity].currentHP - originalHP
        if healthGained > 0:
            if not silent:
                critString = " (Critical Heal)" if isCritical else ""
                self.logMessage(MessageType.DAMAGE_COMBAT,
                                f"{entity.name} **restores {healthGained} health{critString}**!")

            # TODO: may need to do something with result
            for effectFunction in self.combatStateMap[entity].getEffectFunctions(EffectTimings.ON_STAT_CHANGE):
                assert(isinstance(effectFunction, EFOnStatsChange))
                effectFunction.applyEffect(self, entity, {SpecialStats.CURRENT_HP: originalHP}, {SpecialStats.CURRENT_HP: originalHP + healthGained})
                
        return healthGained

    """
        Makes a target spend mana. Returns actual mana spent.
    """
    def spendMana(self, entity : CombatEntity, mpCost : int, silent : bool = False) -> int:
        originalMP : int = self.combatStateMap[entity].currentMP
        newMP : int = max(0, originalMP - mpCost)
        self.combatStateMap[entity].currentMP = newMP

        if originalMP != newMP:
            if not silent:
                self.logMessage(MessageType.MANA,
                                f"{entity.name} spends {originalMP - newMP} mana!")
            
            # TODO: may need to do something with result
            for effectFunction in self.combatStateMap[entity].getEffectFunctions(EffectTimings.ON_STAT_CHANGE):
                assert(isinstance(effectFunction, EFOnStatsChange))
                effectFunction.applyEffect(self, entity, {SpecialStats.CURRENT_MP: originalMP}, {SpecialStats.CURRENT_MP: newMP})

        return originalMP - self.combatStateMap[entity].currentMP

    """
        Makes a target gain mana. Returns actual mana gained.
    """
    def gainMana(self, entity : CombatEntity, mpGain : int, silent : bool = False) -> int:
        originalMP : int = self.combatStateMap[entity].currentMP

        manaGainMult = self.combatStateMap[entity].getTotalStatValueFloat(CombatStats.MANA_GAIN_MULT)
        if self.combatStateMap[entity].getTotalStatValue(CombatStats.INSTANTANEOUS_ETERNITY) == 1:
            manaGainMult = 0
        mpGain = round(mpGain * manaGainMult)

        self.combatStateMap[entity].currentMP = min(self.getMaxMana(entity), originalMP + mpGain)
        manaGained = self.combatStateMap[entity].currentMP - originalMP
        if manaGained > 0:
            if not silent:
                self.logMessage(MessageType.MANA,
                                f"{entity.name} restores {manaGained} mana!")
            
            # TODO: may need to do something with result
            for effectFunction in self.combatStateMap[entity].getEffectFunctions(EffectTimings.ON_STAT_CHANGE):
                assert(isinstance(effectFunction, EFOnStatsChange))
                effectFunction.applyEffect(self, entity, {SpecialStats.CURRENT_MP: originalMP}, {SpecialStats.CURRENT_MP: originalMP + manaGained})
        return manaGained

    def getCurrentHealth(self, entity : CombatEntity) -> int:
        return self.combatStateMap[entity].currentHP

    def getMaxHealth(self, entity : CombatEntity) -> int:
        return self.combatStateMap[entity].getTotalStatValue(BaseStats.HP)

    def getCurrentMana(self, entity : CombatEntity) -> int:
        return self.combatStateMap[entity].currentMP

    def getMaxMana(self, entity : CombatEntity) -> int:
        return self.combatStateMap[entity].getTotalStatValue(BaseStats.MP)
    
    def addWeaknessStacks(self, entity : CombatEntity, attackAttribute : AttackAttribute, numStacks : int) -> None:
        self.combatStateMap[entity].weaknesses += [attackAttribute] * numStacks
    
    def addResistanceStacks(self, entity : CombatEntity, attackAttribute : AttackAttribute, numStacks : int) -> None:
        self.combatStateMap[entity].resistances += [attackAttribute] * numStacks

    def removeWeaknessStacks(self, entity : CombatEntity, attackAttribute : AttackAttribute, numStacks : int) -> None:
        for i in range(numStacks):
            self.combatStateMap[entity].weaknesses.remove(attackAttribute)

    def removeResistanceStacks(self, entity : CombatEntity, attackAttribute : AttackAttribute, numStacks : int) -> None:
        for i in range(numStacks):
            self.combatStateMap[entity].resistances.remove(attackAttribute)

    """
        Reduce an entity's action timer. Returns updated timer amount.
    """
    def spendActionTimer(self, entity : CombatEntity, amount : float) -> float:
        amount *= self.combatStateMap[entity].getTotalStatValueFloat(CombatStats.ACTION_GAUGE_USAGE_MULTIPLIER)
        if self.combatStateMap[entity].getTotalStatValue(CombatStats.INSTANTANEOUS_ETERNITY) == 1:
            amount = 0

        #self.combatStateMap[entity].actionTimer = max(0, self.combatStateMap[entity].actionTimer - amount)
        self.combatStateMap[entity].actionTimer -= amount
        return self.combatStateMap[entity].actionTimer
    
    """
        Restores some fraction of an entity's action timer; cannot make it exactly full.
        Returns updated timer amount.
    """
    def increaseActionTimer(self, entity : CombatEntity, fraction : float) -> float:
        self.combatStateMap[entity].actionTimer += round(MAX_ACTION_TIMER * fraction)
        if self.combatStateMap[entity].actionTimer >= MAX_ACTION_TIMER:
            self.combatStateMap[entity].actionTimer = MAX_ACTION_TIMER - EPSILON
        return self.combatStateMap[entity].actionTimer
    
    """
        Attempts to apply a status effect, or amplify an already-applied status effect.
    """
    def applyStatusCondition(self, entity : CombatEntity, statusEffect : StatusEffect) -> bool:
        statusSuccess =  self.combatStateMap[entity].applyStatusCondition(statusEffect, self)
        if statusSuccess and statusEffect.inflicter != entity:
            for effectFunction in self.combatStateMap[statusEffect.inflicter].getEffectFunctions(EffectTimings.ON_APPLY_STATUS_SUCCESS):
                if isinstance(effectFunction, EFOnStatusApplied):
                    effectFunction.applyEffect(self, statusEffect.inflicter, entity, statusEffect.statusName)
        return statusSuccess

    """
        Adds a skill effect for an entity.
    """
    def addSkillEffect(self, entity : CombatEntity, skillEffect : SkillEffect) -> None:
        if skillEffect not in self.combatStateMap[entity].activeSkillEffects:
            self.combatStateMap[entity].activeSkillEffects[skillEffect] = 0
            if isinstance(skillEffect, EnchantmentSkillEffect):
                self.combatStateMap[entity].addEnchantmentEffect(skillEffect)

    """
        Removes a skill effect from an entity.
    """
    def removeSkillEffect(self, entity : CombatEntity, skillEffect : SkillEffect) -> None:
        self.combatStateMap[entity].activeSkillEffects.pop(skillEffect)
        if isinstance(skillEffect, StatusEffect):
            skillEffect.onRemove(self, entity)
            self.combatStateMap[entity].removeStatusCondition(skillEffect.statusName, self)
        if isinstance(skillEffect, EnchantmentSkillEffect):
            self.combatStateMap[entity].removeEnchantmentEffect(skillEffect, self)

    """
        Gets the targetable opponent that the entity currently has the greatest aggro towards.
        In case of a tie, makes a selection and slightly boosts the winner (to prevent alternating).
    """
    def getAggroTarget(self, entity : CombatEntity) -> CombatEntity:
        aggroMap = self.combatStateMap[entity].aggroMap
        opponents = self.getTargets(entity)

        maxAggro = 0
        targetOptions = []
        for opponent in opponents:
            aggro = aggroMap.get(opponent, 0)
            if aggro > maxAggro:
                maxAggro = aggro
                targetOptions = [opponent]
            elif aggro == maxAggro:
                targetOptions.append(opponent)

        assert(len(targetOptions) > 0)
        if len(targetOptions) > 1:
            chosenTarget = self.rng.choice(targetOptions)
            aggroMap[chosenTarget] = maxAggro + 1
            targetOptions = [chosenTarget]
        return targetOptions[0]
    
    """
        Applies aggro decay multipliers. Intended to be called at the end of the entity's turn.
    """
    def _applyAggroDecay(self, entity : CombatEntity) -> None:
        aggroMap = self.combatStateMap[entity].aggroMap
        aggroFactor = entity.aggroDecayFactor
        for target in aggroMap:
            aggroMap[target] *= aggroFactor
            
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
        originalStats = {stat: self.combatStateMap[entity].getTotalStatValueFloat(stat) for stat in flatStatMap}
        self.combatStateMap[entity].applyFlatStatBonuses(flatStatMap)
        newStats = {stat: self.combatStateMap[entity].getTotalStatValueFloat(stat) for stat in flatStatMap}
        self._onStatMapChange(entity, originalStats, newStats)

    def applyMultStatBonuses(self, entity : CombatEntity, multStatMap : dict[Stats, float]) -> None:
        originalStats = {stat: self.combatStateMap[entity].getTotalStatValueFloat(stat) for stat in multStatMap}
        self.combatStateMap[entity].applyMultStatBonuses(multStatMap)
        newStats = {stat: self.combatStateMap[entity].getTotalStatValueFloat(stat) for stat in multStatMap}
        self._onStatMapChange(entity, originalStats, newStats)

    def revertFlatStatBonuses(self, entity : CombatEntity, flatStatMap : dict[Stats, float]) -> None:
        originalStats = {stat: self.combatStateMap[entity].getTotalStatValueFloat(stat) for stat in flatStatMap}
        self.combatStateMap[entity].revertFlatStatBonuses(flatStatMap)
        newStats = {stat: self.combatStateMap[entity].getTotalStatValueFloat(stat) for stat in flatStatMap}
        self._onStatMapChange(entity, originalStats, newStats)

    def revertMultStatBonuses(self, entity : CombatEntity, multStatMap : dict[Stats, float]) -> None:
        originalStats = {stat: self.combatStateMap[entity].getTotalStatValueFloat(stat) for stat in multStatMap}
        self.combatStateMap[entity].revertMultStatBonuses(multStatMap)
        newStats = {stat: self.combatStateMap[entity].getTotalStatValueFloat(stat) for stat in multStatMap}
        self._onStatMapChange(entity, originalStats, newStats)

    def _onStatMapChange(self, entity : CombatEntity, originalStats : dict[Stats, float], newStats : dict[Stats, float]):
        # TODO: may need to do something with result
        for effectFunction in self.combatStateMap[entity].getEffectFunctions(EffectTimings.ON_STAT_CHANGE):
            assert(isinstance(effectFunction, EFOnStatsChange))
            effectFunction.applyEffect(self, entity, originalStats, newStats)

    """
        Returns any activated reaction attacks.
    """
    def _activateImmediateEffects(self, user : CombatEntity, targets : list[CombatEntity],
                                  skill : SkillData) -> list[tuple[CombatEntity, CombatEntity, AttackSkillData]]:
        reactionAttackData : list[tuple[CombatEntity, CombatEntity, AttackSkillData]] = []
        immediateEffects = filter(lambda effectFunction : effectFunction.effectTiming == EffectTimings.IMMEDIATE, skill.getAllEffectFunctions())
        for effectFunction in immediateEffects:
            if isinstance(effectFunction, EFImmediate):
                effectResult = effectFunction.applyEffect(self, user, targets)
                if effectResult.bonusAttacks is not None:
                    reactionAttackData += effectResult.bonusAttacks

        # Trigger effects caused by existing skills
        for effectFunction in self.combatStateMap[user].getEffectFunctions(EffectTimings.IMMEDIATE):
            if isinstance(effectFunction, EFOnAttackSkill) and skill.causesAttack:
                effectResult = effectFunction.applyEffect(self, user, targets)
                if effectResult.bonusAttacks is not None:
                    reactionAttackData += effectResult.bonusAttacks
        return reactionAttackData

    """
        Performs a repositioning action, performing end-of-turn cleanup.
        Returns a map of changed distances to targets, from the user's perspective.
        If the result is empty, the reposition failed.
        May also return attack data for a triggered counterattack, in which case endTurn operations are not yet called.
    """
    def performReposition(self, user : CombatEntity, targets : list[CombatEntity], distanceChange : int) -> RepositionResultInfo:
        if distanceChange > MAX_SINGLE_REPOSITION:
            distanceChange = MAX_SINGLE_REPOSITION
        if distanceChange < -MAX_SINGLE_REPOSITION:
            distanceChange = -MAX_SINGLE_REPOSITION

        timerPerDistance = DEFAULT_RETREAT_TIMER_USAGE if distanceChange > 0 else DEFAULT_APPROACH_TIMER_USAGE
        expectedTimerCost = (timerPerDistance + (DEFAULT_MULTI_REPOSITION_TIMER_USAGE * (len(targets) - 1))) * abs(distanceChange)
        expectedTimerCost *= self.combatStateMap[user].getTotalStatValueFloat(CombatStats.REPOSITION_ACTION_TIME_MULT)
        if expectedTimerCost > MAX_ACTION_TIMER:
            return RepositionResultInfo(False, {}, False, None, None, None, [])
        totalDistanceChange = 0

        oldDistances = {}
        for target in targets:
            oldDistances[target] = self.checkDistance(user, target)
            if oldDistances[target] is None:
                return RepositionResultInfo(False, {}, False, None, None, None, [])
            
        newDistances = {}
        bonusAttackDetails = []
        for target in targets:
            bonusAttackDetails += self.updateDistance(user, target, oldDistances[target] + distanceChange)
            newDistances[target] = self.checkDistance(user, target)
            totalDistanceChange += abs(newDistances[target] - oldDistances[target])

        realTimerCost = (timerPerDistance + (DEFAULT_MULTI_REPOSITION_TIMER_USAGE * (len(targets) - 1))) * abs(totalDistanceChange)
        realTimerCost *= self.combatStateMap[user].getTotalStatValueFloat(CombatStats.REPOSITION_ACTION_TIME_MULT)
        if totalDistanceChange > 0:
            self.gainMana(user, REPOSITION_MP_GAIN)
            self.spendActionTimer(user, realTimerCost)
        else:
            return RepositionResultInfo(False, {}, False, None, None, None, [])

        if len(bonusAttackDetails) == 0:
            self._endPlayerTurn(user)
            return RepositionResultInfo(True, newDistances, False, None, None, None, [])
        else:
            return RepositionResultInfo(True, newDistances, True,
                                        bonusAttackDetails[0][0], bonusAttackDetails[0][1], bonusAttackDetails[0][2], bonusAttackDetails[1:])

    """
        Checks to see if a given reposition is possible (and will have any effect), without actually executing it.
    """
    def validateReposition(self, user : CombatEntity, targets : list[CombatEntity], distanceChange : int) -> bool:
        if StatusConditionNames.RESTRICT in self.combatStateMap[user].currentStatusEffects:
            return False
        
        if distanceChange > MAX_SINGLE_REPOSITION:
            return False
        if distanceChange < -MAX_SINGLE_REPOSITION:
            return False

        timerPerDistance = DEFAULT_RETREAT_TIMER_USAGE if distanceChange > 0 else DEFAULT_APPROACH_TIMER_USAGE
        expectedTimerCost = (timerPerDistance + (DEFAULT_MULTI_REPOSITION_TIMER_USAGE * (len(targets) - 1))) * abs(distanceChange)
        expectedTimerCost *= self.combatStateMap[user].getTotalStatValueFloat(CombatStats.REPOSITION_ACTION_TIME_MULT)
        if expectedTimerCost > MAX_ACTION_TIMER:
            return False

        oldDistances = {}
        for target in targets:
            oldDistances[target] = self.checkDistance(user, target)
            if oldDistances[target] is None:
                return False
            
        newDistances = {}
        for target in targets:
            newDistances[target] = oldDistances[target] + distanceChange
            if newDistances[target] < 0:
                newDistances[target] = 0
            if newDistances[target] > MAX_DISTANCE:
                newDistances[target] = MAX_DISTANCE
            if abs(newDistances[target] - oldDistances[target]) > 0:
                return True
        return False

    """
        Performs a defend action, performing end-of-turn cleanup.
    """
    def performDefend(self, user : CombatEntity) -> None:
        self.combatStateMap[user].defendActive = True
        self.logMessage(MessageType.ACTION,
                        f"{user.name} defends themselves against the next attack!")

        self.gainMana(user, DEFEND_MP_GAIN)
        self.spendActionTimer(user, MAX_ACTION_TIMER)
        self._endPlayerTurn(user)

    """-
        Performs an active skill. Indicates if an attack should begin; otherwise, performs end of action/turn cleanup.
    """
    def performActiveSkill(self, user : CombatEntity, targets : list[CombatEntity], skill : SkillData) -> ActionResultInfo:
        validTargets = True
        expectedTeam = self.opponentTeam if user in self.playerTeam else self.playerTeam
        if not skill.targetOpponents:
            expectedTeam = self.playerTeam if user in self.playerTeam else self.opponentTeam
        if skill.expectedTargets is not None and len(targets) != skill.expectedTargets:
            validTargets = False
        if not all([target in expectedTeam for target in targets]):
            validTargets = False
        if not validTargets:
            return ActionResultInfo(ActionSuccessState.FAILURE_TARGETS, False, None, False, False, [])

        isToggle = isinstance(skill, ActiveToggleSkillData)
        toggleEnabled = isToggle and skill in self.combatStateMap[user].activeToggleSkills

        mpCost = self.getSkillManaCost(user, skill)
        if mpCost is not None and not toggleEnabled:
            if self.combatStateMap[user].currentMP < mpCost:
                return ActionResultInfo(ActionSuccessState.FAILURE_MANA, False, None, False, False, [])
            else:
                self.spendMana(user, mpCost)

        skipDurationTick = False
        reactionAttackData = []
        if not isToggle:
            if skill.skillName != "":
                targetString = f" on {makeTeamString(targets)}" if len(targets) > 0 else ""
                if len(targets) == 1 and targets[0] == user:
                    targetString = " on themselves"
                self.logMessage(MessageType.ACTION,
                                f"{user.name} uses {skill.skillName}{targetString}!")
            reactionAttackData = self._activateImmediateEffects(user, targets, skill)
            # add skill effects to active
            for effect in skill.skillEffects:
                self.addSkillEffect(user, effect)
        else:
            if not toggleEnabled:
                self.logMessage(MessageType.ACTION,
                                f"{user.name} activates {skill.skillName}!")
                self.combatStateMap[user].activeToggleSkills.add(skill)
                self.applyFlatStatBonuses(user, skill.flatStatBonuses)
                self.applyMultStatBonuses(user, skill.multStatBonuses)
                for effect in skill.skillEffects:
                    self.addSkillEffect(user, effect)
            else:
                self.logMessage(MessageType.ACTION,
                                f"{user.name} deactivates {skill.skillName}.")
                self.combatStateMap[user].activeToggleSkills.remove(skill)
                self.revertFlatStatBonuses(user, skill.flatStatBonuses)
                self.revertMultStatBonuses(user, skill.multStatBonuses)
                for effect in skill.skillEffects:
                    self.removeSkillEffect(user, effect)
                skipDurationTick = True

        attackTarget : CombatEntity | None = None
        if skill.actionTime is not None:
            self.spendActionTimer(user, skill.actionTime)

        if not skill.causesAttack and len(reactionAttackData) == 0:
            self._endPlayerTurn(user, skipDurationTick)
        elif skill.causesAttack:
            attackTarget = targets[skill.attackTargetIndex]

        return ActionResultInfo(ActionSuccessState.SUCCESS, skill.causesAttack, attackTarget, isToggle, not toggleEnabled, reactionAttackData)
    
    def getSkillManaCost(self, entity : CombatEntity, skill : SkillData) -> int | None:
        if skill.mpCost is None:
            return None
        costMult = self.combatStateMap[entity].getTotalStatValueFloat(CombatStats.MANA_COST_MULT)
        if isinstance(skill, AttackSkillData):
            costMult *= self.combatStateMap[entity].getTotalStatValueFloat(CombatStats.ATTACK_SKILL_MANA_COST_MULT)
        return round(skill.mpCost * costMult)

    """
        Performs all steps of an attack, modifying HP, Action Timers, etc. as needed.
    """
    def performAttack(self, attacker : CombatEntity, defender : CombatEntity,
                      isPhysical : bool, attackType : AttackType | None, isBasic : bool,
                      bonusAttackData : list[tuple[CombatEntity, CombatEntity, AttackSkillData]]) -> AttackResultInfo:
        if isBasic:
            self.logMessage(MessageType.ACTION,
                            f"{attacker.name} attacks {defender.name}!")

        # initial attack
        attackResultInfo : AttackResultInfo = self._doSingleAttack(attacker, defender, isPhysical, attackType, isBasic, False)
        if attackResultInfo.repeatAttack:
            repeatAttackResultInfo : AttackResultInfo = self._doSingleAttack(attacker, defender, isPhysical, attackType, False, True)
            attackResultInfo.addBonusResultInfo(repeatAttackResultInfo)
        self._cleanupEffects(attacker)

        [attackResultInfo.addBonusAttack(*bonusAttack) for bonusAttack in bonusAttackData]
        self._processBonusAttacks(attackResultInfo)
        self._endPlayerTurn(attacker)
        return attackResultInfo
    
    """
        For attacks caused as a reaction to actions like repositioning; treats them all as bonus attacks.
    """
    def performReactionAttack(self, turnPlayer : CombatEntity, attacker : CombatEntity, defender : CombatEntity, attackSkillData : AttackSkillData,
                              additionalAttacks : list[tuple[CombatEntity, CombatEntity, AttackSkillData]]):
        self.logMessage(MessageType.ACTION,
                        f"{attacker.name} performs a bonus attack against {defender.name}!")
        
        self.performActiveSkill(attacker, [defender], attackSkillData)
        attackResultInfo = self._doSingleAttack(attacker, defender, attackSkillData.isPhysical, attackSkillData.attackType, False, True)
        [attackResultInfo.addBonusAttack(*additionalAttack) for additionalAttack in additionalAttacks]
        self._cleanupEffects(attacker)

        self._processBonusAttacks(attackResultInfo)
        self._endPlayerTurn(turnPlayer)
        return attackResultInfo

    def _processBonusAttacks(self, attackResultInfo : AttackResultInfo):
        # process bonus attacks
        while len(attackResultInfo.bonusAttacks) > 0:
            bonusAttacker, bonusTarget, bonusAttackData = attackResultInfo.bonusAttacks.pop(0)
            if self.getCurrentHealth(bonusAttacker) > 0:
                self.performActiveSkill(bonusAttacker, [bonusTarget], bonusAttackData)
                self.logMessage(MessageType.ACTION,
                                f"{bonusAttacker.name} performs a bonus attack against {bonusTarget.name}!")
                bonusAttackResultInfo : AttackResultInfo = self._doSingleAttack(bonusAttacker, bonusTarget, bonusAttackData.isPhysical,
                                                                                bonusAttackData.attackType, False, True)
                attackResultInfo.addBonusResultInfo(bonusAttackResultInfo)
                self._cleanupEffects(bonusAttacker)
    
    """
        Checks if a target is in range. Returns false for entities on the same team.
    """
    def checkInRange(self, attacker : CombatEntity, defender : CombatEntity):
        distance = self.checkDistance(attacker, defender)
        if distance is None:
            return False
        elif self.combatStateMap[attacker].getTotalStatValue(CombatStats.IGNORE_RANGE_CHECK) == 0:
            if self.combatStateMap[attacker].getTotalStatValue(CombatStats.RANGE) < distance:
                return False
        return True
    
    def _doSingleAttack(self, attacker : CombatEntity, defender : CombatEntity,
                        isPhysical : bool, attackType : AttackType | None, isBasic : bool, isBonus : bool) -> AttackResultInfo:
        if attackType is None:
            attackType = self.combatStateMap[attacker].getDefaultAttackType()
        
        for effectFunction in self.combatStateMap[attacker].getEffectFunctions(EffectTimings.BEFORE_ATTACK):
            assert(isinstance(effectFunction, EFBeforeNextAttack))
            effectFunction.applyEffect(self, attacker, defender)
        for ally in self.getTeammates(defender):
            for effectFunction in self.combatStateMap[ally].getEffectFunctions(EffectTimings.BEFORE_ATTACKED):
                if ally == defender:
                    if isinstance(effectFunction, EFBeforeAttacked):
                        effectFunction.applyEffect(self, defender, attacker)
                else:
                    if isinstance(effectFunction, EFBeforeAllyAttacked):
                        effectFunction.applyEffect(self, ally, attacker, defender)

        originalDistance = self.checkDistanceStrict(attacker, defender)
        inRange = self.checkInRange(attacker, defender)
        if not inRange:
            self.logMessage(MessageType.DAMAGE_COMBAT,
                            f"{attacker.name} is out of range of {defender.name}!")

        parryBonusAttacks = None
        parryDamageMultiplier = 1
        guaranteeDodge = False
        if inRange and self.combatStateMap[defender].parryType is not None:
            if attackType == self.combatStateMap[defender].parryType:
                self.logMessage(MessageType.EFFECT,
                                f"{defender.name} reacts to the {attackType.name.lower()} attack!")
                for effectFunction in self.combatStateMap[defender].getEffectFunctions(EffectTimings.PARRY):
                    assert(isinstance(effectFunction, EFOnParry))
                    effectResult = effectFunction.applyEffect(self, defender, attacker, isPhysical)
                    parryBonusAttacks = effectResult.bonusAttacks
                    if effectResult.damageMultiplier is not None:
                        parryDamageMultiplier = effectResult.damageMultiplier
                    if effectResult.guaranteeDodge is not None:
                        self.logMessage(MessageType.PROBABILITY,
                                        f"{attacker.name} is guaranteed to miss {defender.name}!")
                        guaranteeDodge = effectResult.guaranteeDodge
            else:
                self.logMessage(MessageType.EFFECT,
                                f"{defender.name} fails to react to the {attackType.name.lower()} attack!")
            self.combatStateMap[defender].clearParryType()

        checkHit : bool = False
        if inRange and not guaranteeDodge:
            if self.combatStateMap[defender].getTotalStatValue(CombatStats.GUARANTEE_SELF_HIT) == 1:
                self.logMessage(MessageType.PROBABILITY,
                                f"{attacker.name} is guaranteed to hit {defender.name}!")
                checkHit = True
            else:
                checkHit = self.rollForHit(attacker, defender)
        damageDealt : int = 0
        isCritical : bool = False
        if inRange:
            if checkHit:
                damage, isCritical = self.rollForDamage(attacker, defender, isPhysical)
                damage = math.ceil(damage * parryDamageMultiplier)
                damageDealt = self.applyDamage(attacker, defender, damage, isCritical)
            else:
                self.logMessage(MessageType.DAMAGE_COMBAT,
                                f"{attacker.name}'s attack misses {defender.name}!")

        attackResultInfo = AttackResultInfo(attacker, defender, originalDistance, inRange, checkHit, damageDealt,
                                            isCritical, isBonus, isPhysical, attackType)
        if parryBonusAttacks is not None:
            [attackResultInfo.addBonusAttack(*parryAttack) for parryAttack in parryBonusAttacks]

        actionTimerUsage : float = DEFAULT_ATTACK_TIMER_USAGE
        actionTimeMult : float = 1

        for effectFunction in self.combatStateMap[attacker].getEffectFunctions(EffectTimings.AFTER_ATTACK):
            if isinstance(effectFunction, EFAfterNextAttack):
                effectResult = effectFunction.applyEffect(self, attacker, defender, attackResultInfo)
                if effectResult.actionTime is not None:
                    actionTimerUsage = effectResult.actionTime
                if effectResult.actionTimeMult is not None:
                    actionTimeMult = effectResult.actionTimeMult
            elif isinstance(effectFunction, EFBeforeNextAttack_Revert):
                effectFunction.applyEffect(self, attacker, defender, attackResultInfo)
            elif isinstance(effectFunction, EFBeforeAttacked_Revert):
                # note that defender is the user here
                effectFunction.applyEffect(self, defender, attacker)
        for effectFunction in self.combatStateMap[defender].getEffectFunctions(EffectTimings.AFTER_ATTACKED):
            if isinstance(effectFunction, EFWhenAttacked):
                effectFunction.applyEffect(self, defender, attacker, attackResultInfo)

        if isBasic:
            basicMpGain = math.ceil(
                BASIC_ATTACK_MP_GAIN * self.combatStateMap[attacker].getTotalStatValueFloat(CombatStats.BASIC_MP_GAIN_MULT))
            self.gainMana(attacker, basicMpGain)
            self.spendActionTimer(attacker, actionTimerUsage * actionTimeMult)

        return attackResultInfo
    
    """
        Calculates and performs a combat healing skill, performing bonus effects.
    """
    def doHealSkill(self, healer : CombatEntity, target : CombatEntity, healStrength : float):
        healerMag = self.combatStateMap[healer].getTotalStatValue(BaseStats.MAG)
        healerRes = self.combatStateMap[healer].getTotalStatValue(BaseStats.RES)

        critChance : float = self.combatStateMap[healer].getTotalStatValueFloat(CombatStats.CRIT_RATE)
        critDamage : float = self.combatStateMap[healer].getTotalStatValueFloat(CombatStats.CRIT_DAMAGE)
        isCritical : bool = self._randomRoll(None, healer) <= critChance
        critFactor : float = critDamage if isCritical else 1

        rawHealValue = healStrength * math.sqrt(healerMag * healerRes)
        variationFactor : float = self._randomRollUniform(0.9, 1.1, healer, None)
        baseHealAmount = math.ceil(rawHealValue * variationFactor * critFactor)
    
        totalHealAmount = self.gainHealth(target, baseHealAmount, isCritical)

        for effectFunction in self.combatStateMap[healer].getEffectFunctions(EffectTimings.ON_HEAL_SKILL):
            if isinstance(effectFunction, EFOnHealSkill):
                effectFunction.applyEffect(self, healer, target, totalHealAmount)
    
    """
        Cleanup after an attack. At the moment, just removes single-attack skills.
    """
    def _cleanupEffects(self, player) -> None:
        for expiredEffect in self.combatStateMap[player].durationCheck():
            self.removeSkillEffect(player, expiredEffect)
            if expiredEffect.expirationMessage is not None:
                self.logMessage(MessageType.EFFECT, f"{player.name}'s {expiredEffect.expirationMessage}")

    """
        Cleanup for beginning of turn. At the moment, just disables defend.
        Should be called when it's a player's turn, unless they are stunned.
    """
    def beginPlayerTurn(self, player) -> None:
        self.logMessage(MessageType.BASIC, f"--__{player.name} turn!__--")
        self.combatStateMap[player].defendActive = False
        for effectFunction in self.combatStateMap[player].getEffectFunctions(EffectTimings.START_TURN):
            if isinstance(effectFunction, EFStartTurn):
                effectFunction.applyEffect(self, player)

    def isStunned(self, player) -> bool:
        return StatusConditionNames.STUN in self.combatStateMap[player].currentStatusEffects
    
    """
        Skips a player's turn when they are stunned, updating state accordingly.
        Call this instead of beginPlayerTurn if stunned.
        Returns true if their turn was skipped (i.e. if they were actually stunned)
    """
    def stunSkipTurn(self, player) -> bool:
        if not self.isStunned(player):
            return False

        self.beginPlayerTurn(player)
        self.logMessage(MessageType.BASIC, f"{player.name} is stunned!")
        self.spendActionTimer(player, MAX_ACTION_TIMER)
        self._endPlayerTurn(player)
        return True

    """
        Cleanup for end of turn. At the moment, mostly just decreases effect durations.
    """
    def _endPlayerTurn(self, player : CombatEntity, skipDurationTick : bool = False) -> None:
        for effectFunction in self.combatStateMap[player].getEffectFunctions(EffectTimings.END_TURN):
            if isinstance(effectFunction, EFEndTurn):
                effectFunction.applyEffect(self, player, skipDurationTick)

        if not skipDurationTick:
            for expiredEffect in self.combatStateMap[player].durationTick(self):
                self.removeSkillEffect(player, expiredEffect)
                if expiredEffect.expirationMessage is not None:
                    self.logMessage(MessageType.EFFECT, f"{player.name}'s {expiredEffect.expirationMessage}")

        self._applyAggroDecay(player)
        self.previousTurnEntity = player

class ActionResultInfo(object):
    def __init__(self, success : ActionSuccessState, startAttack : bool, attackTarget : CombatEntity | None,
                 toggleChanged : bool, newToggle : bool,
                 reactionAttackData : list[tuple[CombatEntity, CombatEntity, AttackSkillData]]) -> None:
        self.success : ActionSuccessState = success
        self.startAttack : bool = startAttack
        self.attackTarget : CombatEntity | None = attackTarget
        self.toggleChanged : bool = toggleChanged
        self.newToggle : bool = newToggle
        self.reactionAttackData : list[tuple[CombatEntity, CombatEntity, AttackSkillData]] = reactionAttackData

class RepositionResultInfo(object):
    def __init__(self, success : bool, changedDistances : dict[CombatEntity, int], startAttack : bool,
                 attackUser : CombatEntity | None, attackTarget : CombatEntity | None, attackData : AttackSkillData | None,
                 additionalAttacks : list[tuple[CombatEntity, CombatEntity, AttackSkillData]]):
        self.success : bool = success
        self.changedDistances : dict[CombatEntity, int] = changedDistances
        self.startAttack : bool = startAttack
        self.attackUser : CombatEntity | None = attackUser
        self.attackTarget : CombatEntity | None = attackTarget
        self.attackData : AttackSkillData | None = attackData
        self.additionalAttacks : list[tuple[CombatEntity, CombatEntity, AttackSkillData]] = additionalAttacks

class AttackResultInfo(object):
    def __init__(self, attacker : CombatEntity, defender : CombatEntity, originalDistance : int, inRange : bool,
                 attackHit : bool, damageDealt : int, isCritical : bool, isBonus : bool,
                 isPhysical : bool, attackType : AttackType) -> None:
        self.attacker : CombatEntity = attacker
        self.defender : CombatEntity = defender
        self.originalDistance : int = originalDistance
        self.inRange : bool = inRange
        self.attackHit : bool = attackHit
        self.damageDealt : int = damageDealt
        self.isCritical : bool = isCritical
        self.isBonus : bool = isBonus
        self.bonusAttacks : list[tuple[CombatEntity, CombatEntity, AttackSkillData]] = []
        self.bonusResultInfo : AttackResultInfo | None = None
        self.repeatAttack : bool = False
        self.isPhysical : bool = isPhysical
        self.attackType : AttackType = attackType

    def setRepeatAttack(self):
        self.repeatAttack = True

    def addBonusAttack(self, user : CombatEntity, target : CombatEntity, attackData : AttackSkillData):
        self.bonusAttacks.append((user, target, attackData))

    def addBonusResultInfo(self, attackResultInfo : AttackResultInfo):
        self.bonusAttacks += attackResultInfo.bonusAttacks

        if self.bonusResultInfo is None:
            self.bonusResultInfo = attackResultInfo
        else:
            self.bonusResultInfo.addBonusResultInfo(attackResultInfo)