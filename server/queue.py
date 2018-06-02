from logging import getLogger
from typing import List, Tuple


class DuplicateUser(RuntimeError):
    """ Raised when a user is enqueued for a second time """


class NotInQueue(RuntimeError):
    """ Raised when removing a user from the queue who is not in the queue """


class QueueTooSmall(RuntimeError):
    """ Raised when the queue is too small to create a match """


class UserQueue:
    def __init__(self, logger=getLogger(__name__)):
        self.__users: List["Session"] = []
        self.__logger = logger

    def enqueue_user(self, user_to_add: "Session"):
        if user_to_add in self.__users:
            raise DuplicateUser()
        self.__users.append(user_to_add)

    def dequeue_user(self, user_to_remove: "Session"):
        try:
            self.__users.remove(user_to_remove)
        except ValueError:
            raise NotInQueue()

    def pop_closest_pair(self):
        if len(self) < 2:
            raise QueueTooSmall()
        best_user_pair: Tuple["Session", "Session"] = (None, None)
        smallest_diff = 100000000
        for user in self.__users:
            for inner_user in self.__users:
                if user == inner_user:
                    continue
                if abs(user.rating - inner_user.rating) < smallest_diff:
                    best_user_pair = (user, inner_user)
                    smallest_diff = abs(user.rating - inner_user.rating)
        self.dequeue_user(best_user_pair[0])
        self.dequeue_user(best_user_pair[1])
        return best_user_pair

    def __len__(self):
        return len(self.__users)

    def __contains__(self, item):
        return item in self.__users

    def location_of(self, user: "Session"):
        if user in self.__users:
            return self.__users.index(user)
        else:
            raise NotInQueue()

    def __iter__(self):
        return self.__users.__iter__()
