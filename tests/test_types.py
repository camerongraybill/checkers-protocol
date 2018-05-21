from unittest import TestCase

from internal_types.types import Move, Direction, BoardLocation, Board, Encodable


class TestMoveType(TestCase):

    def test_move(self):
        m = Move(1, 2, Direction.Negative, Direction.Positive)
        self.assertEqual(m.to_bytes(), b"\x29")
        self.assertEqual(m.to_bytes(), Move.from_bytes(m.to_bytes()).to_bytes())
        self.assertEqual(m.x_pos, 1)
        self.assertEqual(m.y_pos, 2)
        self.assertEqual(m.x_direction, Direction.Negative)
        self.assertEqual(m.y_direction, Direction.Positive)


class TestBoardLocationType(TestCase):

    def test_board_location(self):
        loc = BoardLocation(True, True, False)
        self.assertEqual(loc.to_bytes(), b"\x06")
        self.assertEqual(loc.to_bytes(), BoardLocation.from_bytes(loc.to_bytes()).to_bytes())
        self.assertEqual(loc.used, True)
        self.assertEqual(loc.promoted, True)
        self.assertEqual(loc.owner, False)


class TestBoardType(TestCase):

    def test_board(self):
        b = Board([BoardLocation(True, False, False)] * 64)
        self.assertEqual(b.to_bytes(), b"\x92I$\x92I$\x92I$\x92I$\x92I$\x92I$\x92I$\x92I$")
        self.assertEqual(b.to_bytes(), Board.from_bytes(b.to_bytes()).to_bytes())
        self.assertEqual(b[(0, 0)], b[0][0])
        with self.assertRaises(KeyError):
            b['A']

    def test_invalid_board(self):
        with self.assertRaises(TypeError):
            Board([])


class TestEncodableAbstract(TestCase):

    def test_encodable(self):
        class test(Encodable):
            pass

        with self.assertRaises(TypeError):
            x = test()
