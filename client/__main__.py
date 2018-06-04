"""
Main entrypoint for the application, is to be run from the command line.
If the package was installed correctly with pip or setuptools, then this file will be executed with the "client" command
Otherwise, it can be executed (from the root directory) with `python -m client`
"""

from argparse import ArgumentParser, ArgumentError, Namespace
from logging import getLogger, DEBUG, CRITICAL, basicConfig
from socket import socket, AF_INET, SOCK_DGRAM, timeout, inet_aton, error as socket_error
from sys import exit as s_exit
# Validate that the python version is at least 3.6
from sys import version_info

from pyuv import Loop

from .Interface import Interface
from .client import Client

if version_info <= (3, 6,):
    from sys import stderr

    stderr.write("Invalid Python version, needs 3.6 or above")
    s_exit(1)


def listen_for_address() -> str:
    """
    SERVICE DISCOVERY (Client side)
    Listen for any UDP Packets being sent on the specified checkers port
    If a packet is found, return the IP Address of the sender
    :return: The IP Address of a checkers server
    """
    s = socket(AF_INET, SOCK_DGRAM)
    s.settimeout(3)
    s.bind(('0.0.0.0', 8864))
    data = s.recvfrom(1024)
    s.close()
    return data[1][0]


def get_args() -> Namespace:
    """
    Parse the command line args, returning an arguments object
    :return: Parsed command line args
    """

    def validate_ip_arg(ip: str) -> str:
        """
        Validate that an IP address is valid
        Raise ArgumentError if the address is invalid
        :param ip: ip address to validate, as xxx.xxx.xxx.xxx
        :return: The same IP address
        """
        try:
            inet_aton(ip)
            return ip
        except socket_error:
            raise ArgumentError(None, "Invalid IP Address: {}".format(ip))

    parser = ArgumentParser()
    try:
        parser.add_argument("--server-ip", type=validate_ip_arg, default=listen_for_address(),
                            help="The ipv4 address for the server (%(default)s found by service discovery)")
    except timeout:
        parser.add_argument("--server-ip", type=validate_ip_arg, required=True,
                            help="The ipv4 address for the server (Failed to find with service discovery)")
    parser.add_argument("--username", type=str.encode, help="The Username to connect with")
    parser.add_argument("--password", type=str.encode, help="The Password to connect with")
    parser.add_argument("--port", type=int, help="The Port the server is running on", default=8864)
    parser.add_argument("--verbose", action="store_true", default=False, help="Enable Logging")

    return parser.parse_args()


def start():
    """
    Start the client application by allocating a logger, parsing args and then forwarding the args on to the client
    """
    basicConfig(format='%(levelname)s(%(asctime)s):%(message)s', level=DEBUG)
    logger = getLogger()
    try:
        try:
            args = get_args()

            if not args.verbose:
                logger.setLevel(CRITICAL)

            ui = Interface()
            if not args.username:
                args.username = ui.request_username()

            if not args.password:
                args.password = ui.request_pass()

            # Create a client
            s = Client(args.server_ip, 8864, args.username, args.password, ui, logger)

            # Create an event loop
            loop = Loop()
            # Bind Client to event Loop
            s.start(loop)
        except KeyboardInterrupt:
            s_exit(1)
        else:
            # Run the event loop
            loop.run()
            s_exit(0)
    except ArgumentError as e:
        print("Argument Error: {}".format(e))
        s_exit(1)


if __name__ == "__main__":
    start()
