"""
Main entrypoint for the server, is to be run from the command line.
If the package was installed correctly with pip or setuptools, then this file will be executed with the "server" command
Otherwise, it can be executed (from the root directory) with `python -m server`
"""
from argparse import ArgumentParser, ArgumentError, Namespace
from logging import getLogger, DEBUG, INFO, WARNING, basicConfig
from signal import SIGINT
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

    def valid_port(port: str) -> int:
        """
        Validate that a port is valid
        Raises ArgumentError if it is not a valid port
        :param port: port to validate
        :return: the port if it is valid
        """
        try:
            port = int(port)
        except TypeError:
            raise ArgumentError(None, "Invalid Port: {}".format(port))
        else:
            if not 0 <= port <= 25565:
                raise ArgumentError(None, "Invalid Port Number: {}".format(port))
            return port

    parser = ArgumentParser()
    parser.add_argument("--broadcast-ip", default="255.255.255.255",
                        help="The Broadcast address to send Service Discovery messages to (default: %(default)s)")
    parser.add_argument("--listen-ip", default="0.0.0.0",
                        help="The IP Address to listen for new connections on (default: %(default)s)")
    parser.add_argument("--verbose", action="store_true", default=False, help="Enable Debug Logging")
    parser.add_argument("--listen-port", type=valid_port, default="8864",
                        help="Port to listen on for incoming connections (default: %(default)s)")
    parser.add_argument("--quiet", action="store_true", default=False, help="Only log warning and above")
    parser.add_argument("--udp-port", type=valid_port, default="0",
                        help="Port to bind UDP Advertiser to (default: %(default)s)")
    args = parser.parse_args()
    if args.verbose and args.quiet:
        raise ArgumentError(None, "Cannot have verbose AND quiet logging, please only pick --verbose or --quiet")
    return args


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
        if args.quiet:
            logger.setLevel(WARNING)

        # Allocate a database and register some test users
        db = DictionaryDB(logger)
        db.register_user(b"cam", b"mac", 1200)
        db.register_user(b"jen", b"nej", 1201)
        db.register_user(b"kain", b"niak", 1200)
        db.register_user(b"andrei", b"ierdna", 1199)

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
        s = Server(args.listen_ip, args.listen_port, create_session, logger)

        # Allocate an advertiser
        a = Advertiser(args.listen_ip, args.broadcast_ip, args.listen_port, args.udp_port, logger)

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
