from __future__ import annotations
import dill as pickle
from typing import TYPE_CHECKING
from datetime import datetime

from rpg_consts import *
from structures.rpg_combat_entity import Player
from structures.rpg_dungeons import DungeonData

if TYPE_CHECKING:
    from rpg_discord_interface import GameSession

class GlobalState(object):
    TS_FILENAME = STATE_FILE_PREFIX + "ts"

    def __init__(self):
        self.accountDataMap : dict[int, AccountData] = {}
        self.loaded = False
        self.firstSave = False

    def idRegistered(self, id : int) -> bool:
        return id in self.accountDataMap and len(self.accountDataMap[id].allCharacters) > 0

    def registerNewCharacter(self, userId : int, characterName : str, playerClass : BasePlayerClassNames, session : GameSession):
        player : Player = Player(characterName, playerClass)

        if userId in self.accountDataMap:
            self.accountDataMap[userId].allCharacters.append(player)
            self.accountDataMap[userId].currentCharacter = player
        else:
            self.accountDataMap[userId] = AccountData(userId, player, session)

    def saveState(self):
        if len(self.accountDataMap) == 0:
            return

        timestamp = int(datetime.now().timestamp())

        # if len(self.accountDataMap) > 0:
        #     print(pickle.detect.baditems(list(self.accountDataMap.values())[0]))
        # # pickle.detect.trace(True)
        # errors = pickle.detect.errors(self.accountDataMap)
        # if isinstance(errors, BaseException):
        #     raise errors

        filename = STATE_FILE_PREFIX + str(timestamp)
        with open(filename, 'wb') as saveFile:
            pickle.dump(self.accountDataMap, saveFile, protocol=pickle.HIGHEST_PROTOCOL)

        with open(GlobalState.TS_FILENAME, 'w') as timestampFile:
            timestampFile.write(str(timestamp))

        print(f"state saved at {timestamp}")

    def loadState(self):
        try:
            lastSaveTimestamp = None
            with open(GlobalState.TS_FILENAME, 'r') as tsFile:
                lastSaveTimestamp = int(tsFile.read())

            if lastSaveTimestamp is not None:
                filename = STATE_FILE_PREFIX + str(lastSaveTimestamp)
                with open(filename, 'rb') as saveFile:
                    self.accountDataMap = pickle.load(saveFile)
                
                for accountData in self.accountDataMap.values():
                    accountData.session.onLoadReset()

                # # temp
                # availableDungeons = DungeonData.registeredDungeons
                # flags = [
                #     Milestones.TUTORIAL_COMPLETE,
                #     Milestones.FRESH_FIELDS_COMPLETE,
                #     Milestones.SKYLIGHT_CAVE_COMPLETE,
                #     Milestones.SAFFRON_FOREST_COMPLTE,
                #     Milestones.ABANDONED_STOREHOUSE_COMPLETE
                # ]
                # for i in range(len(flags)):
                #     availableDungeons[i].clearFlag = flags[i]

                print(f"loaded state from {lastSaveTimestamp}")
        except FileNotFoundError:
            print("unable to load previous state")

        self.loaded = True

    def deleteCharacter(self, userId, character):
        if userId not in self.accountDataMap:
            return
        accountData = self.accountDataMap[userId]
        accountData.allCharacters.remove(character)
        if accountData.currentCharacter == character:
            if len(accountData.allCharacters) > 0:
                accountData.currentCharacter = accountData.allCharacters[0]

class AccountData(object):
    def __init__(self, userId : int, character : Player, session : GameSession):
        self.userId = userId
        self.currentCharacter = character
        self.session = session

        self.enabledLogFilters : set[MessageType] = set()
        for logFilter in MessageType:
            if logFilter in TOGGLE_LOG_FILTER_DEFAULTS:
                if TOGGLE_LOG_FILTER_DEFAULTS.get(logFilter, True):
                    self.enabledLogFilters.add(logFilter)
            else:
                    self.enabledLogFilters.add(logFilter)

        self.allCharacters = [self.currentCharacter]

GLOBAL_STATE = GlobalState()