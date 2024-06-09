from __future__ import annotations
from typing import TYPE_CHECKING

from rpg_consts import *
if TYPE_CHECKING:
    from rpg_combat_entity import CombatEntity


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

    def sendAllMessages(self, filters : list[MessageType] | None, includeTypes : bool) -> LogMessageCollection:
        result = LogMessageCollection(self.allMessages)
        return result
    
    def sendNewestMessages(self, filters : list[MessageType] | None, includeTypes : bool) -> LogMessageCollection:
        result = LogMessageCollection(self.allMessages[self.lastSendLength:])
        self.lastSendLength = len(self.allMessages)
        return result
    
class LocalMessageCollector(MessageCollector):
    def __init__(self):
        super().__init__()

    def sendAllMessages(self, filters : list[MessageType] | None, includeTypes : bool) -> LogMessageCollection:
        result = super().sendAllMessages(filters, includeTypes)
        print(result.getMessagesString(filters, includeTypes))
        return result
    
    def sendNewestMessages(self, filters : list[MessageType] | None, includeTypes : bool) -> LogMessageCollection:
        result = super().sendNewestMessages(filters, includeTypes)
        print(result.getMessagesString(filters, includeTypes))
        return result

# eventually have a child class that does whatever networking instead of just printing
    
def makeTeamString(entities : list[CombatEntity]):
    nameList = [entity.name for entity in entities]
    if len(nameList) > 1:
        nameList[-1] = "and " + nameList[-1]
    joiner = " " if len(nameList) <= 2 else ", "
    return joiner.join(nameList)