"""
This file contains the all of the Messages objects to send between client and server
They represent the PDUs from the spec
"""
from abc import ABC
from enum import IntEnum
from struct import unpack, pack, calcsize
from typing import List, Any

from internal_types.types import Board, Move, Encodable


# Exceptions
class ParseError(RuntimeError):
    """ Raised when there is an error parsing """


class NotEnoughData(ParseError):
    """ Raised when a message fails to parse because it does not have enough data """


class InvalidType(ParseError):
    """ Raised when you try to parse an invalid message """


# Helper function
def bytes_strip(buf: bytes) -> bytes:
    """
    Strip '\x00' from a buffer of bytes
    :param buf: The buffer to strip null characters from
    :return: buf without null characters on the right
    """
    if b'\x00' in buf:
        return buf[:buf.find(b'\x00')]
    else:
        return buf


# Messages
class Message(ABC):
    """
    Generic abstract class for network messages
    All Messages must have a format and type
    """
    fmt: str = ""
    type: int = -1

    def __init__(self, *args: Any):
        """
        Constructor for Abstract Message
        Takes in all args that were given to the concrete message and stores them to later be packed
        :param args: Store these to later pack
        """
        self.__args: List[Any] = [x.to_bytes() if isinstance(x, Encodable) else x for x in args]

    @classmethod
    def calc_size(cls) -> int:
        """
        Calculate the size of this message
        NOTE: Size does not include the type field
        :return: The calculated size of the message
        """
        return calcsize('<' + cls.fmt)

    @classmethod
    def parse_and_decode(cls, data: bytes) -> "Message":
        """
        Given a buffer, parse it and return a new instance of the correct message class from the data
        :param data: Binary data to parse
        :return: New instance of a concrete Message
        """
        if len(data) < cls.calc_size() + 1:
            raise NotEnoughData()
        if data[0] != cls.type:
            raise InvalidType()
        return cls(*unpack('<' + cls.fmt, data[1:cls.calc_size() + 1]))

    def encode(self) -> bytes:
        """
        Take the stored __args and pack them into a buffer based on the Message's format
        :return: Buffer of bytes based on the format
        """
        return pack('<B' + self.fmt, *([self.type] + self.__args))

    def __repr__(self) -> str:
        return "{}({})".format(self.__class__.__name__, self.__args)


class Connect(Message):
    """
    Message sent from client to server when connecting to the server
    """
    fmt: str = "B16s16s"
    type: int = 0x01

    def __init__(self, version: int, username: bytes, password: bytes):
        super(Connect, self).__init__(version, username, password)
        self.__version: int = version
        self.__username: bytes = username
        self.__password: bytes = password

    @property
    def version(self) -> int:
        return self.__version

    @property
    def username(self) -> bytes:
        return self.__username

    @property
    def password(self) -> bytes:
        return self.__password

    @classmethod
    def parse_and_decode(cls, data: bytes) -> "Connect":
        if len(data) < cls.calc_size() + 1:
            raise NotEnoughData()
        if data[0] != cls.type:
            raise InvalidType()
        res = unpack('<' + cls.fmt, data[1:cls.calc_size() + 1])
        return cls(res[0], bytes_strip(res[1]), bytes_strip(res[2]))


class InvalidLogin(Message):
    """
    Message sent from Server to Client if the Client passes invalid login information
    """
    fmt: str = "B"
    type: int = 0x02

    class Reasons(IntEnum):
        """
        Valid response codes for reasons why a user failed to log in
        """
        AccountDoesNotExist = 0x00
        InvalidPassword = 0x01
        AlreadyLoggedIn = 0x02

    def __init__(self, reason: Reasons):
        super(InvalidLogin, self).__init__(reason)
        self.__reason: InvalidLogin.Reasons = reason

    @classmethod
    def parse_and_decode(cls, data: bytes) -> "InvalidLogin":
        if len(data) < cls.calc_size() + 1:
            raise NotEnoughData()
        if data[0] != cls.type:
            raise InvalidType()
        res = unpack('<' + cls.fmt, data[1:cls.calc_size() + 1])
        return cls(InvalidLogin.Reasons(res[0]))

    @property
    def reason(self) -> "InvalidLogin.Reasons":
        return self.__reason


class InvalidVersion(Message):
    """
    Message sent from server to client when the client attempted to connect with an invalid version
    """
    fmt: str = "BB"
    type: int = 0x0D

    def __init__(self, highest_supported_version: int, lowest_supported_version: int):
        super(InvalidVersion, self).__init__(highest_supported_version, lowest_supported_version)
        self.__highest_supported_version = highest_supported_version
        self.__lowest_supported_version = lowest_supported_version

    @property
    def highest_supported_version(self) -> int:
        return self.__highest_supported_version

    @property
    def lowest_supported_version(self) -> int:
        return self.__lowest_supported_version


class QueuePosition(Message):
    """
    Message sent from server to client to tell the client what position in the queue it is
    """
    fmt: str = "III"
    type: int = 0x03

    def __init__(self, queue_size: int, queue_pos: int, rating: int):
        super(QueuePosition, self).__init__(queue_size, queue_pos, rating)
        self.__queue_size = queue_size
        self.__queue_pos = queue_pos
        self.__rating = rating

    @property
    def queue_size(self) -> int:
        return self.__queue_size

    @property
    def queue_pos(self) -> int:
        return self.__queue_pos

    @property
    def rating(self) -> int:
        return self.__rating


class GameStart(Message):
    fmt: str = "16sI"
    type: int = 0x04

    def __init__(self, opponent_name: bytes, opponent_rating: int):
        super(GameStart, self).__init__(opponent_name, opponent_rating)
        self.__opponent_name = opponent_name
        self.__opponent_rating = opponent_rating

    @property
    def opponent_name(self) -> bytes:
        return self.__opponent_name

    @property
    def opponent_rating(self) -> int:
        return self.__opponent_rating

    @classmethod
    def parse_and_decode(cls, data: bytes) -> "GameStart":
        if len(data) < cls.calc_size() + 1:
            raise NotEnoughData()
        if data[0] != cls.type:
            raise InvalidType()
        res = unpack('<' + cls.fmt, data[1:cls.calc_size() + 1])
        return cls(bytes_strip(res[0]), res[1])


class YourTurn(Message):
    fmt: str = "c24s"
    type: int = 0x05

    def __init__(self, last_move: Move, board: Board):
        super(YourTurn, self).__init__(last_move, board)
        self.__last_move = last_move
        self.__board = board

    @property
    def last_move(self) -> Move:
        return self.__last_move

    @property
    def board(self) -> Board:
        return self.__board

    @classmethod
    def parse_and_decode(cls, data: bytes) -> "YourTurn":
        if len(data) < cls.calc_size() + 1:
            raise NotEnoughData()
        if data[0] != cls.type:
            raise InvalidType()
        res = unpack('<' + cls.fmt, data[1:cls.calc_size() + 1])
        return cls(Move.from_bytes(res[0]), Board.from_bytes(res[1]))


class MakeMove(Message):
    fmt: str = "c"
    type: int = 0x06

    def __init__(self, move: Move):
        super(MakeMove, self).__init__(move)
        self.__move = move

    @property
    def move(self) -> Move:
        return self.__move

    @classmethod
    def parse_and_decode(cls, data: bytes) -> "MakeMove":
        if len(data) < cls.calc_size() + 1:
            raise NotEnoughData()
        if data[0] != cls.type:
            raise InvalidType()
        res = unpack('<' + cls.fmt, data[1:cls.calc_size() + 1])
        return cls(Move.from_bytes(res[0]))


class CompulsoryMove(Message):
    fmt: str = "c24s"
    type: int = 0x07

    def __init__(self, move: Move, board: Board):
        super(CompulsoryMove, self).__init__(move, board)
        self.__move = move
        self.__board = board

    @property
    def move(self) -> Move:
        return self.__move

    @property
    def board(self) -> Board:
        return self.__board

    @classmethod
    def parse_and_decode(cls, data: bytes) -> "CompulsoryMove":
        if len(data) < cls.calc_size() + 1:
            raise NotEnoughData()
        if data[0] != cls.type:
            raise InvalidType()
        res = unpack('<' + cls.fmt, data[1:cls.calc_size() + 1])
        return cls(Move.from_bytes(res[0]), Board.from_bytes(res[1]))


class InvalidMove(Message):
    fmt: str = "c24s"
    type: int = 0x08

    def __init__(self, move: Move, board: Board):
        super(InvalidMove, self).__init__(move, board)
        self.__move = move
        self.__board = board

    @property
    def move(self) -> Move:
        return self.__move

    @property
    def board(self) -> "Board":
        return self.__board

    @classmethod
    def parse_and_decode(cls, data: bytes) -> "InvalidMove":
        if len(data) < cls.calc_size() + 1:
            raise NotEnoughData()
        if data[0] != cls.type:
            raise InvalidType()
        res = unpack('<' + cls.fmt, data[1:cls.calc_size() + 1])
        return cls(Move.from_bytes(res[0]), Board.from_bytes(res[1]))


class OpponentDisconnect(Message):
    fmt: str = ""
    type: int = 0x09

    def __init__(self):
        super(OpponentDisconnect, self).__init__()


class GameOver(Message):
    fmt: str = "BIIc24s"
    type: int = 0x0A

    def __init__(self, you_won: int, new_rating: int, old_rating: int, winning_move: Move, board: Board):
        super(GameOver, self).__init__(you_won, new_rating, old_rating, winning_move, board)
        self.__you_won = you_won
        self.__new_rating = new_rating
        self.__old_rating = old_rating
        self.__winning_move = winning_move
        self.__board = board

    @property
    def you_won(self) -> int:
        return self.__you_won

    @property
    def new_rating(self) -> int:
        return self.__new_rating

    @property
    def old_rating(self) -> int:
        return self.__old_rating

    @property
    def winning_move(self) -> Move:
        return self.__winning_move

    @property
    def board(self) -> Board:
        return self.__board

    @classmethod
    def parse_and_decode(cls, data: bytes) -> "GameOver":
        if len(data) < cls.calc_size() + 1:
            raise NotEnoughData()
        if data[0] != cls.type:
            raise InvalidType()
        res = unpack('<' + cls.fmt, data[1:cls.calc_size() + 1])
        return cls(res[0], res[1], res[2], Move.from_bytes(res[3]), Board.from_bytes(res[4]))


class ReQueue(Message):
    fmt: str = ""
    type: int = 0x0B

    def __init__(self):
        super(ReQueue, self).__init__()


class LogOut(Message):
    fmt: str = ""
    type: int = 0x0C

    def __init__(self):
        super(LogOut, self).__init__()


__type_to_message = {
    0x01: Connect,
    0x02: InvalidLogin,
    0x0D: InvalidVersion,
    0x03: QueuePosition,
    0x04: GameStart,
    0x05: YourTurn,
    0x06: MakeMove,
    0x07: CompulsoryMove,
    0x08: InvalidMove,
    0x09: OpponentDisconnect,
    0x0A: GameOver,
    0x0B: ReQueue,
    0x0C: LogOut
}


def message_to_type(raw: bytes) -> Message:
    """
    Return the correct constructor for a message based on it's message type
    :param raw: The raw buffer of bytes, where the first byte is the message type
    :return: A Message constructor
    """
    return __type_to_message[raw[0]]
