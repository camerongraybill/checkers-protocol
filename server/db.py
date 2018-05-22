from abc import ABC, abstractmethod
from collections import namedtuple


class Database(ABC):
    class DatabaseException(RuntimeError):
        """ Problems raised by the database """

    class UserDoesNotExist(DatabaseException):
        """ Raised when trying to log in with a user who does not exist """

    class InvalidPassword(DatabaseException):
        """ Raised when the user used an invalid password """

    class DuplicateUser(DatabaseException):
        """ Raised when trying to register a user who is already registered """

    @abstractmethod
    def auth_user(self, username: bytes, password: bytes):
        raise NotImplementedError()

    @abstractmethod
    def get_rating(self, username: bytes):
        raise NotImplementedError()

    @abstractmethod
    def register_user(self, username: bytes, password: bytes, rating: int):
        raise NotImplementedError()


class DictionaryDB(Database):
    __entry = namedtuple("entry", ["password", "rating"])

    def __init__(self):
        self.__data = {
            b"cam": self.__entry(b"mac", 3000),
            b"andrei": self.__entry(b"ierdna", 2000),
            b"safa": self.__entry(b"afas", 1000)
        }

    def auth_user(self, username: bytes, password: bytes):
        try:
            if password != self.__data[username].password:
                raise Database.InvalidPassword()
        except KeyError:
            raise Database.UserDoesNotExist()

    def get_rating(self, username: bytes):
        try:
            return self.__data[username].rating
        except KeyError:
            raise Database.UserDoesNotExist()

    def register_user(self, username: bytes, password: bytes, rating: int):
        if username in self.__data:
            raise Database.DuplicateUser()
        self.__data[username] = self.__entry(password, rating)
