""" This file contains the Session class which implements the server side of the Protocol """

from logging import Logger
from typing import Optional

from pyuv import TCP, errno

from internal_types.messages import message_to_type, Message, Connect, InvalidLogin, InvalidVersion, QueuePosition, \
    LogOut, MakeMove, ReQueue, CompulsoryMove, YourTurn, InvalidMove, GameOver, OpponentDisconnect, GameStart, \
    NotEnoughData
from internal_types.states import ProtocolState
from internal_types.types import Board, Move
from .db import Database
from .game import InvalidMoveException
from .queue import DuplicateUser, NotInQueue, UserQueue


class Session:
    """ STATEFUL
    the __current_state for this is the protocol state for this user's connection to the server
    The Session class represent's a user that is connected to the server
    """
    supported_versions = [1]

    def __init__(self, handle: TCP, queue: UserQueue, database_connection: Database, logger: Logger):
        """
        Create a session for the given TCP handle which is unique to this session,
        and keep references to the queue and database
        Also initialize some variables like the current state
        :param handle: The TCP Socket this session works on
        :param queue: The Queue used on this server
        :param database_connection: The database on this server
        :param logger: The logger to log to
        """
        self.__handle = handle
        self.__current_state = ProtocolState.UNAUTHENTICATED
        self.__server_queue = queue
        self.__server_db = database_connection
        self.__game: "Game" = None
        self.__rating: int = None
        self.__username: bytes = None
        self.__logger = logger

    # Public Methods

    def start(self):
        """
        Start reading from the socket
        """
        self.__logger.info("Started New Session")
        self.__handle.start_read(self.__on_data)

    def disconnect(self, force=False):
        """
        Disconnect the user from the server
        :param force: If true, do not cleanly shut down and clear the state of the socket
        """
        username = self.username or "(that was not logged in)"
        if not force:
            # Remove the user from the queue
            if self in self.__server_queue:
                self.__server_queue.dequeue_user(self)
            # Cleanly close the user's game
            if self.__game is not None:
                game = self.__game
                self.__game = None
                game.user_disconnect(self)
            # Reset all session variables to defaults
            self.__rating = None
            self.__username = None
            self.__current_state = ProtocolState.UNAUTHENTICATED
        try:
            if self.__handle is not None and self.__handle.active:
                self.__handle.stop_read()
                self.__handle.shutdown()
        except Exception:
            # No matter what exception happens here, we don't care. Just close the connection.
            self.__logger.warning("Problem while disconnecting user {username}".format(username=username))

        self.__logger.info("User {username} was disconnected".format(username=username))

    # Public event handlers

    def on_compulsory_move(self, move: Move, board: Board):
        """
        Event handle to be called by the Game when it makes a compulsory move
        STATEFUL this being called is the edge of the DFA from Processing Game State to Processing Game State (Compulsory Move)
        :param move: Move that was made
        :param board: New Board state
        """
        if self.__current_state != ProtocolState.PROCESSING_GAME_STATE:
            self.__logger.error(
                "{user} is Attempting to send compulsory move from state {state}".format(user=self.username,
                                                                                         state=self.__current_state.name))
            self.disconnect()
        else:
            self.__send(CompulsoryMove(move, board))
            self.__current_state = ProtocolState.PROCESSING_GAME_STATE

    def on_request_move(self, last_move: Move, board: Board):
        """
        Request a move from a user
        STATEFUL this being called is the edge of the DFA from Processing Game State to User Move (Your Turn)
        :param last_move: The last move that was made
        :param board: The current game board
        """
        if self.__current_state != ProtocolState.PROCESSING_GAME_STATE:
            self.__logger.error("{user} is attempting to request move from state {state}".format(user=self.username,
                                                                                                 state=self.__current_state.name))
            self.disconnect()
        else:
            self.__send(YourTurn(last_move, board))
            self.__current_state = ProtocolState.USER_MOVE

    def on_game_end(self, last_move: Move, board: Board, rating_change: int, winner: bool):
        """
        End the game
        STATEFUL this being called is the edge of the DFA from Processing Game State to Game End (Game Over)
        :param last_move: The winning move
        :param board: The board at the end of the game
        :param rating_change: The user's change in rating
        :param winner: True if this user was the winner
        """
        if self.__current_state != ProtocolState.PROCESSING_GAME_STATE:
            self.__logger.error("{user} is attempting to end game from state {state}".format(user=self.username,
                                                                                             state=self.__current_state.name))
            self.disconnect()
        else:
            self.__send(GameOver(winner, self.__rating + rating_change, self.__rating, last_move, board))
            self.__server_db.set_rating(self.__username, self.__rating + rating_change)
            self.__rating = self.__rating + rating_change
            self.__current_state = ProtocolState.GAME_END

    def on_opponent_disconnect(self):
        """
        Called when an opponent disconnects from a game
        STATEFUL this being called is the edge of the DFA from Processing Game State or User Move to Game End (Opponent Disconnect)
        """
        if self.__current_state not in [ProtocolState.PROCESSING_GAME_STATE, ProtocolState.USER_MOVE]:
            self.__logger.error("{user} had opponent disconnect while in state {state}".format(user=self.username,
                                                                                               state=self.__current_state.name))
            self.disconnect()
        else:
            self.__send(OpponentDisconnect())
            self.__game = None
            self.__current_state = ProtocolState.GAME_END

    def on_queue_position(self, queue_size: int, queue_position: int):
        """
        Called when the queue updates and the user is given their position again
        STATEFUL this being called is the edge of the DFA from In Queue to In Queue (Queue Position)
        :param queue_size: The length of the queue
        :param queue_position: The user's position in the queue
        """
        if self.__current_state != ProtocolState.IN_QUEUE:
            self.__logger.error("{user} got Queue Update while in state {state}".format(user=self.username,
                                                                                        state=self.__current_state.name))
            self.disconnect()
        else:
            self.__send(QueuePosition(queue_size, queue_position, self.rating))

    def on_game_start(self, opponent_name: str, opponent_rating: int, game: "Game"):
        """
        Called when a match is made and the user is added to a game
        STATEFUL this being called is the edge of the DFA from In Queue to Processing Game State (Game Start)
        :param opponent_name: The name of the user's opponent
        :param opponent_rating: The rating of the opponent
        :param game: The game to join
        """
        self.__game = game
        if self.__current_state != ProtocolState.IN_QUEUE:
            self.__logger.error("{user} got placed in game while in state {state}".format(user=self.username,
                                                                                          state=self.__current_state.name))
            self.disconnect()
        else:
            self.__send(GameStart(opponent_name.encode(), opponent_rating))
            self.__current_state = ProtocolState.PROCESSING_GAME_STATE

    # Public Properties
    @property
    def username(self) -> str:
        return self.__username.decode()

    @property
    def rating(self):
        return self.__rating

    # Private Methods

    def __send(self, msg: Message) -> None:
        """
        Encode and Send a message to the client
        :param msg: Message to send
        """
        self.__logger.debug("Sending {msg}, encoded as {raw}, from session {user}".format(msg=msg, raw=msg.encode(),
                                                                                          user=self.username))
        self.__handle.write(msg.encode())

    # Private Event Handles

    def __on_data(self, client: TCP, data: bytes, error: Optional[int]):
        """
        Called when the session receives data
        :param client: The TCP socket that data was received on
        :param data: Raw buffer of received data
        :param error: Where an error would be
        """
        if error is not None:
            # End of file
            if error == -4095:
                self.disconnect()
            else:
                self.__logger.warning(
                    "Got unknown error {strerror} {errno} while reading from client {username}".format(
                        strerror=errno.strerror(error), errno=error, username=self.username))
                self.disconnect()
        else:
            try:
                msg = message_to_type(data).parse_and_decode(data)
                self.__logger.debug(
                    "Received {message} from user {user} with session in state {state}".format(message=msg,
                                                                                               user=self.username or "(who is not logged in)",
                                                                                               state=self.__current_state.name))
            except NotEnoughData:
                self.__logger.critical("Got invalid message ({raw}) from session {user}, shutting down".format(raw=data,
                                                                                                               user=self.username))
                self.disconnect()
            else:
                # Call the correct callback based on current protocol state
                {
                    ProtocolState.UNAUTHENTICATED: self.__msg_on_unauthenticated,
                    ProtocolState.IN_QUEUE: self.__msg_on_in_queue,
                    ProtocolState.PROCESSING_GAME_STATE: self.__msg_on_processing_game_state,
                    ProtocolState.USER_MOVE: self.__msg_on_user_move,
                    ProtocolState.GAME_END: self.__msg_on_game_end
                }[self.__current_state](msg)
                # If there is more data, keep parsing
                if len(data) > msg.calc_size() + 1:
                    self.__on_data(client, data[msg.calc_size():], None)

    # State based event handlers
    # These functions implement the Server side of the DFA
    # All of the following functions are STATEFUL

    def __msg_on_unauthenticated(self, msg: Message):
        """
        Logic to do while in Unauthenticated State
        :param msg: Message received
        """
        if isinstance(msg, Connect):
            # This is the edge of the DFA from Unauthenticated to In Queue (Connect)
            try:
                if msg.version not in self.supported_versions:
                    self.__send(InvalidVersion(min(self.supported_versions), max(self.supported_versions)))
                else:
                    # Authorize the user
                    self.__server_db.auth_user(msg.username, msg.password)
                    self.__username = msg.username
                    self.__rating = self.__server_db.get_rating(self.__username)
                    # Add the user to the queue
                    self.__server_queue.enqueue_user(self)
                    self.__send(
                        QueuePosition(len(self.__server_queue), self.__server_queue.location_of(self) + 1, self.rating))
                    self.__current_state = ProtocolState.IN_QUEUE
            except Database.UserDoesNotExist:
                # If the user does not exist, ask the client to log in again (DFA Edge from In Queue to Unauthenticated (Invalid Login))
                self.__logger.info("{user} attempted to log in but is not registered".format(user=msg.username))
                self.__send(InvalidLogin(InvalidLogin.Reasons.AccountDoesNotExist))
            except Database.InvalidPassword:
                # If the user got their password wrong, ask them to send it again (DFA Edge from In Queue to Unauthenticated (Invalid Login))
                self.__logger.info("{user} attempted to log in but got their password wrong".format(user=msg.username))
                self.__send(InvalidLogin(InvalidLogin.Reasons.InvalidPassword))
            except DuplicateUser:
                # If the user is already logged in, tell them (DFA Edge from In Queue to Unauthenticated (Invalid Login))
                self.__logger.info("{user} attempted to log in but already is logged in".format(user=msg.username))
                self.__send(InvalidLogin(InvalidLogin.Reasons.AlreadyLoggedIn))
        else:
            self.__logger.warning(
                "Received invalid message of type {type} for state {state}".format(type=msg.__class__.__name__,
                                                                                   state=self.__current_state.name))
            self.disconnect()

    def __msg_on_in_queue(self, msg: Message):
        """
        Logic to do while in the In Queue State
        :param msg: Message received
        """
        if isinstance(msg, LogOut):
            # This is the edge of the DFA from In Queue to Unauthenticated (Log Out)
            self.__logger.info("{user} logged out".format(user=self.username))
            try:
                self.__server_queue.dequeue_user(self)
            except NotInQueue:
                pass
            self.__current_state = ProtocolState.UNAUTHENTICATED
            self.__rating = None
            self.__username = None
        else:
            self.__logger.warning(
                "Received invalid message of type {type} for state {state}".format(type=msg.__class__.__name__,
                                                                                   state=self.__current_state.name))
            self.disconnect()

    def __msg_on_processing_game_state(self, msg: Message):
        """
        Logic to do while in Processing Game State state
        :param msg: Message received
        """
        if isinstance(msg, LogOut):
            # This is the edge of the DFA from Processing Game State to Unauthenticated (Log Out)
            self.__logger.info("{user} logged out".format(user=self.username))
            # User leaves game
            g = self.__game
            self.__game = None
            g.user_disconnect(self)
            self.__current_state = ProtocolState.UNAUTHENTICATED
            self.__rating = None
            self.__username = None
        else:
            self.__logger.warning(
                "Received invalid message of type {type} for state {state}".format(type=msg.__class__.__name__,
                                                                                   state=self.__current_state.name))
            self.disconnect()

    def __msg_on_user_move(self, msg: Message):
        """
        Logic to do while in User Move state
        :param msg: Message received
        """
        if isinstance(msg, MakeMove):
            # This is the edge of the DFA from User Move to Processing Game State (Make Move)
            try:
                self.__current_state = ProtocolState.PROCESSING_GAME_STATE
                self.__game.apply_move(msg.move, self)
                self.__logger.info("{} made move {}".format(self.username, msg.move.__repr__()))
            except InvalidMoveException:
                self.__current_state = ProtocolState.USER_MOVE
                self.__send(InvalidMove(msg.move, self.__game.get_board(self)))
        elif isinstance(msg, LogOut):
            # This is the edge of the DFA from User Move to Unauthenticated (Log Out)
            self.__logger.info("{user} logged out".format(user=self.username))
            # User leaves game
            g = self.__game
            self.__game = None
            g.user_disconnect(self)
            self.__username = None
            self.__rating = None
            self.__current_state = ProtocolState.UNAUTHENTICATED
        else:
            self.__logger.warning(
                "Received invalid message of type {type} for state {state}".format(type=msg.__class__.__name__,
                                                                                   state=self.__current_state.name))
            self.disconnect()

    def __msg_on_game_end(self, msg: Message):
        """
        Logic to do while in Game End state
        :param msg: Message received
        """
        if isinstance(msg, MakeMove):
            # This is not in the DFA - NEED TO ADD
            # (for when the client and server are one step out of sync and the client's opponent left)
            if not self.__game:
                self.__logger.info(
                    "{user} made a move while in game end, happened because client and server were out of sync".format(
                        user=self.username))
            else:
                self.__logger.warning(
                    "Received invalid MakeMove message from {user} for state {state}".format(user=self.username,
                                                                                             state=self.__current_state.name))
        elif isinstance(msg, ReQueue):
            # This is the edge of the DFA from Game End to In Queue (ReQueue)
            self.__logger.info("{user} has rejoined the queue".format(user=self.username))
            self.__server_queue.enqueue_user(self)
            self.__current_state = ProtocolState.IN_QUEUE
            self.__send(QueuePosition(len(self.__server_queue), self.__server_queue.location_of(self) + 1, self.rating))
        elif isinstance(msg, LogOut):
            # This is the edge of the DFA from Game End to Unauthenticated (Log Out)
            self.__logger.info("{user} logged out".format(user=self.username))
            self.__username = None
            self.__rating = None
            self.__game = None
            self.__current_state = ProtocolState.UNAUTHENTICATED
        else:
            self.__logger.warning(
                "Received invalid message of type {type} for state {state}".format(type=msg.__class__.__name__,
                                                                                   state=self.__current_state.name))
            self.disconnect()

    # Operators

    def __eq__(self, other: "Session") -> bool:
        return self.__username == other.__username
