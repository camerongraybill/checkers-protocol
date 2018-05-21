from enum import IntEnum
from abc import ABC, abstractmethod
from typing import Iterable


class Encodable(ABC):

    @staticmethod
    @abstractmethod
    def from_bytes(raw: bytes):
        raise NotImplementedError()

    @abstractmethod
    def to_bytes(self) -> bytes:
        raise NotImplementedError()

    def __eq__(self, other: "Encodable"):
        return self.to_bytes() == other.to_bytes()


class BoardLocation(Encodable):
    def __init__(self, used: bool, promoted: bool, owner: bool):
        self.__used = used
        self.__promoted = promoted
        self.__owner = owner

    @staticmethod
    def from_bytes(raw: bytes):
        raw = int.from_bytes(raw, byteorder='big')
        if raw & 4 == 0:
            return None
        return BoardLocation(bool(raw & 4), bool(raw & 2), bool(raw & 1))

    def to_bytes(self):
        return bytes([self.__used << 2 | self.__promoted << 1 | self.__owner])

    @property
    def used(self):
        return self.__used

    @property
    def promoted(self):
        return self.__promoted

    @property
    def owner(self):
        return self.__owner


class Board(Encodable):
    def __init__(self, locations: Iterable[BoardLocation]):
        self.__state = [[BoardLocation(False, False, False)] * 8] * 8
        i = 0
        for v in locations:
            if i == 64:
                raise TypeError()
            self.__state[i // 8][i % 8] = v
            i += 1

    @staticmethod
    def from_bytes(raw: bytes) -> "Board":
        raw = int.from_bytes(raw, byteorder="big")
        return Board((BoardLocation.from_bytes(bytes([(raw >> (i * 3)) & 0x07]))) for i in reversed(range(64)))

    def to_bytes(self):
        output_val = 0
        for i in reversed(range(64)):
            output_val |= (int.from_bytes(self.__state[i // 8][i % 8].to_bytes(), byteorder='big') << (i * 3))
        return output_val.to_bytes(length=24, byteorder='big')


class Direction(IntEnum):
    Negative = 0x00
    Positive = 0x01


class Move(Encodable):
    def __init__(self, x_pos: int, y_pos: int, x_direction: Direction, y_direction: Direction):
        self.__x_pos = x_pos
        self.__y_pos = y_pos
        self.__x_direction = x_direction
        self.__y_direction = y_direction

    @staticmethod
    def from_bytes(raw: bytes) -> "Move":
        raw = int.from_bytes(raw, byteorder='big')
        return Move((raw & (0x07 << 5)) >> 5, (raw & (0x07 << 2)) >> 2, Direction((raw & 0x02) >> 1), Direction(raw & 0x01))

    def to_bytes(self) -> bytes:
        return bytes([((self.x_pos & 0x07) << 5) | ((self.y_pos & 0x07) << 2) | ((self.x_direction & 0x01) << 1) | (self.y_direction & 0x01)])

    @property
    def x_pos(self):
        return self.__x_pos

    @property
    def y_pos(self):
        return self.__y_pos

    @property
    def x_direction(self):
        return self.__x_direction

    @property
    def y_direction(self):
        return self.__y_direction
