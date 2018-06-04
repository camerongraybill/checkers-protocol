"""
This file has the Server class. The Server class accepts incoming connections and creates sessions for them
"""

from logging import Logger
from typing import Callable, Optional, List

from pyuv import TCP, Loop, errno

from server.user_session import Session


class Server:
    """ The Server accepts incoming TCP connections and moves the TCP socket into a Session object. """

    def __init__(self, listen_ip: str, port: int, session_creator: Callable[[TCP], Session], logger: Logger):
        """
        Create a server object and initialize private members
        :param listen_ip: IP Address to listen on for new connections
        :param port: Port to listen on for new connections
        :param session_creator: Callable to use to create new sessions from TCP sockets
        :param logger: Logger to log to
        """
        self.__ip = listen_ip
        self.__port = port
        self.__connections: List[TCP] = []
        self.__handle: TCP = None
        self.__session_creator = session_creator
        self.__logger = logger

    def on_connection(self, handle: TCP, error: Optional[int]):
        """
        Called when a new user connects to the server
        :param handle: The TCP Server
        :param error: Where an error would be if there was an error connecting
        """
        if error is not None:
            self.__logger.warning("Got {error},  {errno} when client attempted to connect to server".format(error=error,
                                                                                                            errno=errno.strerror(
                                                                                                                error)))
        else:

            new_connection = TCP(handle.loop)
            # Accept a connection
            handle.accept(new_connection)
            # Add it to internal connections and create a session
            session = self.__session_creator(new_connection)
            session.start()
            self.__connections.append(new_connection)

    def start(self, loop: Loop):
        """
        Start the Server on the loop
        :param loop: Loop to bind the server to
        """
        self.__logger.info("Listening on {ip}:{port} for new connections".format(ip=self.__ip, port=self.__port))
        self.__handle = TCP(loop)
        # Listen on the provided ip and port
        self.__handle.bind((self.__ip, self.__port))
        # Register connection handler
        self.__handle.listen(self.on_connection)

    def close(self):
        """
        Must close all clients when disconnecting
        """
        self.__logger.info("Stopped accepting new connections, closing all connections that are open")
        [c.close() for c in self.__connections if c.active]
        if self.__handle is not None and self.__handle.active:
            self.__handle.close()
