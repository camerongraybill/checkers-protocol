from unittest import TestCase

from internal_types.messages import Connect, InvalidLogin, InvalidVersion, GameStart, QueuePosition, YourTurn, MakeMove, \
    CompulsoryMove, InvalidMove, OpponentDisconnect, GameOver, ReQueue, LogOut, NotEnoughData, InvalidType, bytes_strip
from internal_types.types import Move, Board, Direction, BoardLocation


class TestAllMessages(TestCase):
    messages_to_test = [
        (Connect, [1, b"username", b"password"],
         b"\x01\x01username\x00\x00\x00\x00\x00\x00\x00\x00password\x00\x00\x00\x00\x00\x00\x00\x00"),
        (InvalidLogin, [InvalidLogin.Reasons.AccountDoesNotExist], b"\x02\x00"),
        (InvalidVersion, [1, 2], b"\x0D\x01\x02"),
        (QueuePosition, [1, 2, 3], b"\x03\x01\x00\x00\x00\x02\x00\x00\x00\x03\x00\x00\x00"),
        (GameStart, [b"opponent", 16], b'\x04opponent\x00\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00'),
        (YourTurn, [Move(1, 2, Direction.Positive, Direction.Negative), Board([BoardLocation(True, False, True)] * 64)],
         b"\x05*\xb6\xdbm\xb6\xdbm\xb6\xdbm\xb6\xdbm\xb6\xdbm\xb6\xdbm\xb6\xdbm\xb6\xdbm"),
        (MakeMove, [Move(2, 1, Direction.Negative, Direction.Positive)], b"\x06\x45"),
        (CompulsoryMove,
         [Move(1, 2, Direction.Positive, Direction.Negative), Board([BoardLocation(True, False, True)] * 64)],
         b"\x07*\xb6\xdbm\xb6\xdbm\xb6\xdbm\xb6\xdbm\xb6\xdbm\xb6\xdbm\xb6\xdbm\xb6\xdbm"),
        (InvalidMove,
         [Move(1, 2, Direction.Positive, Direction.Negative), Board([BoardLocation(True, False, True)] * 64)],
         b"\x08*\xb6\xdbm\xb6\xdbm\xb6\xdbm\xb6\xdbm\xb6\xdbm\xb6\xdbm\xb6\xdbm\xb6\xdbm"),
        (OpponentDisconnect, [], b"\x09"),
        (GameOver, [255, 2, 1, Move(1, 2, Direction.Positive, Direction.Negative),
                    Board([BoardLocation(True, False, True)] * 64)],
         b"\n\xff\x02\x00\x00\x00\x01\x00\x00\x00*\xb6\xdbm\xb6\xdbm\xb6\xdbm\xb6\xdbm\xb6\xdbm\xb6\xdbm\xb6\xdbm\xb6\xdbm"),
        (ReQueue, [], b"\x0B"),
        (LogOut, [], b"\x0C"),

    ]

    def test_messages(self):
        for constructor, args, packed in TestAllMessages.messages_to_test:
            obj = constructor(*args)
            self.assertEqual(packed, obj.encode(), msg="packed vs encode for {}".format(constructor.__name__))
            self.assertEqual(obj.encode(), constructor.parse_and_decode(packed).encode(),
                             msg="encode vs repack for {}".format(constructor.__name__))
            self.assertEqual(obj.__dict__, constructor.parse_and_decode(packed).__dict__,
                             msg="compare dict for {}".format(constructor.__name__))
            with self.assertRaises(NotEnoughData,
                                   msg="Message {} still works with too little data".format(constructor.__name__)):
                constructor.parse_and_decode(packed[:-1])
            with self.assertRaises(InvalidType,
                                   msg="Message {} still works with wrong type number".format(constructor.__name__)):
                constructor.parse_and_decode(b'\x00' + packed[1:])

    def test_strip(self):
        self.assertEqual(bytes_strip(b"abc\x00"), b"abc")
        self.assertEqual(bytes_strip(b"abc"), b"abc")

    def test_connect_message(self):
        m = Connect(1, b"cameron", b"password")
        self.assertEqual(1, m.version)
        self.assertEqual(b"cameron", m.username)
        self.assertEqual(b"password", m.password)

    def test_invalid_login_message(self):
        m = InvalidLogin(InvalidLogin.Reasons.AccountDoesNotExist)
        self.assertEqual(InvalidLogin.Reasons.AccountDoesNotExist, m.reason)

    def test_invalid_version_message(self):
        m = InvalidVersion(3, 2)
        self.assertEqual(3, m.highest_supported_version)
        self.assertEqual(2, m.lowest_supported_version)

    def test_queue_position_message(self):
        m = QueuePosition(3, 2, 1337)
        self.assertEqual(3, m.queue_size)
        self.assertEqual(2, m.queue_pos)
        self.assertEqual(1337, m.rating)

    def test_game_start_message(self):
        m = GameStart(b"opp", 24)
        self.assertEqual(b"opp", m.opponent_name)
        self.assertEqual(24, m.opponent_rating)

    def test_your_turn_message(self):
        move = Move(1, 2, Direction.Positive, Direction.Positive)
        board = Board([BoardLocation(True, False, True)] * 64)
        m = YourTurn(move, board)
        self.assertEqual(move, m.last_move)
        self.assertEqual(board, m.board)

    def test_make_move_message(self):
        move = Move(1, 2, Direction.Positive, Direction.Positive)
        m = MakeMove(move)
        self.assertEqual(move, m.move)

    def test_compulsory_move_message(self):
        move = Move(1, 2, Direction.Positive, Direction.Positive)
        board = Board([BoardLocation(True, False, True)] * 64)
        m = CompulsoryMove(move, board)
        self.assertEqual(move, m.move)
        self.assertEqual(board, m.board)

    def test_invalid_move_message(self):
        move = Move(1, 2, Direction.Positive, Direction.Positive)
        board = Board([BoardLocation(True, False, True)] * 64)
        m = InvalidMove(move, board)
        self.assertEqual(move, m.move)
        self.assertEqual(board, m.board)

    def test_opponent_disconnect_message(self):
        m = OpponentDisconnect()
        # No fields to test

    def test_game_over_message(self):
        move = Move(1, 2, Direction.Positive, Direction.Positive)
        board = Board([BoardLocation(True, False, True)] * 64)
        m = GameOver(0xFF, 1338, 1337, move, board)
        self.assertEqual(0xFF, m.you_won)
        self.assertEqual(1338, m.new_rating)
        self.assertEqual(1337, m.old_rating)
        self.assertEqual(move, m.winning_move)
        self.assertEqual(board, m.board)

    def test_re_queue_message(self):
        m = ReQueue()
        # no fields to test

    def test_log_out_message(self):
        m = LogOut()
        # no fields to test
