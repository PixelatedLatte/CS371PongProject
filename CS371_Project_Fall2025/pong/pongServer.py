# =================================================================================================
# Contributing Authors:	    Jacob Blankenship, Daniel Krutsick
# Email Addresses:          jrbl245@uky.edu, djkr228@uky.edu
# Date:                     11/24/2025
# Purpose:                  The Server member of our Pong game
# Misc:                     To run the pongServer.py file directly run "python pongServer.py",
#                           ensure the port you choose is open and not blocked by firewall and
#                           that the server is running before any clients attempt to connect.
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

REQUIRED_NUM_CLIENTS = 2 #Sets the required number of clients to start the game
clients = [] #The list of clients to ensure we can remove them properly later, holds a tuple of (conn, paddleSide)
running = False #Whether the server is running or not
clientsLock = threading.Lock()#Helps remove race conditions
twoClientsConnected = threading.Event()#Prevents server from running without the threading event flag being set
#Sends the messages to all clients within the server
def broadcast(message) -> None:
    with clientsLock:
        for c, _ in clients:
            try:
                c.sendall(message)
            except:
                pass
# Regex to parse each game message
MSG_PATTERN = re.compile(
    r'PN:(?P<name>\w+):PP:(?P<pos>-?\d+):BX:(?P<bx>-?\d+):BY:(?P<by>-?\d+):LS:(?P<lscore>\d+):RS:(?P<rscore>\d+):TM:(?P<time>\d+)'
)
#Parses the game state to then be sent to each client in the server for game state updating

# Author:  Created by Jacob Blankenship
# Purpose:  Parses the Pong game state message received from the client(s).
# Pre:  Expects a string message formatted according to the MSG_PATTERN regex, and that this
#       is called during the handleclient() function.
# Post:  Returns a dictionary with the parsed game state values if successful,
#      otherwise returns an empty dict if the message could not be parsed.
def parse_game_state(message: str) -> dict:
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
def handle_client(conn: socket.socket, addr) -> None:
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
        #Finally ends a handle_client thread by removing its instance of itself in the list and then closing and reducing the number
        #of clients in the usercount variable by 1, this would be useful if we had more time to implement a way of continuously playing more
        #games after finishing one and also handling spectator clients
        with clientsLock:
            #This finds the one client in the client list and removes it from the list of tuples
            clients[:] = [(c, side) for c, side in clients if c != conn]
            print(f"[CLIENT DISCONNECT] The client: {conn} has disconnected from the server!")
        conn.close()
        usercount -= 1
        if usercount <= 1:
            running = False
#Starts the server, accepts clients, and starts the game when two clients are connected
def start_server() -> int:
    global clients, usercount, running
    running = True
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen()
    s.settimeout(1.0)#For periodically checking for KeyboardInterrupt
    print(f"[LISTENING] Server listening on {HOST}:{PORT}")
    # Allows for continous accepting of clients without blocking any other operations or freezing the server
    # This would be a more helpful definition given we were also account spectators properly, but there is no way of doing a spectator
    # given the time we had to complete the project.
    def accept_loop():
        global usercount, clients, running
        while running:
            try:
                # Try to accept each client that attempts to connect
                conn, addr = s.accept()
                # clientsLock is used here to ensure that if two clients are connecting at the same time, there is no possible
                # way that both clients will connect with the same paddle since the clients will not be able to finalize a connection
                # until one is done initializing itself
                with clientsLock:
                    if usercount == 0:
                        paddle_side = "left"
                    elif usercount == 1:
                        paddle_side = "right"
                    else:
                        paddle_side = "spectator"
                    # Adds the connection and paddle_side as a tuple into the clients list
                    clients.append((conn, paddle_side))
                    usercount += 1
                    print(f"[NEW CONNECTION] {addr} assigned to {paddle_side} paddle. Total clients: {usercount}")
                    if usercount >= REQUIRED_NUM_CLIENTS:# Sets the twoClientsConnected flag to true, indicating there are two clients connected
                        twoClientsConnected.set()
                #Starts a thread for handle_client, will not send any messages out given there will be no messages coming into the server yet
                #Game has not started
                thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
                thread.start()
            except socket.timeout:# Keep running even if timed out, do not want to stop accepting clients
                continue   
    acceptThread = threading.Thread(target=accept_loop, daemon=True)
    acceptThread.start()
    #The server is waiting for the two users to finally join the server
    print("[SERVER] Waiting for two clients to connect... Will time out in 180 seconds")
    twoClientsConnected.wait(timeout=180)
    #The server will never run this if it times out, given that the twoClientsConnected flag will never be set
    if twoClientsConnected.is_set():
        print("[SERVER] Two clients connected, starting game.")
        #Clients lock here ensures that we send all paddle_sides out to their respective clients properly and just in general
        #is a good practice for handling the clients properly
        with clientsLock:
            for conn, paddle_side in clients:
                if paddle_side != "spectator":
                    try:
                        conn.sendall(f"START:{paddle_side}\n".encode('utf-8'))
                    except Exception as e:
                        print(f"[ERROR] Failed to send START to {conn}: {e}")
        #We should continue waiting 0.5 seconds to ensure the server can detect a KeyboardInterrupt and close the server
        #forcefully if need be
        try:
            while running:
                sleep(0.5)
        except KeyboardInterrupt:#Detects if ctrl+c has been clicked and will turn running to False, which then leads to finally
            print("[ClOSING SERVER]: KEYBOARD INTERRUPT EXCEPTION")
            running = False
        finally:#This will finally close down the server after removing each clients connection from the list and closing their connections
            print("[CLOSING CLIENTS]")
            running = False
            with clientsLock:#Attempts to close all clients in the client list, if they are still there
                for client, _ in clients:
                    try:
                        client.close()
                    except:
                        pass
            print("[SERVER CLOSED]")
            s.close()
            return 0
    else:#This is played if the server times out, since there would be no way to get to the finally clause inside of the if statement if timeout occurs
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