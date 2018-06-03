from signal import SIGINT

import pyuv

from server.user_session import Session
from .db import DictionaryDB
from .game import Game
from .queue import UserQueue, QueueTooSmall


class Server:
    def __init__(self, listen_ip: str, broadcast_ip: str, port: int):
        self.__ip = listen_ip
        self.__broadcast_ip = broadcast_ip
        self.__port = port
        self.__connections = []
        self.__handle = None
        self.__signal_handler = None
        self.__matchmaking_handler = None
        self.__advertiser = None
        self.__advertising_timer = None
        self.__queue = UserQueue()
        self.__db = DictionaryDB()

    def on_connection(self, handle: pyuv.TCP, error):
        new_connection = pyuv.TCP(handle.loop)
        handle.accept(new_connection)
        self.__connections.append(Session(new_connection, self.__queue, self.__db))

    def on_signal(self, handler, signal):
        self.close()
        handler.loop.stop()

    def __matchmake(self, timer):
        try:
            user_one, user_two = self.__queue.pop_closest_pair()
            # Make a game
            g = Game(user_one, user_two)
            user_one.join_game(g)
            user_two.join_game(g)
            print("Starting game between {} and {}!".format(user_one.username, user_two.username))
        except QueueTooSmall:
            pass
        for user in self.__queue:
            user.on_queue_position(len(self.__queue), self.__queue.location_of(user) + 1)

    def start(self, loop: pyuv.Loop):
        self.__handle = pyuv.TCP(loop)
        self.__handle.bind((self.__ip, self.__port))
        self.__handle.listen(self.on_connection)

        self.__signal_handler = pyuv.Signal(loop)
        self.__signal_handler.start(self.on_signal, SIGINT)

        self.__matchmaking_handler = pyuv.Timer(loop)
        self.__matchmaking_handler.start(self.__matchmake, 0, 5)

        self.__advertiser = pyuv.UDP(loop)
        self.__advertiser.set_broadcast(True)

        self.__advertising_timer = pyuv.Timer(loop)

        def advertise(*args, **kwargs):
            self.__advertiser.try_send((self.__broadcast_ip, self.__port), "\x64{}".format(self.__ip))

        self.__advertising_timer.start(advertise, 1, 1)

    def close(self):
        [c.disconnect(True) for c in self.__connections]
        self.__signal_handler.close()
        self.__handle.close()

