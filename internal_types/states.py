"""
STATEFUL
This file has the ProtocolState enum used in both the client and server
to show what state of the protocol they are in
"""
from enum import IntEnum


class ProtocolState(IntEnum):
    # Unauthenticated
    UNAUTHENTICATED = 1
    # In Queue
    IN_QUEUE = 2
    # Processing Game State
    PROCESSING_GAME_STATE = 3
    # User Move
    USER_MOVE = 4
    # Game End
    GAME_END = 5
