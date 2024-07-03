import socket
import threading
import struct

PASSWORD = b'my_secret_password'
clients = {}
matches = {}
next_client_id = 1
clients_lock = threading.Lock()

def handle_client(client_socket, client_address):
    global next_client_id
    client_id = None
    try:
        # Send initiation message
        client_socket.send(b'\x01HELLO')

        # Receive password
        data = client_socket.recv(1024)
        if data == struct.pack('!B13s', 0x02, PASSWORD):
            with clients_lock:
                client_id = next_client_id
                next_client_id += 1
                clients[client_id] = client_socket
            client_socket.send(struct.pack('!BI', 0x03, client_id))
        else:
            client_socket.send(b'\x04INVALID PASSWORD')
            client_socket.close()
            return

        # Handle further commands
        while True:
            data = client_socket.recv(1024)
            if not data:
                break

            command = data[0]
            if command == 0x05:  # List opponents
                with clients_lock:
                    opponent_ids = [cid for cid in clients if cid != client_id]
                response = struct.pack('!BI', 0x06, len(opponent_ids)) + bytes(opponent_ids)
                client_socket.send(response)
            elif command == 0x07:  # Request match
                opponent_id = struct.unpack('!I', data[1:5])[0]
                word_length = struct.unpack('!B', data[5:6])[0]
                word_to_guess = data[6:6+word_length].decode()
                if opponent_id in clients:
                    matches[(client_id, opponent_id)] = {'word': word_to_guess, 'attempts': []}
                    clients[opponent_id].send(struct.pack('!BI', 0x08, client_id))
                    client_socket.send(b'\x09MATCH CONFIRMED')
                else:
                    client_socket.send(b'\x0AERROR: INVALID OPPONENT ID')
            elif command == 0x0B:  # Guess word
                opponent_id, guess_length = struct.unpack('!IB', data[1:6])
                guess = data[6:6+guess_length].decode()
                match = matches.get((opponent_id, client_id))
                if match:
                    match['attempts'].append(guess)
                    if guess == match['word']:
                        client_socket.send(b'\x0CSUCCESS')
                        clients[opponent_id].send(struct.pack('!B', 0x0D) + b'SUCCESS')
                        del matches[(opponent_id, client_id)]
                    else:
                        client_socket.send(b'\x0EWRONG GUESS')
                        clients[opponent_id].send(struct.pack('!B', 0x0E) + b'WRONG GUESS')
                else:
                    client_socket.send(b'\x0AFERROR: NO MATCH')
            elif command == 0x0F:  # Send hint
                opponent_id, hint_length = struct.unpack('!IB', data[1:6])
                hint = data[6:6+hint_length].decode()
                if (client_id, opponent_id) in matches:
                    clients[opponent_id].send(struct.pack('!B', 0x10) + hint.encode())
                else:
                    client_socket.send(b'\x0AFERROR: NO MATCH')

    except Exception as e:
        print(f"Exception: {e}")
    finally:
        if client_id in clients:
            with clients_lock:
                del clients[client_id]
        client_socket.close()

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 12345))
    server_socket.listen(5)
    print("Server started on port 12345")

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"Accepted connection from {client_address}")
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_thread.start()

if __name__ == "__main__":
    start_server()
