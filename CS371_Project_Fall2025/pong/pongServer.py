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
    r'PN:(?P<name>\w+):PP:(?P<pos>\d+):BX:(?P<bx>\d+):BY:(?P<by>\d+):LS:(?P<lscore>\d+):RS:(?P<rscore>\d+):TM:(?P<time>\d+)')

def parse_game_state(message: str):
    match = MSG_PATTERN.match(message)
    if match:
        data1 = match.groupdict()
        # Convert numeric values to int
        for key in ['pos', 'bx', 'by', 'lscore', 'rscore', 'time']:
            data1[key] = int(data1[key])
        # Make a separate copy
        data2 = data1.copy()
        print(f"[DEBUG] Parsed data1: {data1}")
        print(f"[DEBUG] Parsed data2: {data2}")
        return data1, data2
    else:
        print(f"[WARNING] Could not parse message: {message}")
        return {}, {}


def handle_client(conn: socket.socket, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    try:
        conn.sendall("Hello from the server!".encode('utf-8'))
        while True:
            data = conn.recv(4096)
            if not data:
                break
            data = data.decode('utf-8')
            message1,message2 = parse_game_state(data)
            if message1:
                print(f"[{addr}] Parsed message: {message1}")
                # Optional: echo back or broadcast
                conn.sendall((f"PN:{message1['name']}:PP:{message1['pos']}:BX:{message1['bx']}:BY:{message1['by']}:"
                            f"LS:{message1['lscore']}:RS:{message1['rscore']}:TM:{message1['time']}\n").encode('utf-8'))
                conn.sendall((f"PN:{message2['name']}:PP:{message2['pos']}:BX:{message2['bx']}:BY:{message2['by']}:"
                            f"LS:{message2['lscore']}:RS:{message2['rscore']}:TM:{message2['time']}\n").encode('utf-8'))
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
