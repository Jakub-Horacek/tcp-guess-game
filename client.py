import socket
import struct
import sys

def print_colored(text, color_code):
    print(f"\033[{color_code}m{text}\033[0m")

def connect_to_server(address):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(address)

    # Receive initiation message
    data = client_socket.recv(1024)
    if data == b'\x01HELLO':
        client_socket.send(struct.pack('!B13s', 0x02, b'my_secret_password'))

        # Receive ID or error
        data = client_socket.recv(1024)
        response_code = data[0]
        if response_code == 0x03:
            client_id = struct.unpack('!I', data[1:5])[0]
            print_colored(f"Connected successfully with client ID: {client_id}", "32")
            return client_socket, client_id
        elif response_code == 0x04:
            print_colored("Invalid password", "31")
            client_socket.close()
            return None, None

def request_opponents(client_socket):
    client_socket.send(b'\x05')
    data = client_socket.recv(1024)
    if data[0] == 0x06:
        num_opponents = struct.unpack('!I', data[1:5])[0]
        opponent_ids = list(data[5:5+num_opponents])
        print_colored(f"Available opponents: {opponent_ids}", "34")
        return opponent_ids

def request_match(client_socket, opponent_id, word):
    word_length = len(word)
    client_socket.send(struct.pack('!BIB', 0x07, opponent_id, word_length) + word.encode())
    data = client_socket.recv(1024)
    if data == b'\x09MATCH CONFIRMED':
        print_colored("Match confirmed", "32")
    elif data == b'\x0AERROR: INVALID OPPONENT ID':
        print_colored("Error: Invalid opponent ID", "31")

def send_guess(client_socket, opponent_id, guess):
    guess_length = len(guess)
    client_socket.send(struct.pack('!BIB', 0x0B, opponent_id, guess_length) + guess.encode())
    data = client_socket.recv(1024)
    response_code = data[0]
    if response_code == 0x0C:
        print_colored("Guess is correct!", "32")
    elif response_code == 0x0E:
        print_colored("Wrong guess. Try again.", "31")
    elif response_code == 0x0A:
        print_colored("Error: No active match.", "31")

def send_hint(client_socket, opponent_id, hint):
    hint_length = len(hint)
    client_socket.send(struct.pack('!BIB', 0x0F, opponent_id, hint_length) + hint.encode())
    data = client_socket.recv(1024)
    response_code = data[0]
    if response_code == 0x0A:
        print_colored("Error: No active match.", "31")
    else:
        print_colored(f"Hint sent to opponent {opponent_id}", "32")

def print_rules():
    rules = """
    Welcome to the Guessing Game!

    How to Play:
    1. Connect to the server using 'python3 client.py'.
    2. List available opponents by entering 'o'.
    3. Request a match by entering 'm', specify the opponent ID and the word to guess.
    4. If you are the guesser, enter 'g' to guess the word.
    5. If you are the hint giver, enter 'h' to send a hint.
    6. Quit the game by entering 'q'.

    Enjoy the game!
    """
    print_colored(rules, "36")

if __name__ == "__main__":
    server_address = ('127.0.0.1', 12345)
    client_socket, client_id = connect_to_server(server_address)
    if client_socket:
        while True:
            action = input("Enter 'o' to list opponents, 'm' to request match, 'g' to guess, 'h' to send hint, 'r' to print rules, or 'q' to quit: ")
            if action == 'o':
                request_opponents(client_socket)
            elif action == 'm':
                opponent_id = int(input("Enter opponent ID: "))
                word = input("Enter the word to guess: ")
                request_match(client_socket, opponent_id, word)
            elif action == 'g':
                opponent_id = int(input("Enter opponent ID: "))
                guess = input("Enter your guess (a word or letter): ")
                send_guess(client_socket, opponent_id, guess)
            elif action == 'h':
                opponent_id = int(input("Enter opponent ID: "))
                hint = input("Enter your hint: ")
                send_hint(client_socket, opponent_id, hint)
            elif action == 'r':
                print_rules()
            elif action == 'q':
                break

        client_socket.close()
