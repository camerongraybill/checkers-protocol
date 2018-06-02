from signal import SIGINT

from pyuv import Loop, TCP, errno, Signal

from internal_types.messages import Connect, Message, message_to_type, InvalidLogin, InvalidVersion, QueuePosition, \
    GameStart, LogOut, CompulsoryMove, InvalidMove, GameOver, OpponentDisconnect, YourTurn, MakeMove, ReQueue
from internal_types.states import ProtocolState
from .Interface import Interface


class Client:
    def __init__(self, ip: str, port: int, username: bytes, password: bytes, interface: Interface):
        self.__ip = ip
        self.__port = port
        self.__handle: TCP = None
        self.__interrupt_handle = None
        self.__username = username
        self.__password = password
        self.__protocol_state = ProtocolState.UNAUTHENTICATED
        self.__ui = interface

    def shutdown(self):
        if self.__protocol_state != ProtocolState.UNAUTHENTICATED:
            self.__handle.write(LogOut().encode())
        self.close()

    def on_signal(self, sig_handler, signal):
        self.shutdown()

    def __msg_on_unauthenticated(self, msg: Message):
        print("Should not receive any message in Unauthenticated state, shutting down")
        self.shutdown()

    def __msg_on_in_queue(self, msg: Message):
        if isinstance(msg, InvalidLogin):
            self.__protocol_state = ProtocolState.UNAUTHENTICATED
            self.__username, self.__password = self.__ui.request_creds()
            self.__handle.write(Connect(1, self.__username, self.__password).encode())
            self.__protocol_state = ProtocolState.IN_QUEUE
        elif isinstance(msg, InvalidVersion):
            self.__ui.display_message(
                "The Server does not support your version of the client, it supports versions {}-{}".format(
                    msg.lowest_supported_version, msg.highest_supported_version))
            self.shutdown()
        elif isinstance(msg, QueuePosition):
            self.__ui.show_queue_position(msg.queue_pos, msg.rating, msg.queue_size)
        elif isinstance(msg, GameStart):
            self.__ui.game_start(msg.opponent_name.decode("utf-8"), msg.opponent_rating)
            self.__protocol_state = ProtocolState.PROCESSING_GAME_STATE
        else:
            print("Should not ever happen, got message {} in queue".format(msg.__class__.__name__))
            self.shutdown()

    def __msg_on_processing_game_state(self, msg: Message):
        if isinstance(msg, YourTurn):
            self.__protocol_state = ProtocolState.USER_MOVE
            self.__ui.display(msg.board)
            self.__handle.write(MakeMove(self.__ui.get_move()).encode())
            self.__protocol_state = ProtocolState.PROCESSING_GAME_STATE
        elif isinstance(msg, CompulsoryMove):
            self.__ui.display(msg.board)
        elif isinstance(msg, InvalidMove):
            self.__protocol_state = ProtocolState.USER_MOVE
            self.__ui.display_message("Invalid Move!")
            self.__ui.display(msg.board)
            self.__handle.write(MakeMove(self.__ui.get_move()).encode())
            self.__protocol_state = ProtocolState.PROCESSING_GAME_STATE
        elif isinstance(msg, GameOver):
            self.__protocol_state = ProtocolState.GAME_END
            self.__ui.game_over(msg.board, msg.old_rating, msg.new_rating, msg.you_won)
            if self.__ui.prompt_play_again():
                self.__protocol_state = ProtocolState.IN_QUEUE
                self.__handle.write(ReQueue().encode())
            else:
                self.shutdown()

        elif isinstance(msg, OpponentDisconnect):
            self.__protocol_state = ProtocolState.GAME_END
            self.__ui.opponent_left()
            if self.__ui.prompt_play_again():
                self.__protocol_state = ProtocolState.IN_QUEUE
                self.__handle.write(ReQueue().encode())
            else:
                self.shutdown()
        else:
            print("Should not ever happen, got message {} in queue".format(msg.__class__.__name__))
            self.shutdown()

    def __msg_on_user_move(self, msg: Message):
        if isinstance(msg, OpponentDisconnect):
            self.__protocol_state = ProtocolState.GAME_END
            self.__ui.opponent_left()
            if self.__ui.prompt_play_again():
                self.__protocol_state = ProtocolState.IN_QUEUE
                self.__handle.write(ReQueue().encode())
            else:
                self.shutdown()
        else:
            print("Should not ever happen, got message {} on user move".format(msg.__class__.__name__))
            self.shutdown()

    def __msg_on_game_end(self, msg: Message):
        print("Should not receive any messages in the state game end, got {}".format(msg.__class__.__name__))
        self.shutdown()

    def on_data(self, client: TCP, data, error):
        if error is not None:
            if error == -4095:
                self.shutdown()
            else:
                print("Unknown error: {}".format(errno.strerror(error)))
        else:
            # Get parse the message
            msg = message_to_type(data).parse_and_decode(data)
            print("Got {}".format(msg))
            {
                ProtocolState.UNAUTHENTICATED: self.__msg_on_unauthenticated,
                ProtocolState.IN_QUEUE: self.__msg_on_in_queue,
                ProtocolState.PROCESSING_GAME_STATE: self.__msg_on_processing_game_state,
                ProtocolState.USER_MOVE: self.__msg_on_user_move,
                ProtocolState.GAME_END: self.__msg_on_game_end
            }[self.__protocol_state](msg)

    def on_connection_start(self, handler: TCP, error):
        handler.start_read(self.on_data)
        handler.write(Connect(1, self.__username, self.__password).encode())
        self.__protocol_state = ProtocolState.IN_QUEUE

    def start(self, loop: Loop):
        self.__handle = TCP(loop)
        self.__handle.connect((self.__ip, self.__port), self.on_connection_start)

        self.__interrupt_handle = Signal(loop)
        self.__interrupt_handle.start(self.on_signal, SIGINT)

    def close(self):
        self.__handle.stop_read()
        self.__handle.shutdown()
        self.__interrupt_handle.close()
