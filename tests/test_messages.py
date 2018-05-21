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
            self.assertEqual(obj.__dict__, constructor.parse_and_decode(packed).__dict__)
            with self.assertRaises(NotEnoughData):
                constructor.parse_and_decode(packed[:-1])
            with self.assertRaises(InvalidType):
                constructor.parse_and_decode(b'\x00' + packed[1:])

    def test_strip(self):
        self.assertEqual(bytes_strip(b"abc\x00"), b"abc")
        self.assertEqual(bytes_strip(b"abc"), b"abc")
