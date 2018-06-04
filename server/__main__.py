"""
Main entrypoint for the server, is to be run from the command line.
If the package was installed correctly with pip or setuptools, then this file will be executed with the "server" command
Otherwise, it can be executed (from the root directory) with `python -m server`
"""
from argparse import ArgumentParser, ArgumentError, Namespace
from logging import getLogger, DEBUG, INFO, basicConfig
from signal import SIGINT
from socket import inet_aton, error as socket_error
from sys import exit as s_exit
# Validate that the python version is at least 3.6
from sys import version_info

from pyuv import Loop, TCP, Signal

from .advertiser import Advertiser
from .db import DictionaryDB
from .queue import UserQueue
from .server import Server
from .user_session import Session

if version_info <= (3, 6,):
    from sys import stderr

    stderr.write("Invalid Python version, needs 3.6 or above")
    s_exit(1)


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
    parser.add_argument("--broadcast-ip", type=validate_ip_arg, required=True,
                        help="The Broadcast address to send Service Discovery messages to")
    parser.add_argument("--listen-ip", type=validate_ip_arg, required=True,
                        help="The IP Address to listen for new connections on")
    parser.add_argument("--verbose", action="store_true", default=False, help="Enable Logging")

    return parser.parse_args()


def start():
    """
    Start the server application by parsing the args
    """
    basicConfig(format='%(levelname)s [%(asctime)s]: %(message)s', level=DEBUG)
    logger = getLogger()
    loop = Loop()
    try:
        # Parse args
        args = get_args()

        # Set the log level if not in verbose mode
        if not args.verbose:
            logger.setLevel(INFO)

        # Allocate a database and register some test users
        db = DictionaryDB(logger)
        db.register_user(b"cam", b"mac", 1200)
        db.register_user(b"jen", b"nej", 1201)
        db.register_user(b"kain", b"niak", 1200)

        # Allocate a Queue
        queue = UserQueue(logger)

        # Create Session Callback
        def create_session(socket: TCP):
            """
            Wrapper for the Session constructor that defaults the queue and db parameters
            :param socket: TCP connection to create the session with
            :return: A new session
            """
            return Session(socket, queue, db, logger)

        # Allocate a Server
        s = Server(args.listen_ip, 8864, create_session, logger)

        # Allocate an advertiser
        a = Advertiser(args.listen_ip, args.broadcast_ip, 8864, 8865, logger)

        # Allocate a Signal Handler
        sig = Signal(loop)

        def on_signal(sig_handler: Signal, signal: int):
            """
            On SIGINT, stop all things depending on the loop and close the loop
            :param sig_handler: Signal handler that caught the signal
            :param signal: The signal that was received
            """
            logger.info("Caught signal {signal}, shutting down".format(signal=signal))
            sig_handler.stop()
            queue.stop()
            a.stop()
            s.close()
            loop.stop()

        # Bind the objects to the event loop
        sig.start(on_signal, SIGINT)
        s.start(loop)
        a.start(loop)
        queue.register_matchmaker(loop)

        # Run the event Loop
        loop.run()
        s_exit(0)
    except ArgumentError:
        logger.error("Argument Error: ", exc_info=True)
        s_exit(1)
