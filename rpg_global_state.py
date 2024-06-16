from __future__ import annotations
import dill as pickle
from typing import TYPE_CHECKING
from datetime import datetime

from rpg_consts import *
from structures.rpg_combat_entity import Player

if TYPE_CHECKING:
    from rpg_discord_interface import GameSession

class GlobalState(object):
    TS_FILENAME = STATE_FILE_PREFIX + "ts"

    def __init__(self):
        self.accountDataMap : dict[int, AccountData] = {}
        self.loaded = False
        self.firstSave = False

    def registerNewCharacter(self, userId : int, characterName : str, playerClass : BasePlayerClassNames, session : GameSession):
        player : Player = Player(characterName, playerClass)

        if userId in self.accountDataMap:
            self.accountDataMap[userId].allCharacters.append(player)
        else:
            self.accountDataMap[userId] = AccountData(userId, player, session)

    def saveState(self):
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

                print(f"loaded state from {lastSaveTimestamp}")
        except FileNotFoundError:
            print("unable to load previous state")

        self.loaded = True

class AccountData(object):
    def __init__(self, userId : int, character : Player, session : GameSession):
        self.userId = userId
        self.currentCharacter = character
        self.session = session

        self.allCharacters = [self.currentCharacter]

GLOBAL_STATE = GlobalState()