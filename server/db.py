"""
CS 544
June 6, 2018
This file contains the Database and DictionaryDB classes, which are used to store user information
"""
from abc import ABC, abstractmethod
from collections import namedtuple
from logging import Logger


class Database(ABC):
    """ Abstract Database Class"""

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
        """
        Attempt to authorize a user
        Raises Database.InvalidPassword if the user has an invalid password
        Raises Database.UserDoesNotExist if the user does not exist
        :param username: Username to check in the database
        :param password: Password to check in the database
        """
        raise NotImplementedError()

    @abstractmethod
    def get_rating(self, username: bytes) -> int:
        """
        Get the rating of a user
        Raises Database.UserDoesNotExist if the User does not exist
        :param username: Username to check
        """
        raise NotImplementedError()

    @abstractmethod
    def register_user(self, username: bytes, password: bytes, rating: int = 1200):
        """
        Register a user
        Raises Database.DuplicateUser if the user is already registered
        :param username: Username to Register
        :param password: Password to register
        :param rating: Rating to start at for the new user
        """
        raise NotImplementedError()

    @abstractmethod
    def set_rating(self, username: bytes, rating: int):
        """
        Set the rating for a user
        Raises Database.UserDoesNotExist if the User does not exist
        :param username: User to set the rating for
        :param rating: Rating to set to
        """
        raise NotImplementedError()


class DictionaryDB(Database):
    """ A concrete implementation of the Database interface but stores everything in memory """
    __entry = namedtuple("entry", ["password", "rating"])

    def __init__(self, logger: Logger):
        """
        Create a dictionary to store user data in, initialize it with nothing
        """
        self.__logger = logger
        self.__data = {}

    def auth_user(self, username: bytes, password: bytes):
        """ See Database """
        try:
            if password != self.__data[username].password:
                raise Database.InvalidPassword()
            self.__logger.info("{user} Logged in".format(user=username))
        except KeyError:
            raise Database.UserDoesNotExist()

    def get_rating(self, username: bytes) -> int:
        """ See Database """
        try:
            return self.__data[username].rating
        except KeyError:
            raise Database.UserDoesNotExist()

    def register_user(self, username: bytes, password: bytes, rating: int = 1200):
        """ See Database """
        if username in self.__data:
            raise Database.DuplicateUser()
        self.__logger.info(
            "Registered user {name}, initializing to {rating} rating".format(name=username, rating=rating))
        self.__data[username] = self.__entry(password, rating)

    def set_rating(self, username: bytes, rating: int):
        """ See Database """
        try:
            old_rating = self.__data[username].rating
            self.__data[username] = self.__entry(self.__data[username].password, rating)
            self.__logger.info(
                "Rating for {user} changed from {before} to {after}".format(user=username, before=old_rating,
                                                                            after=rating))
        except KeyError:
            raise Database.UserDoesNotExist()
