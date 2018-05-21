from unittest import TestCase
from internal_types.types import Move, Direction, BoardLocation, Board


class TestMoveType(TestCase):

    def test_move(self):
        m = Move(1, 2, Direction.Negative, Direction.Positive)
        self.assertEqual(m.to_bytes(), b"\x29")
        self.assertEqual(m.to_bytes(), Move.from_bytes(m.to_bytes()).to_bytes())


class TestBoardLocationType(TestCase):

    def test_board_location(self):
        loc = BoardLocation(True, True, False)
        self.assertEqual(loc.to_bytes(), b"\x06")
        self.assertEqual(loc.to_bytes(), BoardLocation.from_bytes(loc.to_bytes()).to_bytes())


class TestBoardType(TestCase):

    def test_board(self):
        b = Board([BoardLocation(True, False, False)] * 64)
        self.assertEqual(b.to_bytes(), b"\x92I$\x92I$\x92I$\x92I$\x92I$\x92I$\x92I$\x92I$")
        self.assertEqual(b.to_bytes(), Board.from_bytes(b.to_bytes()).to_bytes())
