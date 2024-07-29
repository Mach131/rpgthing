
from __future__ import annotations
from typing import TYPE_CHECKING, Callable

from rpg_consts import *

if TYPE_CHECKING:
    from structures.rpg_combat_state import CombatController
    from structures.rpg_combat_entity import CombatEntity
        
class EntityAI(object):
    def __init__(self, data : dict, decisionFn : Callable[[CombatController, CombatEntity, dict], EntityAIAction]):
        self.data = data
        self.decisionFn = decisionFn
    
    def chooseAction(self, combatController : CombatController, enemy : CombatEntity) -> EntityAIAction:
        return self.decisionFn(combatController, enemy, self.data)
        
class EntityAIAction(object):
    def __init__(self, action : CombatActions, skillIndex : int | None, targetIndices : list[int],
                 actionParameter : int | None, skillSelector : str | None):
        self.action = action
        self.skillIndex = skillIndex
        self.targetIndices = targetIndices
        self.actionParameter = actionParameter
        self.skillSelector = skillSelector