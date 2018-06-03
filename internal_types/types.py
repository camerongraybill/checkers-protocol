from abc import ABC, abstractmethod
from copy import deepcopy
from enum import IntEnum
from typing import Iterable, Tuple, Union, List, Iterator


class Encodable(ABC):

    @staticmethod
    @abstractmethod
    def from_bytes(raw: bytes) -> "Encodable":
        raise NotImplementedError()

    @abstractmethod
    def to_bytes(self) -> bytes:
        raise NotImplementedError()

    def __eq__(self, other: "Encodable"):
        return self.to_bytes() == other.to_bytes()

    def __repr__(self) -> str:
        return str(self.to_bytes())

    def __str__(self) -> str:
        return str(self.to_bytes())


class BoardLocation(Encodable):
    def __init__(self, used: bool, promoted: bool, owner: bool):
        self.__used = used
        self.__promoted = promoted
        self.__owner = owner

    @staticmethod
    def from_bytes(raw: bytes) -> "BoardLocation":
        raw = int.from_bytes(raw, byteorder='big')
        return BoardLocation(bool(raw & 4), bool(raw & 2), bool(raw & 1))

    def to_bytes(self) -> bytes:
        return bytes([self.__used << 2 | self.__promoted << 1 | self.__owner])

    @property
    def used(self) -> bool:
        return self.__used

    @property
    def promoted(self) -> bool:
        return self.__promoted

    @property
    def owner(self) -> bool:
        return self.__owner


class Direction(IntEnum):
    Negative = 0x00
    Positive = 0x01

    @property
    def to_one(self) -> int:
        if self == Direction.Positive:
            return 1
        elif self == Direction.Negative:
            return -1
        else:
            raise TypeError()

    def __repr__(self):
        return str(self.to_one)


class Move(Encodable):
    def __init__(self, x_pos: int, y_pos: int, x_direction: Direction, y_direction: Direction):
        self.__x_pos = x_pos
        self.__y_pos = y_pos
        self.__x_direction = x_direction
        self.__y_direction = y_direction

    @staticmethod
    def from_bytes(raw: bytes) -> "Move":
        raw = int.from_bytes(raw, byteorder='big')
        return Move((raw & (0x07 << 5)) >> 5, (raw & (0x07 << 2)) >> 2, Direction((raw & 0x02) >> 1),
                    Direction(raw & 0x01))

    def to_bytes(self) -> bytes:
        return bytes([((self.x_pos & 0x07) << 5) | ((self.y_pos & 0x07) << 2) | ((self.x_direction & 0x01) << 1) | (
                self.y_direction & 0x01)])

    @property
    def x_pos(self) -> int:
        return self.__x_pos

    @property
    def y_pos(self) -> int:
        return self.__y_pos

    @property
    def x_direction(self) -> Direction:
        return self.__x_direction

    @property
    def y_direction(self) -> Direction:
        return self.__y_direction

    @property
    def pos(self) -> Tuple[int, int]:
        return self.x_pos, self.y_pos

    @property
    def after_move_pos(self) -> Tuple[int, int]:
        return self.x_pos + self.x_direction.to_one, self.y_pos + self.y_direction.to_one

    @property
    def after_double_move_pos(self) -> Tuple[int, int]:
        return self.x_pos + 2 * self.x_direction.to_one, self.y_pos + 2 * self.y_direction.to_one

    def __repr__(self):
        return str("{} -> {}".format(tuple([x + 1 for x in self.pos]), tuple([x + 1 for x in self.after_move_pos])))


class InvalidMove(RuntimeError):
    """ Raised when an invalid move is applied """


class Board(Encodable):
    def __init__(self, locations: Iterable[BoardLocation]):
        self.__state: List[List[BoardLocation]] = [x[:] for x in [[None] * 8] * 8]
        locations = list(locations)
        if len(locations) != 64:
            raise TypeError()
        for i in range(64):
            self.__state[i // 8][i % 8] = locations[i]

    @staticmethod
    def generate_game_start() -> "Board":
        """ Created from the point of view of the player moving top to bottom"""
        b = Board([BoardLocation(False, False, False)] * 64)
        for i in range(12):
            b[((i % 4) * 2) + ((i // 4) % 2), i // 4] = BoardLocation(True, False, False)
            b[((i % 4) * 2) + (((i // 4) + 1) % 2), 7 - (i // 4)] = BoardLocation(True, False, True)

        return b

    @staticmethod
    def from_bytes(raw: bytes) -> "Board":
        raw = int.from_bytes(raw, byteorder="big")
        return Board((BoardLocation.from_bytes(bytes([(raw >> (i * 3)) & 0x07]))) for i in reversed(range(64)))

    def to_bytes(self) -> bytes:
        output_val = 0
        for i in reversed(range(64)):
            output_val |= (int.from_bytes(self.__state[i // 8][i % 8].to_bytes(), byteorder='big') << (i * 3))
        return output_val.to_bytes(length=24, byteorder='big')

    def translate_to_other_user(self) -> "Board":
        return Board(
            (BoardLocation(x.used, x.promoted, (not x.owner) if x.used else False) for x in self.iterate_in_order()))

    def iterate_in_order(self) -> Iterator[BoardLocation]:
        for i in range(8):
            for j in range(8):
                yield self.__state[i][j]

    def get_possible_moves(self, allowed_y_direction: Direction = Direction.Positive, is_primary_payer: bool = True):
        retval = []
        print("Finding legal moves: ")
        for i in range(8):
            for j in range(8):
                if self[i, j].used and (self[i, j].owner == is_primary_payer):
                    for d in [(Direction.Positive, Direction.Positive), (Direction.Positive, Direction.Negative),
                              (Direction.Negative, Direction.Positive), (Direction.Negative, Direction.Negative)]:
                        m = Move(i, j, *d)
                        try:
                            deepcopy(self).apply_move(m, allowed_y_direction, is_primary_payer)
                            retval.append(m)
                        except InvalidMove:
                            pass
        print(retval)
        return retval

    def check_game_over(self, is_primary_user: bool):
        return all(x.owner == is_primary_user for x in self.iterate_in_order() if x.used)

    def get_required_moves(self, allowed_y_direction: Direction = Direction.Positive, is_primary_payer: bool = True):
        def is_required(move: Move):
            try:
                move_plus_one = self[move.after_move_pos]
                move_plus_two = self[move.after_double_move_pos]
                return move_plus_one.used and (move_plus_one.owner != is_primary_payer) and not move_plus_two.used
            except KeyError:
                return False

        required_moves = [x for x in self.get_possible_moves(allowed_y_direction, is_primary_payer) if is_required(x)]
        print("Filtering to required: ")
        print(required_moves)
        return required_moves

    def apply_move(self, move: Move, allowed_y_direction: Direction = Direction.Positive,
                   is_primary_player: bool = True) -> None:
        # Bounds Check
        start_coords = move.pos
        single_move_coords = move.after_move_pos
        double_move_coords = move.after_double_move_pos
        try:
            start_pos = self[start_coords]
            single_move_pos = self[single_move_coords]
        except KeyError:
            raise InvalidMove()

        # If your piece is not promoted then you have to go one y direction
        if (not start_pos.promoted) and move.y_direction != allowed_y_direction:
            raise InvalidMove()

        # If you don't own the piece, you can't move it
        if is_primary_player != start_pos.owner:
            raise InvalidMove()
        # If the position is not used then it's an invalid move
        if not start_pos.used:
            raise InvalidMove()

        # Check for jump stuff
        if single_move_pos.used:
            # Can't jump your pieces
            if single_move_pos.owner == start_pos.owner:
                raise InvalidMove()
            # Bounds check
            try:
                after_jump_dest = self[double_move_coords]
            except KeyError:
                raise InvalidMove()
            # If there is a piece where you want to move to, you can't
            if after_jump_dest.used:
                raise InvalidMove()

        self.__apply_move_no_check(move)

    def __apply_move_no_check(self, move: Move):
        start_coords = move.pos
        single_move_coords = move.after_move_pos
        double_move_coords = move.after_double_move_pos
        start_pos = self[start_coords]
        single_move_pos = self[single_move_coords]
        self[start_coords] = BoardLocation(False, False, False)
        if single_move_pos.used:
            self[double_move_coords] = start_pos
            # If it is at one of the ends, promote it
            if move.after_double_move_pos[1] in [0, 7]:
                self[double_move_coords] = BoardLocation(True, True, start_pos.owner)
            # Remove the piece you jumped
            self[single_move_coords] = BoardLocation(False, False, False)
        else:
            self[single_move_coords] = start_pos
            # If it is at one of the ends, promote it
            if move.after_move_pos[1] in [0, 7]:
                self[single_move_coords] = BoardLocation(True, True, start_pos.owner)

    def __getitem__(self, idx: Union[int, Tuple[int, int]]) -> Union[BoardLocation, List[BoardLocation]]:
        if isinstance(idx, tuple):
            x, y = idx
            if x < 0 or y < 0:
                raise KeyError()
            try:
                return self.__state[x][y]
            except IndexError:
                raise KeyError()
        elif isinstance(idx, int):
            if idx < 0:
                raise KeyError()
            return self.__state[idx]
        else:
            raise KeyError()

    def __setitem__(self, key: Tuple[int, int], value: BoardLocation):
        self.__state[key[0]][key[1]] = value
