from random import choice

from internal_types.types import Board, Move, Direction, InvalidMove


class InvalidMoveException(Exception):
    """ Invalid Move """


class Game:
    def __init__(self, player_one, player_two):
        if player_one.rating < player_two.rating:
            self.__player_one = player_one
            self.__player_two = player_two
        else:
            self.__player_one = player_two
            self.__player_two = player_one
        self.__board = Board.generate_game_start()
        player_one.on_game_start(player_two.username, player_two.rating)
        player_two.on_game_start(player_one.username, player_one.rating)

        self.__next_to_go = self.__player_one
        self.__next_to_go.request_move(Move(0, 0, Direction.Negative, Direction.Negative), self.__board)

    def finish_game(self, winner, last_move):
        # At some point call self.__player_one.on_game_end() and self.__player_two.on_game_end()
        loser = self.get_opponent(winner)
        winner.on_game_end(last_move, self.get_board(winner), 10, True)
        loser.on_game_end(last_move, self.get_board(loser), -10, False)

    def get_opponent(self, user):
        if user.username == self.__player_one.username:
            return self.__player_two
        else:
            return self.__player_one

    def apply_move(self, move, user):
        # If it is an invalid move for that user
        if self.__next_to_go != user:
            raise InvalidMoveException()
        allowed_y_direction = self.__get_allowed_direction(user)
        is_primary_player = self.__is_primary(user)
        try:
            self.__board.apply_move(move, allowed_y_direction, is_primary_player)
        except InvalidMove:
            raise InvalidMoveException()

        # After applying the move, switch to the next player

        self.__next_to_go = self.get_opponent(user)
        # Process game state (making compulsory moves and switching players turns as needed)

        last_move = self.__process_game_state()
        last_move = last_move if last_move is not None else move
        # Check if either player won
        if self.__board.check_game_over(True):
            self.finish_game(self.__player_one, last_move)
        elif self.__board.check_game_over(False):
            self.finish_game(self.__player_two, last_move)
        else:
            # Lastly, get a move from whichever player needs to go next
            self.__next_to_go.request_move(last_move, self.get_board(self.__next_to_go))

    def __process_game_state(self):
        allowed_y_direction = self.__get_allowed_direction(self.__next_to_go)
        is_primary_player = self.__is_primary(self.__next_to_go)

        compulsive_moves = self.__board.get_required_moves(allowed_y_direction, is_primary_player)
        piece_to_move = None
        compulsive_move: Move = None
        while compulsive_moves:
            # print("Compulsive moves: {}".format(compulsive_moves))
            compulsive_move: Move = choice(compulsive_moves)
            self.__board.apply_move(compulsive_move, allowed_y_direction, is_primary_player)
            self.__player_one.on_compulsory_move(compulsive_move, self.get_board(self.__player_one))
            self.__player_two.on_compulsory_move(compulsive_move, self.get_board(self.__player_two))
            piece_to_move = compulsive_move.after_double_move_pos

            compulsive_moves = [x for x in self.__board.get_required_moves(allowed_y_direction, is_primary_player)
                                if x.pos == piece_to_move]

        if piece_to_move:
            self.__next_to_go = self.get_opponent(self.__next_to_go)
            return self.__process_game_state() or compulsive_move
        return compulsive_move

    def __get_allowed_direction(self, user):
        return Direction.Negative if user.username == self.__player_one.username else Direction.Positive

    def __is_primary(self, user):
        return user.username == self.__player_one.username

    def user_disconnect(self, user):
        self.get_opponent(user).on_opponent_disconnect()

    def get_board(self, user):
        if user.username == self.__player_one.username:
            return self.__board
        else:
            return self.__board.translate_to_other_user()
