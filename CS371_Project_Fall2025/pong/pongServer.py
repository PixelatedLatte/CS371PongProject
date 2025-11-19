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
import re
from time import time

REQUIRED_NUM_CLIENTS = 2
clients = []
userCount = 0
running = True
gameStarted = False
clientsLock = threading.Lock()
twoClientsConnected = threading.Event()

def broadcast(message):
    with clientsLock:
        for c, _ in clients:
            try:
                c.sendall(message)
            except:
                clients.remove((c,_))


# Regex to parse each game message
MSG_PATTERN = re.compile(
    r'PN:(?P<name>\w+):PP:(?P<pos>\d+):BX:(?P<bx>\d+):BY:(?P<by>\d+):LS:(?P<lscore>\d+):RS:(?P<rscore>\d+):TM:(?P<time>\d+)')

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


def handle_client(conn: socket.socket, addr):
    global usercount
    try:
        while True:
            data = conn.recv(4096)
            data = data.decode('utf-8').strip()
            if not data:  # Skip empty messages
                continue
            message1 = parse_game_state(data)
            if message1:
                print(f"[{addr}] Parsed message: {message1}")
                # Broadcast to all clients
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
        if usercount < 1:
            twoClientsConnected.set(False)

def start_server():
    global clients
    global usercount
    global running
    running = True
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen()
    s.settimeout(1.0)#For periodically checking for KeyboardInterrupt
    print(f"[LISTENING] Server listening on {HOST}:{PORT}")
    
     # Allows for continous accepting of clients without blocking any other operations or freezing the server
    def accept_loop():
        global usercount
        global clients
        global running
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
                #Checks for KeyboardInterrupt
                continue
    
    acceptThread = threading.Thread(target=accept_loop, daemon=True)
    acceptThread.start()


    twoClientsConnected.wait()
    print("[SERVER] Two clients connected, starting game.")
    with clientsLock:
        for conn, paddle_side in clients:
            if paddle_side != "spectator":
                try:
                    conn.sendall(f"START:{paddle_side}\n".encode('utf-8'))
                except Exception as e:
                    print(f"[ERROR] Failed to send START to {conn}: {e}")
    try:
        acceptThread.join() # Keeps the main thread alive for catching Keyboard Interrupt
        while running:
            time.pause(0.5)
    except KeyboardInterrupt:
        print("[ClOSING SERVER]: KEYBOARD INTERRUPT EXCEPTION")
        running = False
    finally:
        print("[CLOSING CLIENTS]")
        with clientsLock:
            for client, _ in clients:#Attempts to close all clients in the client list, if they are still there
                try: client.close()
                except: pass
        s.close()
        print("[SERVER CLOSED]")

if __name__ == "__main__":
    global usercount
    usercount = 0
    HOST = input("Enter server IP address (default 0.0.0.0): ") or "0.0.0.0"
    PORT = int(input("Enter server port number: ") or 50007)
    start_server()