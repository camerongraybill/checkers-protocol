""" This file contains the UserQueue class which is where users are placed while waiting for a game. """

from logging import Logger
from typing import List, Tuple

from pyuv import Loop, Timer

from .game import Game, InvalidGameException


class DuplicateUser(RuntimeError):
    """ Raised when a user is enqueued for a second time """


class NotInQueue(RuntimeError):
    """ Raised when removing a user from the queue who is not in the queue """


class QueueTooSmall(RuntimeError):
    """ Raised when the queue is too small to create a match """


class UserQueue:
    """ Add users to a queue to make games for them, create games on a timer with pairs of users. """

    def __init__(self, logger: Logger):
        """
        Initialize the queue with a List of sessions and the matchmaking handler
        :param logger: Logger to log to
        """
        self.__users: List["Session"] = []
        self.__logger = logger
        self.__matchmaking_handler: Timer = None
        self.__games: List[Game] = []

    def enqueue_user(self, user_to_add: "Session"):
        """
        Add a user to the queue
        Raise DuplicateUser if the user is already in the queue
        :param user_to_add: The User to add to the queue
        """
        if user_to_add in self.__users:
            raise DuplicateUser()
        self.__users.append(user_to_add)

    def dequeue_user(self, user_to_remove: "Session"):
        """
        Remove a user from the Queue
        Raise ValueError if the user is not in the queue
        :param user_to_remove: The user to remove from the queue
        """
        try:
            self.__users.remove(user_to_remove)
        except ValueError:
            raise NotInQueue()

    def pop_closest_pair(self):
        """
        Find the two closest users and remove them from the queue
        :return:
        """
        if len(self) < 2:
            raise QueueTooSmall()
        best_user_pair: Tuple["Session", "Session"] = (None, None)
        smallest_diff = 100000000
        for user in self.__users:
            for inner_user in self.__users:
                if user.username == inner_user.username:
                    continue
                if abs(user.rating - inner_user.rating) < smallest_diff:
                    best_user_pair = (user, inner_user)
                    smallest_diff = abs(user.rating - inner_user.rating)
        self.dequeue_user(best_user_pair[0])
        self.dequeue_user(best_user_pair[1])
        self.__logger.info("Popped {one} and {two} from the queue".format(one=best_user_pair[0].username,
                                                                          two=best_user_pair[1].username))
        return best_user_pair

    def __len__(self):
        return len(self.__users)

    def __contains__(self, item):
        return item in self.__users

    def location_of(self, user: "Session") -> int:
        """
        Return the index of a user in the queue
        Raises NotInQueue if the user is not in the queue
        :param user: The user to find
        :return: The location of the user in the queue
        """
        if user in self.__users:
            return self.__users.index(user)
        else:
            raise NotInQueue()

    def register_matchmaker(self, loop: Loop):
        """
        Register the event loop and the matchmaking timer
        :param loop: The loop to bind to
        """
        self.__logger.info("Registering matchmaker")
        self.__matchmaking_handler = Timer(loop)
        self.__matchmaking_handler.start(self.__make_match, 0, 5)

    def __make_match(self, timer_handle: Timer):
        """
        Create a game from the two closest users
        :param timer_handle: The timer handle, not used
        """
        try:
            user_one, user_two = self.pop_closest_pair()
            # Make a game
            try:
                self.__games.append(Game(user_one, user_two, self.__logger))
            except InvalidGameException:
                self.__logger.warning(
                    "Failed to start game between {pone} and {ptwo}, putting both back in queue".format(
                        pone=user_one.username, ptwo=user_two.username))
                self.enqueue_user(user_one)
                self.enqueue_user(user_two)
            self.__logger.info("Starting game between {} and {}".format(user_one.username, user_two.username))
        except QueueTooSmall:
            pass
        for user in self:
            user.on_queue_position(len(self), self.location_of(user) + 1)

    def stop(self):
        """
        Stop the matchmaking handler
        """
        self.__logger.info("Stopping matchmaker")
        if self.__matchmaking_handler:
            self.__matchmaking_handler.stop()
        self.__logger.info("Stopping all running games")
        [x.end_and_disconnect() for x in self.__games]
        self.__logger.info("Disconnecting all users in queue")
        [user.disconnect(force=True) for user in self.__users]

    def __iter__(self):
        return self.__users.__iter__()
