from getpass import getpass

from internal_types.types import Direction, Move


class Interface:

    def display_message(self, message):
        print(message)

    def display(self, board: "Board"):
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

    def get_move(self):
        def get_location():
            try:
                x = int(input("X value for piece to move:"))
                y = int(input("Y value for piece to move:"))
                return x - 1, y - 1
            except ValueError:
                self.display_message("Please enter values from 1-8")
                return get_location()

        def get_direction():
            left = input("Would you like to move the piece left or right? (left/right)") == "left"
            up = input("Would you like to move the piece up or down? (up/down)") == "up"
            x_dir = Direction.Negative if left else Direction.Positive
            y_dir = Direction.Negative if up else Direction.Positive
            return x_dir, y_dir

        location = get_location()
        direction = get_direction()
        return Move(*location, *direction)

    def game_over(self, final_board, old_rating, new_rating, you_won):
        self.display(final_board)
        if you_won:
            self.display_message("You won!")
        else:
            self.display_message("You lost :(")
        self.display_message("Your Rating changed from {} -> {}".format(old_rating, new_rating))

    def prompt_play_again(self):
        return input("Play again? yes/no") == "yes"

    def request_creds(self):
        return str.encode(input("Please input your Username: ")), str.encode(getpass("Please input your Password:"))

    def show_queue_position(self, position, rating, queue_size):
        self.display_message("Position in Queue: {}, Rating: {}, Queue size: {}".format(position, rating, queue_size))

    def game_start(self, opponent_name, opponent_rating):
        self.display_message("Starting game vs {} ({})".format(opponent_name, opponent_rating))

    def opponent_left(self):
        self.display_message("Your Opponent Disconnected")
