from signal import SIGINT

import pyuv

from server.user_session import UserSession


class Server:
    def __init__(self, ip: str, port: int):
        self.__ip = ip
        self.__port = port
        self.__connections = []
        self.__handle = None
        self.__signal_handler = None

    def on_connection(self, handle: pyuv.TCP, error):
        new_connection = pyuv.TCP(handle.loop)
        handle.accept(new_connection)
        self.__connections.append(UserSession(new_connection))

    def on_signal(self, handler, signal):
        print("Closing down server")
        self.close()

    def start(self, loop: pyuv.Loop):
        self.__handle = pyuv.TCP(loop)
        self.__handle.bind((self.__ip, self.__port))
        self.__handle.listen(lambda x, e: self.on_connection(x, e))

        self.__signal_handler = pyuv.Signal(loop)
        self.__signal_handler.start(lambda x, n: self.on_signal(x, n), SIGINT)

    def close(self):
        [c.close() for c in self.__connections]
        self.__signal_handler.close()
        self.__handle.close()
