from logging import getLogger
from unittest import TestCase

from server.db import DictionaryDB, Database


class TestDictionaryDB(TestCase):
    def test_normal_op(self):
        db = DictionaryDB(getLogger())
        db.register_user(b"test", b"tset", 1234)
        self.assertEqual(1234, db.get_rating(b"test"))
        db.auth_user(b"test", b"tset")

    def test_abnormal_op(self):
        db = DictionaryDB(getLogger(__name__))
        db.register_user(b"a", b"a", 1)
        with self.assertRaises(Database.DuplicateUser):
            db.register_user(b"a", b"a", 1)
        with self.assertRaises(Database.UserDoesNotExist):
            db.auth_user(b"x", b"x")
        with self.assertRaises(Database.UserDoesNotExist):
            db.get_rating(b"x")
        with self.assertRaises(Database.InvalidPassword):
            db.auth_user(b"a", b"b")
