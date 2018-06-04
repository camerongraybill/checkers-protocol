""" This file contains the Game class which represents a game between two players.
It implements the majority of the game logic. """

from logging import Logger
from random import choice

from internal_types.types import Board, Move, Direction, InvalidMove


class InvalidMoveException(Exception):
    """ Invalid Move """


class InvalidGameException(Exception):
    """ Raised when the game is in an invalid state """


class Game:
    """ Game represents a Checkers game between two players """

    def __init__(self, player_one: "Session", player_two: "Session", logger: Logger):
        """
        A Game takes two players, assign the one with lower rating to be player one and go first
        Also generate a default board start
        :param player_one: The first player in the game
        :param player_two: The second player in the game
        """
        if player_one.username == player_two.username:
            logger.warning("Attempting to start game between two of {user}".format(user=player_one.username))
            raise InvalidGameException()
        if player_one.rating < player_two.rating:
            self.__player_one = player_one
            self.__player_two = player_two
        else:
            self.__player_one = player_two
            self.__player_two = player_one
        self.__logger = logger
        self.__board = Board.generate_game_start()
        player_one.on_game_start(player_two.username, player_two.rating, self)
        player_two.on_game_start(player_one.username, player_one.rating, self)

        self.__next_to_go = self.__player_one
        # Request a move from the first player
        self.__next_to_go.on_request_move(Move(0, 0, Direction.Negative, Direction.Negative), self.__board)

    def user_disconnect(self, user: "Session"):
        """
        Called when a user disconnects
        :param user: The user that disconnected
        """
        self.__logger.info("{user} disconnected from their game".format(user=user.username))
        self.__get_opponent(user).on_opponent_disconnect()

    def get_board(self, user: "Session") -> Board:
        """
        Get the board from the given user's point of view
        :param user: The user to get the board for
        :return: A board that might be switched
        """
        if self.__is_primary(user):
            return self.__board
        else:
            return self.__board.translate_to_other_user()

    def apply_move(self, move: Move, user: "Session"):
        """
        Apply a Move, raise InvalidMoveException if the move is invalid.
        Process internal state until user input is again needed
        :param move: The move to apply
        :param user: The user that made the move
        """
        self.__logger.info("{user} is trying to apply move {move}".format(user=user.username, move=move.__repr__()))
        # If it is an invalid move for that user
        if self.__next_to_go != user:
            self.__logger.info("{user} failed to apply a move because it was not their turn".format(user=user.username))
            raise InvalidMoveException()
        allowed_y_direction = self.__get_allowed_direction(user)
        is_primary_player = self.__is_primary(user)
        # Try applying the move to the lower level Board type, raise InvalidMoveException if it fails
        try:
            self.__board.apply_move(move, allowed_y_direction, is_primary_player)
        except InvalidMove:
            raise InvalidMoveException()

        # After applying the move, switch to the next player

        self.__next_to_go = self.__get_opponent(user)
        # Process game state (making compulsory moves and switching players turns as needed)

        last_move = self.__process_game_state()
        # The last move made was either the one process_game_state returned or the one the last user made
        last_move = last_move or move
        # Check if either player won
        if self.__board.check_game_over(True):
            self.__finish_game(self.__player_one, last_move)
        elif self.__board.check_game_over(False):
            self.__finish_game(self.__player_two, last_move)
        else:
            # Lastly, get a move from whichever player needs to go next
            self.__next_to_go.on_request_move(last_move, self.get_board(self.__next_to_go))

    def __process_game_state(self) -> Move:
        """
        Process the internal game state without input from players until input from players is needed
        :return: The last move that was made
        """
        allowed_y_direction = self.__get_allowed_direction(self.__next_to_go)
        is_primary_player = self.__is_primary(self.__next_to_go)
        # Get a list of moves that the current player MUST make
        compulsive_moves = self.__board.get_required_moves(allowed_y_direction, is_primary_player)
        piece_to_move = None
        compulsive_move: Move = None
        while compulsive_moves:
            compulsive_move: Move = choice(compulsive_moves)
            self.__logger.info("Applying compulsive move {move} in game between {first} and {second}".format(
                move=compulsive_move.__repr__(), first=self.__player_one.username, second=self.__player_two.username))
            self.__board.apply_move(compulsive_move, allowed_y_direction, is_primary_player)
            self.__player_one.on_compulsory_move(compulsive_move, self.get_board(self.__player_one))
            self.__player_two.on_compulsory_move(compulsive_move, self.get_board(self.__player_two))
            # Can only move the same piece multiple times
            piece_to_move = compulsive_move.after_double_move_pos

            compulsive_moves = [x for x in self.__board.get_required_moves(allowed_y_direction, is_primary_player)
                                if x.pos == piece_to_move]
        # If a move was made, check if the next player has any moves to make
        if piece_to_move:
            self.__next_to_go = self.__get_opponent(self.__next_to_go)
            return self.__process_game_state() or compulsive_move
        return compulsive_move

    def __get_allowed_direction(self, user: "Session") -> Direction:
        """
        Get the direction a user is allowed to move non promoted pieces
        :param user:
        :return: The direction the user can move pieces
        """
        return Direction.Negative if self.__is_primary(user) else Direction.Positive

    def __is_primary(self, user: "Session") -> bool:
        """
        Check if a user is the primary user
        :param user:
        :return: True if the user is the primary user, false otherwise
        """
        return user.username == self.__player_one.username

    def __finish_game(self, winner: "Session", last_move: Move):
        """
        Called to finish the game
        :param winner:
        :param last_move:
        """
        loser = self.__get_opponent(winner)
        self.__logger.info("{winner} beat {loser}".format(winner=winner.username, loser=loser.username))
        winner.on_game_end(last_move, self.get_board(winner), 10, True)
        loser.on_game_end(last_move, self.get_board(loser), -10, False)

    def __get_opponent(self, user: "Session") -> "Session":
        """
        Get the opponent of a user
        :param user:
        :return:
        """
        if self.__is_primary(user):
            return self.__player_two
        else:
            return self.__player_one
