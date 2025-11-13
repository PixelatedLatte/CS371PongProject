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

# Use this file to write your server logic
# You will need to support at least two clients
# You will need to keep track of where on the screen (x,y coordinates) each paddle is, the score 
# for each player and where the ball is, and relay that to each client
# I suggest you use the sync variable in pongClient.py to determine how out of sync your two
# clients are and take actions to resync the games
'''
PORT = 50007 # Always keep this port the same between server and clients
'''
clients = []

def broadcast(message, sender):
    for client in clients:
        if client != sender:
            try:#Successfully sent message
                client.sendall(message)
            except:#Send failed, remove client with error
                clients.remove(client)

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    conn.sendall("Hello from the server!".encode('utf-8'))
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            
            print(f"Received from {addr}: {data.decode()}")
            broadcast(f"Server echo: {data.decode()}".encode('utf-8'), conn)

    except ConnectionResetError:
        pass
    finally:
        print(f"[DISCONNECTED] {addr}")
        clients.remove(conn)
        conn.close()

def start_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen()
    print(f"[LISTENING] Server listening on {HOST}:{PORT}")

    while True:
        conn, addr = s.accept()
        clients.append(conn)
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

if __name__ == "__main__":
    HOST = input ("Enter server IP address (default): ")
    PORT = int(input("Enter server port number: "))
    start_server()