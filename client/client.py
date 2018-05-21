from signal import SIGINT

import pyuv


class Client:
    def __init__(self, ip: str, port: int):
        self.__ip = ip
        self.__port = port
        self.__handle = None
        self.__interrupt_handle = None
        self.__counter = 0

    def on_signal(self, sig_handler, signal):
        self.close()

    def on_data(self, handle, data, error):
        handle.write(self.__counter.to_bytes(4, "big", signed=False))
        self.__counter += 1

    def on_connection_start(self, handler: pyuv.TCP, error):
        handler.start_read(lambda h, d, e: self.on_data(h, d, e))
        handler.write(b"lol")

    def start(self, loop: pyuv.Loop):
        self.__handle = pyuv.TCP(loop)
        self.__handle.connect((self.__ip, self.__port), lambda x, e: self.on_connection_start(x, e))

        self.__interrupt_handle = pyuv.Signal(loop)
        self.__interrupt_handle.start(lambda x, n: self.on_signal(x, n), SIGINT)

    def close(self):
        self.__handle.close()
        self.__interrupt_handle.close()
