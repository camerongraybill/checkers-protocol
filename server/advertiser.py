"""
This file contains the Advertiser, which sends out broadcasts advertising the TCP server's existence
"""
from logging import Logger

from pyuv import Loop, UDP, Timer


class Advertiser:
    """ The Advertiser is used for SERVICE DISCOVERY to advertise the address of a checkers server """

    def __init__(self, server_ip: str, broadcast_ip: str, broadcast_port: int, listen_port: int, logger: Logger):
        """
        :param server_ip: IP to bind the UDP server to
        :param broadcast_ip: IP to broadcast messages to
        :param broadcast_port: Port to broadcast messages to
        """
        self.__ip = server_ip
        self.__port = broadcast_port
        self.__broadcast_ip = broadcast_ip
        self.__listen_port = listen_port
        self.__advertiser: UDP = None
        self.__advertising_timer: Timer = None
        self.__logger = logger

    def start(self, loop: Loop):
        """
        Add the UDP socket and a Timer to the event loop which
        :param loop: The Event Loop to bind the objects to
        """
        self.__logger.info("Registering Advertiser on {ip}:{port}".format(ip=self.__ip, port=self.__listen_port))
        self.__advertiser = UDP(loop)
        # Bind to the same IP and Port as the TCP server
        self.__advertiser.bind((self.__ip, self.__listen_port))
        # Enable Broadcast
        self.__advertiser.set_broadcast(True)

        # Create a timer to send a broadcast consistently
        self.__advertising_timer = Timer(loop)
        self.__advertising_timer.start(self.advertise, 1, 1)

    def advertise(self, timer_handle: Timer):
        """
        Send a UDP Packet to the port to show that this server is accepting connections to play checkers
        :param timer_handle: The timer handle, unused
        """
        self.__logger.debug("Broadcasting existence to {ip}:{port}".format(ip=self.__broadcast_ip, port=self.__port))
        self.__advertiser.try_send((self.__broadcast_ip, self.__port), b"")

    def stop(self):
        """
        Stop the timer and close the UDP server when stopping the advertiser
        """
        self.__logger.info("Shutting down Advertiser")
        if self.__advertising_timer:
            self.__advertising_timer.stop()
        if self.__advertiser:
            self.__advertiser.close()
