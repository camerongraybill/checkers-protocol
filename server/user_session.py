import pyuv


class UserSession:
    def __init__(self, handle: pyuv.TCP):
        self.__handle = handle
        handle.start_read(lambda a, b, c: self.on_data(a, b, c))

    def on_data(self, client: pyuv.TCP, data, error):
        print(data)
        client.write(data)

    def close(self):
        self.__handle.close()
