from enum import IntEnum
from struct import unpack, pack

from internal_types.types import Board, Move, Encodable


class ParseError(RuntimeError):
    """ Raised when there is an error parsing """


class NotEnoughData(ParseError):
    """ Raised when a message fails to parse because it does not have enough data """


class InvalidType(ParseError):
    """ Raised when you try to parse an invalid message """


def bytes_strip(buf):
    if b'\x00' in buf:
        return buf[:buf.find(b'\x00')]
    else:
        return buf


class Message:
    fmt: str = ""
    size: int = 0
    type: int = -1

    def __init__(self, *args):
        self.__args = [x.to_bytes() if isinstance(x, Encodable) else x for x in args]

    @classmethod
    def parse_and_decode(cls, data: bytes) -> "Message":
        if len(data) < cls.size + 1:
            raise NotEnoughData()
        if data[0] != cls.type:
            raise InvalidType()
        return cls(*unpack('<' + cls.fmt, data[1:]))

    def encode(self) -> bytes:
        return pack('<B' + self.fmt, *([self.type] + self.__args))


class Connect(Message):
    fmt: str = "B16s16s"
    size: int = 33
    type: int = 0x01

    def __init__(self, version: int, username: bytes, password: bytes):
        super(Connect, self).__init__(version, username, password)
        self.__version = version
        self.__username = username
        self.__password = password

    @property
    def version(self):
        return self.__version

    @property
    def username(self):
        return self.__username

    @property
    def password(self):
        return self.__password

    @classmethod
    def parse_and_decode(cls, data: bytes):
        if len(data) < cls.size + 1:
            raise NotEnoughData()
        if data[0] != cls.type:
            raise InvalidType()
        res = unpack('<' + cls.fmt, data[1:])
        return cls(res[0], bytes_strip(res[1]), bytes_strip(res[2]))


class InvalidLogin(Message):
    fmt: str = "B"
    size: int = 1
    type: int = 0x02

    class Reasons(IntEnum):
        AccountDoesNotExist = 0x00
        InvalidPassword = 0x01

    def __init__(self, reason: Reasons):
        super(InvalidLogin, self).__init__(reason)
        self.__reason = reason

    @property
    def reason(self):
        return self.__reason


class InvalidVersion(Message):
    fmt: str = "BB"
    size: int = 2
    type: int = 0x0D

    def __init__(self, highest_supported_version: int, lowest_supported_version: int):
        super(InvalidVersion, self).__init__(highest_supported_version, lowest_supported_version)
        self.__highest_supported_version = highest_supported_version
        self.__lowest_supported_version = lowest_supported_version

    @property
    def highest_supported_version(self):
        return self.__highest_supported_version

    @property
    def lowest_supported_version(self):
        return self.__lowest_supported_version


class QueuePosition(Message):
    fmt: str = "III"
    size: int = 12
    type: int = 0x03

    def __init__(self, queue_size: int, queue_pos: int, rating: int):
        super(QueuePosition, self).__init__(queue_size, queue_pos, rating)
        self.__queue_size = queue_size
        self.__queue_pos = queue_pos
        self.__rating = rating

    @property
    def queue_size(self):
        return self.__queue_size

    @property
    def queue_pos(self):
        return self.__queue_pos

    @property
    def rating(self):
        return self.__rating


class GameStart(Message):
    fmt: str = "16sI"
    size: int = 20
    type: int = 0x04

    def __init__(self, opponent_name: bytes, opponent_rating: int):
        super(GameStart, self).__init__(opponent_name, opponent_rating)
        self.__opponent_name = opponent_name
        self.__opponent_rating = opponent_rating

    @property
    def opponent_name(self):
        return self.__opponent_name

    @property
    def opponent_rating(self):
        return self.__opponent_rating

    @classmethod
    def parse_and_decode(cls, data: bytes):
        if len(data) < cls.size + 1:
            raise NotEnoughData()
        if data[0] != cls.type:
            raise InvalidType()
        res = unpack('<' + cls.fmt, data[1:])
        return cls(bytes_strip(res[0]), res[1])


class YourTurn(Message):
    fmt: str = "c24s"
    size: int = 25
    type: int = 0x05

    def __init__(self, last_move: Move, board: Board):
        super(YourTurn, self).__init__(last_move, board)
        self.__last_move = last_move
        self.__board = board

    @property
    def last_move(self):
        return self.__last_move

    @property
    def board(self):
        return self.__board

    @classmethod
    def parse_and_decode(cls, data: bytes):
        if len(data) < cls.size + 1:
            raise NotEnoughData()
        if data[0] != cls.type:
            raise InvalidType()
        res = unpack('<' + cls.fmt, data[1:])
        return cls(Move.from_bytes(res[0]), Board.from_bytes(res[1]))


class MakeMove(Message):
    fmt: str = "c"
    size: int = 1
    type: int = 0x06

    def __init__(self, move: Move):
        super(MakeMove, self).__init__(move)
        self.__move = move

    @property
    def move(self):
        return self.__move

    @classmethod
    def parse_and_decode(cls, data: bytes):
        if len(data) < cls.size + 1:
            raise NotEnoughData()
        if data[0] != cls.type:
            raise InvalidType()
        res = unpack('<' + cls.fmt, data[1:])
        return cls(Move.from_bytes(res[0]))


class CompulsoryMove(Message):
    fmt: str = "c24s"
    size: int = 25
    type: int = 0x07

    def __init__(self, move: Move, board: Board):
        super(CompulsoryMove, self).__init__(move, board)
        self.__move = move
        self.__board = board

    @property
    def move(self):
        return self.__move

    @property
    def board(self):
        return self.__board

    @classmethod
    def parse_and_decode(cls, data: bytes):
        if len(data) < cls.size + 1:
            raise NotEnoughData()
        if data[0] != cls.type:
            raise InvalidType()
        res = unpack('<' + cls.fmt, data[1:])
        return cls(Move.from_bytes(res[0]), Board.from_bytes(res[1]))


class InvalidMove(Message):
    fmt: str = "c24s"
    size: int = 25
    type: int = 0x08

    def __init__(self, move: Move, board: Board):
        super(InvalidMove, self).__init__(move, board)
        self.__move = move
        self.__board = board

    @property
    def move(self):
        return self.__move

    @property
    def board(self):
        return self.__board

    @classmethod
    def parse_and_decode(cls, data: bytes):
        if len(data) < cls.size + 1:
            raise NotEnoughData()
        if data[0] != cls.type:
            raise InvalidType()
        res = unpack('<' + cls.fmt, data[1:])
        return cls(Move.from_bytes(res[0]), Board.from_bytes(res[1]))


class OpponentDisconnect(Message):
    fmt: str = ""
    size: int = 0
    type: int = 0x09

    def __init__(self):
        super(OpponentDisconnect, self).__init__()


class GameOver(Message):
    fmt: str = "BIIc24s"
    size: int = 34
    type: int = 0x0A

    def __init__(self, you_won: int, new_rating: int, old_rating: int, winning_move: Move, board: Board):
        super(GameOver, self).__init__(you_won, new_rating, old_rating, winning_move, board)
        self.__you_won = you_won
        self.__new_rating = new_rating
        self.__old_rating = old_rating
        self.__winning_move = winning_move
        self.__board = board

    @property
    def you_won(self):
        return self.__you_won

    @property
    def new_rating(self):
        return self.__new_rating

    @property
    def old_rating(self):
        return self.__old_rating

    @property
    def winning_move(self):
        return self.__winning_move

    @property
    def board(self):
        return self.__board

    @classmethod
    def parse_and_decode(cls, data: bytes):
        if len(data) < cls.size + 1:
            raise NotEnoughData()
        if data[0] != cls.type:
            raise InvalidType()
        res = unpack('<' + cls.fmt, data[1:])
        return cls(res[0], res[1], res[2], Move.from_bytes(res[3]), Board.from_bytes(res[4]))


class ReQueue(Message):
    fmt: str = ""
    size: int = 0
    type: int = 0x0B

    def __init__(self):
        super(ReQueue, self).__init__()


class LogOut(Message):
    fmt: str = ""
    size: int = 0
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
    return __type_to_message[raw[0]]
