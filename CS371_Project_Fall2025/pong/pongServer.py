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
from time import sleep
import threading
import re
from time import time

REQUIRED_NUM_CLIENTS = 2 #Sets the required number of clients to start the game
clients = [] #The list of clients to ensure we can remove them properly later, holds a tuple of (conn, paddleSide)
running = False #Whether the server is running or not
clientsLock = threading.Lock()#Helps remove race conditions
twoClientsConnected = threading.Event()#Prevents server from running without the threading event flag being set

#Sends the messages to all clients within the server
def broadcast(message):
    with clientsLock:
        bad = []
        for c, side in clients:
            try:
                c.sendall(message)
            except:
                bad.append((c, side))
        for b in bad:
            clients.remove(b)



# Regex to parse each game message
MSG_PATTERN = re.compile(
    r'PN:(?P<name>\w+):PP:(?P<pos>-?\d+):BX:(?P<bx>-?\d+):BY:(?P<by>-?\d+):LS:(?P<lscore>\d+):RS:(?P<rscore>\d+):TM:(?P<time>\d+)'
)
#Parses the game state to then be sent to each client in the server for game state updating
def parse_game_state(message: str):
    match = MSG_PATTERN.match(message)
    if match:
        data1 = match.groupdict()
        # Convert numeric values to int
        for key in ['pos', 'bx', 'by', 'lscore', 'rscore', 'time']:
            data1[key] = int(data1[key])
        # Make a separate copy
        print(f"[DEBUG] Parsed data1: {data1}")
        return data1
    else:
        print(f"[WARNING] Could not parse message: {message}")
        return {}

#The main threaded function for handling each client individually
def handle_client(conn: socket.socket, addr):
    global usercount, running
    buffer = ""

    try:
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break

            chunk = chunk.decode("utf-8")
            buffer += chunk

            # Process all complete messages
            while "\n" in buffer:
                message_line, buffer = buffer.split("\n", 1)
                message_line = message_line.strip()
                if not message_line:
                    continue

                message1 = parse_game_state(message_line)
                if message1:
                    print(f"[{addr}] Parsed message: {message1}")
                    transmit = (
                        f"PN:{message1['name']}:PP:{message1['pos']}:BX:{message1['bx']}:BY:{message1['by']}:"
                        f"LS:{message1['lscore']}:RS:{message1['rscore']}:TM:{message1['time']}\n"
                    ).encode('utf-8')
                    broadcast(transmit)

    except ConnectionResetError:
        pass

    finally:
        with clientsLock:
            clients[:] = [(c, side) for c, side in clients if c != conn]
            print(f"[CLIENT DISCONNECT] The client: {conn} has disconnected from the server!")

        conn.close()
        usercount -= 1

        if usercount <= 1:
            running = False
            twoClientsConnected.clear()
#Starts the server, accepts clients, and starts the game when two clients are connected

def start_server():
    global clients, usercount, running
    running = True
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen()
    s.settimeout(1.0)#For periodically checking for KeyboardInterrupt
    print(f"[LISTENING] Server listening on {HOST}:{PORT}")
    
    # Allows for continuous accepting of clients without blocking any other operations or freezing the server
    def accept_loop():
        global usercount, clients, running
        while running:
            try:
                conn, addr = s.accept()

                with clientsLock:
                    if usercount == 0:
                        paddle_side = "left"
                    elif usercount == 1:
                        paddle_side = "right"
                    else:
                        paddle_side = "spectator"

                    clients.append((conn, paddle_side))
                    usercount += 1
                    print(f"[NEW CONNECTION] {addr} assigned to {paddle_side} paddle. Total clients: {usercount}")

                    if usercount >= REQUIRED_NUM_CLIENTS:
                        twoClientsConnected.set()

                thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
                thread.start()

            except socket.timeout:
                continue
    
    acceptThread = threading.Thread(target=accept_loop, daemon=True)
    acceptThread.start()


    print("[SERVER] Waiting for two clients to connect... Will time out in 180 seconds")
    twoClientsConnected.wait(timeout=180)

    #The server will never run this if it times out, given that the twoClientsConnected flag will never be set
    if twoClientsConnected.is_set():
        print("[SERVER] Two clients connected, starting game.")

        with clientsLock:
            for conn, paddle_side in clients:
                if paddle_side != "spectator":
                    try:
                        conn.sendall(f"START:{paddle_side}\n".encode('utf-8'))
                    except Exception as e:
                        print(f"[ERROR] Failed to send START to {conn}: {e}")

        try:
            while running:
                sleep(0.5)
        except KeyboardInterrupt:
            print("[ClOSING SERVER]: KEYBOARD INTERRUPT EXCEPTION")
            running = False

        finally:
            print("[CLOSING CLIENTS]")
            with clientsLock:
                for client, _ in clients:
                    try:
                        client.close()
                    except:
                        pass

            s.close()
            print("[SERVER CLOSED]")

    else:
        running = False
        for client, _ in clients:
            try:
                client.close()
            except:
                pass
        s.close()
        print("[SERVER CLOSED]")
        return 0

#Runs if this is the main module and not ran with another program and prompts you to enter a HOST and PORT number for the server
#before starting it up
if __name__ == "__main__":
    global usercount
    usercount = 0
    HOST = input("Enter server IP address (default 0.0.0.0): ") or "0.0.0.0"
    PORT = int(input("Enter server port number: ") or 50007)
    start_server()