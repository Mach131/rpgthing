from __future__ import annotations
from typing import TYPE_CHECKING

from rpg_consts import *
from structures.rpg_combat_entity import Player

if TYPE_CHECKING:
    from rpg_discord_interface import GameSession

class GlobalState(object):
    def __init__(self):
        self.accountDataMap : dict[int, AccountData] = {}

    def registerNewCharacter(self, userId : int, characterName : str, playerClass : BasePlayerClassNames, session : GameSession):
        player : Player = Player(characterName, playerClass)

        if userId in self.accountDataMap:
            self.accountDataMap[userId].allCharacters.append(player)
        else:
            self.accountDataMap[userId] = AccountData(userId, player, session)

class AccountData(object):
    def __init__(self, userId : int, character : Player, session : GameSession):
        self.userId = userId
        self.currentCharacter = character
        self.session = session

        self.allCharacters = [self.currentCharacter]

GLOBAL_STATE = GlobalState()