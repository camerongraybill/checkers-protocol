from pyuv import TCP, errno

from internal_types.messages import message_to_type, Message, Connect, InvalidLogin, InvalidVersion, QueuePosition, \
    LogOut, MakeMove, ReQueue, CompulsoryMove, YourTurn, InvalidMove, GameOver, OpponentDisconnect, GameStart
from internal_types.states import ProtocolState
from .db import Database
from .game import InvalidMoveException
from .queue import DuplicateUser, NotInQueue


class Session:
    def __init__(self, handle: TCP, queue, database_connection: Database):
        self.__handle = handle
        self.current_state = ProtocolState.UNAUTHENTICATED
        self.__server_queue = queue
        self.__server_db = database_connection
        self.__game: "Game" = None
        self.__rating = None
        self.__username = None
        handle.start_read(self.on_data)

    def disconnect(self, force=False):
        if not force:
            if self in self.__server_queue:
                self.__server_queue.dequeue_user(self)
            if self.__game:
                self.__game.user_disconnect(self)
                self.__game = None
            self.__rating = None
            self.__username = None
            self.current_state = ProtocolState.UNAUTHENTICATED
        try:
            self.__handle.stop_read()
            self.__handle.shutdown()
        except:
            pass

    def __eq__(self, other):
        return self.__username == other.__username

    def __msg_on_unauthenticated(self, msg: Message):
        if isinstance(msg, Connect):
            try:
                if msg.version != 1:
                    self.__handle.write(InvalidVersion(1, 1).encode())
                else:
                    self.__server_db.auth_user(msg.username, msg.password)
                    self.__username = msg.username
                    self.__rating = self.__server_db.get_rating(self.__username)
                    self.__server_queue.enqueue_user(self)
                    self.__handle.write(
                        QueuePosition(len(self.__server_queue), self.__server_queue.location_of(self) + 1,
                                      self.rating).encode())
                    self.current_state = ProtocolState.IN_QUEUE
            except Database.UserDoesNotExist:
                self.__handle.write(InvalidLogin(InvalidLogin.Reasons.AccountDoesNotExist).encode())
            except Database.InvalidPassword:
                self.__handle.write(InvalidLogin(InvalidLogin.Reasons.InvalidPassword).encode())
            except DuplicateUser:
                self.__handle.write(InvalidLogin(InvalidLogin.Reasons.AlreadyLoggedIn).encode())
        else:
            print("Invalid message on unauthenticated: {}".format(msg.__class__.__name__))
            self.disconnect()

    def __msg_on_in_queue(self, msg: Message):
        if isinstance(msg, LogOut):
            print("User {} has Logged Out".format(self.__username))
            try:
                self.__server_queue.dequeue_user(self)
            except NotInQueue:
                pass
            self.current_state = ProtocolState.UNAUTHENTICATED
            self.__rating = None
            self.__username = None
        else:
            print("Invalid message on in queue: {}".format(msg.__class__.__name__))
            self.disconnect()

    def __msg_on_processing_game_state(self, msg: Message):
        if isinstance(msg, LogOut):
            print("User {} logged out".format(self.__username))
            # User leaves game
            self.__game.user_disconnect(self)
            self.current_state = ProtocolState.UNAUTHENTICATED
            self.__rating = None
            self.__username = None
        else:
            print("Invalid message on in queue: {}".format(msg.__class__.__name__))
            self.disconnect()

    def __msg_on_user_move(self, msg: Message):
        if isinstance(msg, MakeMove):
            print("User {} made a move!".format(self.__username))
            # send a response based on the outcome of the function
            try:
                self.current_state = ProtocolState.PROCESSING_GAME_STATE
                self.__game.apply_move(msg.move, self)
            except InvalidMoveException:
                self.current_state = ProtocolState.USER_MOVE
                self.__handle.write(InvalidMove(msg.move, self.__game.get_board(self)).encode())
        elif isinstance(msg, LogOut):
            print("User {} logged out during make move!".format(self.__username))
            self.__game.user_disconnect(self)
            self.__game = None
            self.__username = None
            self.__rating = None
            self.current_state = ProtocolState.UNAUTHENTICATED
        else:
            print("Invalid message on on user move: {}".format(msg.__class__.__name__))
            self.disconnect()

    def __msg_on_game_end(self, msg: Message):
        if isinstance(msg, ReQueue):
            print("User {} reentered the queue".format(self.__username))
            self.__server_queue.enqueue_user(self)
            self.current_state = ProtocolState.IN_QUEUE
            self.__handle.write(
                QueuePosition(len(self.__server_queue), self.__server_queue.location_of(self), self.rating).encode())
        elif isinstance(msg, LogOut):
            self.__username = None
            self.__rating = None
            self.__game = None
            self.current_state = ProtocolState.UNAUTHENTICATED
        else:
            print("Invalid message on game end: {}".format(msg.__class__.__name__))
            self.disconnect()

    def on_data(self, client: TCP, data, error):
        # Get parse the message
        if error is not None:
            # End of file
            if error == -4095:
                self.disconnect()
            else:
                print("Unknown error: {}, {}".format(errno.strerror(error), error))
        else:
            msg = message_to_type(data).parse_and_decode(data)
            print("got: {} from {}".format(msg, self.__username))
            {
                ProtocolState.UNAUTHENTICATED: self.__msg_on_unauthenticated,
                ProtocolState.IN_QUEUE: self.__msg_on_in_queue,
                ProtocolState.PROCESSING_GAME_STATE: self.__msg_on_processing_game_state,
                ProtocolState.USER_MOVE: self.__msg_on_user_move,
                ProtocolState.GAME_END: self.__msg_on_game_end
            }[self.current_state](msg)

    def on_compulsory_move(self, move, board):
        self.__handle.write(CompulsoryMove(move, board).encode())
        self.current_state = ProtocolState.PROCESSING_GAME_STATE

    def request_move(self, last_move, board):
        self.__handle.write(YourTurn(last_move, board).encode())
        self.current_state = ProtocolState.USER_MOVE

    def on_game_end(self, last_move, board, rating_change, winner):
        self.__handle.write(
            GameOver(winner, self.__rating + rating_change, self.__rating, last_move, board).encode())
        self.__server_db.set_rating(self.__username, self.__rating + rating_change)
        self.__rating = self.__rating + rating_change
        self.current_state = ProtocolState.GAME_END

    def on_opponent_disconnect(self):
        print("My opponent disconnected")
        self.__handle.write(OpponentDisconnect().encode())
        self.current_state = ProtocolState.GAME_END

    def on_queue_position(self, queue_size, queue_position):
        self.__handle.write(QueuePosition(queue_size, queue_position, self.rating).encode())

    def on_game_start(self, opponent_name, opponent_rating):
        self.__handle.write(GameStart(opponent_name, opponent_rating).encode())
        self.current_state = ProtocolState.PROCESSING_GAME_STATE

    def join_game(self, game):
        self.__game = game

    @property
    def username(self):
        return self.__username

    @property
    def rating(self):
        return self.__rating
