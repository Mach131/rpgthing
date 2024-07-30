from __future__ import annotations
import os
import random
import shutil
import dill as pickle
from typing import TYPE_CHECKING
from datetime import datetime

from rpg_consts import *
from structures.rpg_combat_entity import Player
from structures.rpg_dungeons import DungeonData

CURRENT_VERSION = "0.1.4"

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
        
        if not os.path.exists(STATE_FILE_FOLDER):
            os.mkdir(STATE_FILE_FOLDER)

        # Archive old files
        saveFiles = [f for f in os.listdir(STATE_FILE_FOLDER) if f.startswith(STATE_FILE_NAME) and f != STATE_FILE_NAME + "ts"]
        saveFiles.sort()
        print(saveFiles)
        if len(saveFiles) > ARCHIVE_SIZE + 1:
            if os.path.exists(STATE_ARCHIVE_FOLDER):
                shutil.rmtree(STATE_ARCHIVE_FOLDER)
            os.mkdir(STATE_ARCHIVE_FOLDER)
            for file in saveFiles[:-1]:
                os.rename(STATE_FILE_FOLDER + file, STATE_ARCHIVE_FOLDER + file)

        # Save new file, update timestamp tracker
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
            timestampFile.write(str(timestamp) + "\n" + CURRENT_VERSION)

        print(f"state saved at {timestamp}")

    def loadState(self):
        try:
            lastSaveTimestamp = None
            lastSaveVersion = None
            with open(GlobalState.TS_FILENAME, 'r') as tsFile:
                tsFileData = tsFile.read().split("\n")
                lastSaveTimestamp = int(tsFileData[0])
                if len(tsFileData) > 1:
                    lastSaveVersion = tsFileData[1]

            if lastSaveTimestamp is not None:
                filename = STATE_FILE_PREFIX + str(lastSaveTimestamp)
                with open(filename, 'rb') as saveFile:
                    self.accountDataMap = pickle.load(saveFile)
                
                for accountData in self.accountDataMap.values():
                    for character in accountData.allCharacters:
                        character._updateAvailableSkills()
                    accountData.session.onLoadReset()

                    # Upgrades
                    if lastSaveVersion != CURRENT_VERSION:
                        for character in accountData.allCharacters:
                            character.summonName = random.choice(DEFAULT_SUMMON_NAMES)
                            for secretClassName in SecretPlayerClassNames:
                                character.classRanks[secretClassName] = 1
                                character.classExp[secretClassName] = 0

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