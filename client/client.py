"""
This file contains the Client class. The Client handles the TCP connection to the server,
and protocol logic from the User's point of view
"""

from logging import Logger
from signal import SIGINT
from typing import Optional

from pyuv import Loop, TCP, errno, Signal

from internal_types.messages import Connect, Message, message_to_type, InvalidLogin, InvalidVersion, QueuePosition, \
    GameStart, LogOut, CompulsoryMove, InvalidMove, GameOver, OpponentDisconnect, YourTurn, MakeMove, ReQueue, \
    NotEnoughData
from internal_types.states import ProtocolState
from internal_types.types import Move, Direction
from .Interface import Interface


class Client:
    """
    STATEFUL
    Represents a User playing checkers
    The .__protocol_state property shows what state of the protocol this client is currently in
    """

    def __init__(self, ip: str, port: int, username: bytes, password: bytes, interface: Interface,
                 logger: Logger) -> None:
        """
        Constructor for the Client class
        :param ip: The IP Address for the server to connect to
        :param port: The Port to connect to on the remove server
        :param username: Username to connect with
        :param password: Password to connect with
        :param interface: The User Interface object to allow a user to interface with the game
        :param logger: Logger to write messages to
        """
        # Private Properties
        self.__ip = ip
        self.__port = port
        self.__tcp_handle: TCP = None
        self.__interrupt_handle: Signal = None
        self.__username = username
        self.__password = password
        self.__protocol_state = ProtocolState.UNAUTHENTICATED
        self.__ui = interface
        self.__logger = logger

    # Public Methods

    def start(self, loop: Loop) -> None:
        """
        Attach the client to the event loop
        :param loop: Event Loop object to attach to
        """
        # Register the TCP client to connect to the server
        self.__tcp_handle = TCP(loop)
        self.__tcp_handle.connect((self.__ip, self.__port), self.__on_connection_start)

        # Register the interrupt handler to catch sigint
        self.__interrupt_handle = Signal(loop)
        self.__interrupt_handle.start(self.__on_signal, SIGINT)

    def shutdown(self) -> None:
        """
        Shut the client down by telling the server it is logging out (if it is logged in)
        and then closing the connection
        """
        self.__logger.info("Shutting Down...")
        if self.__protocol_state != ProtocolState.UNAUTHENTICATED:
            self.__send(LogOut())
        self.__close()

    # Private Methods

    def __send(self, msg: Message) -> None:
        """
        Encode and Send a message to the server
        :param msg: Message to send
        """
        self.__logger.debug("Sending {msg}, encoded as {raw}".format(msg=msg, raw=msg.encode()))
        self.__tcp_handle.write(msg.encode())

    def __close(self):
        """
        Close the connection to the server and shut down the signal handler
        """
        self.__tcp_handle.stop_read()
        self.__tcp_handle.shutdown()
        self.__interrupt_handle.close()

    # Event Handles

    def __on_connection_start(self, handler: TCP, error: Optional[int]):
        """
        Called when the TCP connection is started
        :param handler: TCP Socket that is connected to the server
        :param error: An Error would be here if it failed to connect to the server
        """
        if error is not None:
            if error == -4095:
                self.__logger.warning("Got End of File from server")
                self.shutdown()
            else:
                self.__logger.error(
                    "Unknown TCP Error: {stringed}, errno: {no}".format(stringed=errno.strerror(error), no=error))
                self.shutdown()
        else:
            self.__logger.info("Connected to server at {ip}".format(ip=self.__ip))
            # Start Asynchronous Read on the TCP Socket
            handler.start_read(self.__on_data)
            # Send the Log In Message
            self.__send(Connect(1, self.__username, self.__password))
            self.__protocol_state = ProtocolState.IN_QUEUE

    def __on_data(self, client: TCP, data: bytes, error: Optional[int]):
        """
        Called when the TCP socket receives data
        :param client: The TCP Socket that received Data
        :param data: Read Data
        :param error: An Error would be here if it failed to read data
        """
        if error is not None:
            if error == -4095:
                self.__logger.warning("Got End of File from server")
                self.shutdown()
            else:
                self.__logger.error(
                    "Unknown TCP Error: {stringed}, errno: {no}".format(stringed=errno.strerror(error), no=error))
                self.shutdown()
        else:
            # Parse the Message
            try:
                msg = message_to_type(data).parse_and_decode(data)
            except NotEnoughData:
                self.__logger.critical("Got invalid message ({raw}) from the server, shutting down".format(raw=data))
                self.shutdown()
            else:
                self.__logger.debug(
                    "Got {message} in state {state}".format(message=msg, state=self.__protocol_state.name))
                # Dispatch to another function based on current DFA state
                {
                    ProtocolState.UNAUTHENTICATED: self.__msg_on_unauthenticated,
                    ProtocolState.IN_QUEUE: self.__msg_on_in_queue,
                    ProtocolState.PROCESSING_GAME_STATE: self.__msg_on_processing_game_state,
                    ProtocolState.USER_MOVE: self.__msg_on_user_move,
                    ProtocolState.GAME_END: self.__msg_on_game_end
                }[self.__protocol_state](msg)
                # If there is more data, keep parsing
                if len(data) > msg.calc_size() + 1:
                    self.__on_data(client, data[msg.calc_size():], None)

    def __on_signal(self, sig_handler: Signal, signal: int) -> None:
        """
        Callback to be called when a signal is caught
        :param sig_handler: The Signal Handler that caught the signal
        :param signal: The signal that was caught
        """
        self.__logger.info("Received Signal {}".format(signal))
        self.shutdown()

    # State based event handlers
    # These functions implement the Client side of the DFA
    # All of the following functions are STATEFUL

    def __msg_on_unauthenticated(self, msg: Message) -> None:
        """
        Logic to do while in the Unauthenticated state
        :param msg: Message received
        """
        self.__logger.fatal(
            "Received invalid message of type {type} for state {state}".format(type=msg.__class__.__name__,
                                                                               state=self.__protocol_state.name))
        self.shutdown()

    def __msg_on_in_queue(self, msg: Message) -> None:
        """
        Logic to do while in the In Queue state
        :param msg: Message received
        """
        if isinstance(msg, InvalidLogin):
            # This is the edge of the DFA from In Queue -> Unauthenticated (Invalid Login)
            self.__protocol_state = ProtocolState.UNAUTHENTICATED
            bad_login_reasons = {
                InvalidLogin.Reasons.InvalidPassword: "Invalid Password",
                InvalidLogin.Reasons.AlreadyLoggedIn: "User is already logged in",
                InvalidLogin.Reasons.AccountDoesNotExist: "User does not exist"
            }
            self.__ui.display_message("Invalid Login, {reason}".format(reason=bad_login_reasons[msg.reason]))
            # Request a new set of credentials from the user
            self.__username, self.__password = self.__ui.request_credentials()
            self.__send(Connect(1, self.__username, self.__password))
            self.__protocol_state = ProtocolState.IN_QUEUE
        elif isinstance(msg, InvalidVersion):
            # This is the edge of the DFA from In Queue -> Unauthenticated (Invalid Login)
            self.__ui.display_message(
                "The Server does not support your version of the client, it supports versions {lowest}-{highest}".format(
                    lowest=msg.lowest_supported_version, highest=msg.highest_supported_version))
            self.shutdown()
        elif isinstance(msg, QueuePosition):
            # This is the edge of the DFA from In Queue -> In Queue (Queue Pos)
            self.__ui.show_queue_position(msg.queue_pos, msg.rating, msg.queue_size)
        elif isinstance(msg, GameStart):
            # This is the edge of the DFA from In Queue -> Processing Game State (Game Start)
            self.__ui.game_start(msg.opponent_name.decode("utf-8"), msg.opponent_rating)
            self.__protocol_state = ProtocolState.PROCESSING_GAME_STATE
        else:
            self.__logger.fatal(
                "Received invalid message of type {type} for state {state}".format(type=msg.__class__.__name__,
                                                                                   state=self.__protocol_state.name))
            self.shutdown()

    def __msg_on_processing_game_state(self, msg: Message):
        """
        Logic to do while in the Processing Game State state
        :param msg: Message received
        """
        if isinstance(msg, YourTurn):
            # This is the edge of the DFA from Processing Game State -> User Move (Your Turn)
            self.__protocol_state = ProtocolState.USER_MOVE
            # Check if this is the beginning of the game
            if msg.last_move == Move(0, 0, Direction.Negative, Direction.Negative):
                self.__ui.display_message("You go first!")
            else:
                self.__ui.display_message("Last Move was : {move}".format(move=msg.last_move.__repr__()))
            self.__ui.display(msg.board)
            self.__send(MakeMove(self.__ui.get_move()))
            self.__protocol_state = ProtocolState.PROCESSING_GAME_STATE
        elif isinstance(msg, CompulsoryMove):
            # This is the edge of the DFA from Processing Game State -> Processing Game State (Compulsory Move)
            self.__ui.display_message("Compulsory Move: {move}".format(move=msg.move.__repr__()))
            self.__ui.display(msg.board)
        elif isinstance(msg, InvalidMove):
            # This is the edge of the DFA from Processing Game State -> User Move (Invalid Move)
            self.__protocol_state = ProtocolState.USER_MOVE
            self.__ui.display_message("{move} Is an invalid move".format(move=msg.move.__repr__()))
            self.__ui.display(msg.board)
            self.__send(MakeMove(self.__ui.get_move()))
            self.__protocol_state = ProtocolState.PROCESSING_GAME_STATE
        elif isinstance(msg, GameOver):
            # This is the edge of the DFA from Processing Game State -> Game End (Game Over)
            self.__protocol_state = ProtocolState.GAME_END
            self.__ui.game_over(msg.board, msg.old_rating, msg.new_rating, msg.you_won != 0)
            if self.__ui.prompt_play_again():
                self.__protocol_state = ProtocolState.IN_QUEUE
                self.__send(ReQueue())
            else:
                self.shutdown()

        elif isinstance(msg, OpponentDisconnect):
            # This is the edge of the DFA from Processing Game State -> Game End (Opponent Disconnect)
            self.__protocol_state = ProtocolState.GAME_END
            self.__ui.opponent_left()
            if self.__ui.prompt_play_again():
                self.__protocol_state = ProtocolState.IN_QUEUE
                self.__send(ReQueue())
            else:
                self.shutdown()
        else:
            self.__logger.fatal(
                "Received invalid message of type {type} for state {state}".format(type=msg.__class__.__name__,
                                                                                   state=self.__protocol_state.name))
            self.shutdown()

    def __msg_on_user_move(self, msg: Message):
        """
        Logic to do while in the User Move state
        :param msg: Message received
        """
        if isinstance(msg, OpponentDisconnect):
            # This is the edge of the DFA from User Move -> Game End (Opponent Disconnect)
            self.__protocol_state = ProtocolState.GAME_END
            self.__ui.opponent_left()
            if self.__ui.prompt_play_again():
                self.__protocol_state = ProtocolState.IN_QUEUE
                self.__send(ReQueue())
            else:
                self.shutdown()
        else:
            self.__logger.fatal(
                "Received invalid message of type {type} for state {state}".format(type=msg.__class__.__name__,
                                                                                   state=self.__protocol_state.name))
            self.shutdown()

    def __msg_on_game_end(self, msg: Message):
        """
        Logic to do while in the Game End state
        :param msg: Message Received
        """
        self.__logger.fatal(
            "Received invalid message of type {type} for state {state}".format(type=msg.__class__.__name__,
                                                                               state=self.__protocol_state.name))
        self.shutdown()
