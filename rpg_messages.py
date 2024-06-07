from __future__ import annotations

from rpg_combat_entity import CombatEntity
from rpg_consts import *


class LogMessage(object):
    def __init__(self, messageType : MessageType, messageText : str):
        self.messageType : MessageType = messageType
        self.messageText : str = messageText

    def getMessageString(self, includeType : bool):
        typeString = f"[{self.messageType.name}] " if includeType else ""
        return typeString + self.messageText

class LogMessageCollection(object):
    def __init__(self, messages : list[LogMessage]):
        self.messages : list[LogMessage] = messages

    def getMessagesString(self, filters : list[MessageType] | None, includeTypes : bool):
        if filters is None:
            filters = [messageType for messageType in MessageType]
        return '\n'.join(map(lambda msg: msg.getMessageString(includeTypes), filter(lambda msg: msg.messageType in filters, self.messages)))

class MessageCollector(object):
    def __init__(self):
        self.allMessages : list[LogMessage] = []
        self.lastSendLength : int = 0

    def addMessage(self, messageType : MessageType, messageText : str) -> None:
        self.allMessages.append(LogMessage(messageType, messageText))

    def getAllMessages(self) -> LogMessageCollection:
        return LogMessageCollection(self.allMessages)
    
    def getNewestMessages(self) -> LogMessageCollection:
        result = LogMessageCollection(self.allMessages[self.lastSendLength:])
        self.lastSendLength = len(self.allMessages)
        return result
    
def makeTeamString(entities : list[CombatEntity]):
    nameList = [entity.name for entity in entities]
    if len(nameList) > 1:
        nameList[-1] = "and " + nameList[-1]
    joiner = " " if len(nameList) <= 2 else ", "
    return joiner.join(nameList)