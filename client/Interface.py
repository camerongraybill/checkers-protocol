"""
This file contains the Interface class. It provides the basic hooks that the Client needs
into the interface to get all the needed user input. Very basic interface.
"""

from getpass import getpass
from typing import Tuple

from internal_types.types import Direction, Move, Board


class Interface:
    """
    Basic user interface
    """

    def display_message(self, message: str):
        """
        Print a message to the screen
        :param message:
        """
        print(message)

    def display(self, board: Board):
        """
        Display a Board on the screen
        :param board: The Board to display
        """
        print("___________________")
        print("| |1|2|3|4|5|6|7|8|")
        for i in reversed(range(8)):
            print("-------------------")
            output_str = "|{}|".format(8 - i)
            for j in reversed(range(8)):
                pos = board[j, i]
                if not pos.used:
                    letter = ' '
                elif pos.owner and pos.promoted:
                    letter = 'O'
                elif pos.owner and not pos.promoted:
                    letter = 'o'
                elif not pos.owner and pos.promoted:
                    letter = 'X'
                elif not pos.owner and not pos.promoted:
                    letter = 'x'
                else:
                    raise Exception("Invalid Board")
                output_str += "{}|".format(letter)
            print(output_str)
        print("-------------------")

    def get_move(self) -> Move:
        def get_location():
            try:
                x = int(input("X value for piece to move:"))
                y = int(input("Y value for piece to move:"))
                return x - 1, y - 1
            except ValueError:
                self.display_message("Please enter values from 1-8")
                return get_location()

        def get_direction():
            def get_x_dir():
                first_input = input("Would you like to move the piece left or right? (left/right): ")
                if first_input == "left":
                    return Direction.Negative
                elif first_input == "right":
                    return Direction.Positive
                else:
                    return get_x_dir()

            def get_y_dir():
                first_input = input("Would you like to move the piece up or down? (up/down): ")
                if first_input == "up":
                    return Direction.Negative
                elif first_input == "down":
                    return Direction.Positive
                else:
                    return get_y_dir()

            return get_x_dir(), get_y_dir()

        return Move(*get_location(), *get_direction())

    def game_over(self, final_board: Board, old_rating: int, new_rating: int, you_won: bool):
        """
        Display a game end
        :param final_board: Board at the end of the game
        :param old_rating: Rating before the game
        :param new_rating: Rating after the game
        :param you_won: If the user won ro not
        """
        self.display(final_board)
        if you_won:
            self.display_message("You won!")
        else:
            self.display_message("You lost :(")
        self.display_message("Your Rating changed from {} -> {}".format(old_rating, new_rating))

    def prompt_play_again(self) -> bool:
        """
        Ask the player if they want to play again
        :return: Whether or not the User wants to play again
        """
        input_str = input("Play again? yes/no: ")
        if input_str == "yes":
            return True
        elif input_str == "no":
            return False
        else:
            return self.prompt_play_again()

    def request_creds(self) -> Tuple[bytes, bytes]:
        """
        Prompt the user for username and password
        :return: Username and password
        """
        return self.request_username(), self.request_pass()

    def request_username(self) -> bytes:
        """
        Prompt the user for a username
        :return: Username
        """
        return str.encode(input("Please input your Username: "))

    def request_pass(self) -> bytes:
        """
        Prompt the user for their password
        :return: Password
        """
        return str.encode(getpass("Please input your Password: "))

    def show_queue_position(self, position: int, rating: int, queue_size: int):
        """
        Update in the UI where the user is in queue currently
        :param position: Position in Queue
        :param rating: The User's current rating
        :param queue_size: The length of the queue
        """
        self.display_message("Position in Queue: {}, Rating: {}, Queue size: {}".format(position, rating, queue_size))

    def game_start(self, opponent_name: str, opponent_rating: int):
        """
        Message for when a game starts
        :param opponent_name: The name of the opponent
        :param opponent_rating: The rating of the opponent
        """
        self.display_message("Starting game vs {} ({})".format(opponent_name, opponent_rating))

    def opponent_left(self):
        """
        Display when an opponent leaves
        """
        self.display_message("Your Opponent Disconnected")
