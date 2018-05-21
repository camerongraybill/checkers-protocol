from enum import IntEnum


class ProtocolState(IntEnum):
    UNAUTHENTICATED = 1
    IN_QUEUE = 2
    PROCESSING_GAME_STATE = 3
    USER_MOVE = 4
    GAME_END = 5
