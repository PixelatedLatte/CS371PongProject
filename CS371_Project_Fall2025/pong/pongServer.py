# =================================================================================================
# Contributing Authors:	    Jacob Blankenship, Daniel Krutsick
# Email Addresses:          jrbl245@uky.edu, djkr228@uky.edu
# Date:                     11/3/2025
# Purpose:                  The Server member of our Pong game
# Misc:                     <Not Required.  Anything else you might want to include>
# =================================================================================================
# TO FREE UP PORT NUMBER ON WINDOWS, USE THE FOLLOWING COMMAND IN CMD:
# netstat -ano | findstr :<your_port_number>
# THIS WILL GIVE YOU THE PID OF THE PROCESS USING THE PORT
# THEN USE THE COMMAND:
# taskkill /PID <that_pid> /

import socket
import threading

clients = []

def broadcast(message, sender):
    for client in clients:
        if client != sender:
            try:#Successfully sent message
                client.sendall(message)
            except:#Send failed, remove client with error
                clients.remove(client)


# Regex to parse each game message
MSG_PATTERN = re.compile(
    r'PADDLENAME:(?P<name>\w+):PADDLEPOS:(?P<pos>\d+):BX:(?P<bx>\d+):BY:(?P<by>\d+):LSCORE:(?P<lscore>\d+):RSCORE:(?P<rscore>\d+):TIME:(?P<time>\d+)'
)

def parse_game_state(message: str) -> dict:
    """Parses a single game message into a dictionary."""
    match = MSG_PATTERN.match(message)
    if match:
        data = match.groupdict()
        # Convert numeric values to int
        for key in ['pos', 'bx', 'by', 'lscore', 'rscore', 'time']:
            data[key] = int(data[key])
        return data
    else:
        print(f"[WARNING] Could not parse message: {message}")
        return {}

def handle_client(conn: socket.socket, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    try:
        conn.sendall("Hello from the server!".encode('utf-8'))

        buffer = ""  # store incomplete messages
        while True:
            data = conn.recv(4096)
            if not data:
                break  # client disconnected

            buffer += data.decode('utf-8')

            # Split messages by detecting "PADDLENAME:" prefixes
            while "PADDLENAME:" in buffer:
                # Find start of next message
                start_idx = buffer.find("PADDLENAME:")
                # Find start of next "PADDLENAME:" after current
                next_idx = buffer.find("PADDLENAME:", start_idx + 1)
                if next_idx == -1:
                    # No complete next message yet
                    message = buffer[start_idx:]
                    buffer = message  # keep as incomplete for next recv
                    break
                else:
                    message = buffer[start_idx:next_idx]
                    buffer = buffer[next_idx:]

                # Parse the message
                parsed = parse_game_state(message)
                if parsed:
                    print(f"[{addr}] Parsed message: {parsed}")

                # Optional: echo back
                conn.sendall(f"Server received: {message}".encode('utf-8'))

    except ConnectionResetError:
        pass
    finally:
        conn.close()
        print(f"[DISCONNECTED] from: {addr}")
        if conn in clients:
            clients.remove(conn)

def start_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # allow quick restart
    s.bind((HOST, PORT))
    s.listen()
    print(f"[LISTENING] Server listening on {HOST}:{PORT}")

    try:
        while True:
            conn, addr = s.accept()
            clients.append(conn)
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()
    except KeyboardInterrupt:
        print("\n[SERVER STOPPING]")
    finally:
        print("[CLOSING CLIENTS]")
        for c in clients:
            try:
                c.close()
            except:
                pass
        s.close()
        print("[SERVER CLOSED]")

if __name__ == "__main__":
    HOST = input("Enter server IP address (default 0.0.0.0): ") or "0.0.0.0"
    PORT = int(input("Enter server port number: ") or 50007)
    start_server()
