# =================================================================================================
# Contributing Authors:	    Jacob Blankenship, Daniel Krutsick
# Email Addresses:          jrbl245@uky.edu, djkr228@uky.edu
# Date:                     11/3/2025
# Purpose:                  The Client member of our Pong game
# Misc:                     <Not Required.  Anything else you might want to include>
# =================================================================================================
import queue
import pygame
import re
from typing import Union

import tkinter as tk
import sys
import threading
import socket
import time

from assets.code.helperCode import *

# The main game loop, called after connecting to the server and getting the required info
# Added msg_queue parameter to receive messages from the server, as our client code caches 
# incoming messages in a queue (see receive_messages function)

# Author:  Initially provided by the instructor, modified by Jacob Blankenship
# Purpose:  Main code to handle the Pong game client side, including movement, drawing, and
#       sending/receiving game state to/from the server.
# Pre:  Expects that there is a valid connection to the server via the client socket,
#       and that msg_queue is being populated with incoming messages from the server,
#       as well as valid screen dimensions and player paddle side.
# Post:  Runs the Pong game until a player wins or the connection is lost, then exits. Game does
#       not return any values, or return to another function.
def playGame(screenWidth:int, screenHeight:int, playerPaddle:str, client:socket.socket, msg_queue:queue.Queue) -> None:
    
    print("The game started!")
    # Pygame inits
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.init()

    # Constants
    WHITE = (255,255,255)
    clock = pygame.time.Clock()
    scoreFont = pygame.font.Font("./assets/fonts/pong-score.ttf", 32)
    winFont = pygame.font.Font("./assets/fonts/visitor.ttf", 48)
    pointSound = pygame.mixer.Sound("./assets/sounds/point.wav")
    bounceSound = pygame.mixer.Sound("./assets/sounds/bounce.wav")

    # Display objects
    screen = pygame.display.set_mode((screenWidth, screenHeight))
    winMessage = pygame.Rect(0,0,0,0)
    topWall = pygame.Rect(-10,0,screenWidth+20, 10)
    bottomWall = pygame.Rect(-10, screenHeight-10, screenWidth+20, 10)
    centerLine = []
    for i in range(0, screenHeight, 10):
        centerLine.append(pygame.Rect((screenWidth/2)-5,i,5,5))

    # Paddle properties and init
    paddleHeight = 50
    paddleWidth = 10
    paddleStartPosY = (screenHeight/2)-(paddleHeight/2)
    leftPaddle = Paddle(pygame.Rect(10,paddleStartPosY, paddleWidth, paddleHeight))
    rightPaddle = Paddle(pygame.Rect(screenWidth-20, paddleStartPosY, paddleWidth, paddleHeight))

    ball = Ball(pygame.Rect(screenWidth/2, screenHeight/2, 5, 5), -5, 0)

    if playerPaddle == "left":
        opponentPaddleObj = rightPaddle
        playerPaddleObj = leftPaddle
    else:
        opponentPaddleObj = leftPaddle
        playerPaddleObj = rightPaddle

    lScore = 0
    rScore = 0

    sync = 0

    # Use the global paddleSide as requested (keeps compatibility with the server/client handshake)
    global paddleSide

    while True:
        # Took out screen.fill((0,0,0)) and moved it as player bars and balls 
        # had white trails that were not leaving the screen
        
        # Getting keypress events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    playerPaddleObj.moving = "down"

                elif event.key == pygame.K_UP:
                    playerPaddleObj.moving = "up"

            elif event.type == pygame.KEYUP:
                playerPaddleObj.moving = ""

        # Create a dictionary to hold the latest messages from each paddle
        latest_messages = {"left": {}, "right": {}}

        # While there are messages in the queue, process them
        while not msg_queue.empty():

            # Add and pop message from queue
            incomingmessage = msg_queue.get_nowait()
            parsed = parse_game_state(incomingmessage)

            # If the message could not be parsed, skip it
            if parsed is None:
                print("[WARNING] Received unparsable message, ignoring.")
                continue

            # Store the latest message from each paddle
            latest_messages[parsed['name']] = parsed

        # Only update if we have messages from both paddles
        if latest_messages['left'] and latest_messages['right']:
            left = latest_messages['left']
            right = latest_messages['right']
                
            # Use the data from the client with the higher timestamp,
            # also update sync variable so that both users stay in sync
            if left['time'] >= right['time']:
                authoritative = left
                if paddleSide == "right":
                    sync = left['time']
            else:
                authoritative = right
                if paddleSide == "left":
                    sync = right['time']

            
            # Update ball position by the user that had the latest timestamp
            ball.rect.x = authoritative['bx']
            ball.rect.y = authoritative['by']
            lScore = authoritative['lscore']
            rScore = authoritative['rscore']

            # Update opponent paddle position
            if playerPaddle == "left":
                opponentPaddleObj.rect.y = right['pos']
            else:
                opponentPaddleObj.rect.y = left['pos']


            #print(f"[SYNC] Left time: {left['time']}, Right time: {right['time']}, "
                #f"Authoritative: {authoritative['name']}")

        # Decided to clear the screen here instead to prevent trails
        screen.fill((0,0,0))

        # Update the player paddle and opponent paddle's location on the screen
        for paddle in [playerPaddleObj, opponentPaddleObj]:
            if paddle.moving == "down":
                if paddle.rect.bottomleft[1] < screenHeight-10:
                    paddle.rect.y += paddle.speed
            elif paddle.moving == "up":
                if paddle.rect.topleft[1] > 10:
                    paddle.rect.y -= paddle.speed

        # If the game is over, display the win message
        # Switched score to 9 to make the game longer
        if lScore > 9 or rScore > 9:
            winText = "Player 1 Wins! " if lScore > 9 else "Player 2 Wins! "
            textSurface = winFont.render(winText, False, WHITE, (0,0,0))
            textRect = textSurface.get_rect()
            textRect.center = (int(screenWidth/2), int(screenHeight/2))
            winMessage = screen.blit(textSurface, textRect)
            
            # Also created a sleep and auto quit after displaying win message
            # So that code can exit properly instead of hanging and rerun sooner
            pygame.display.update()
            time.sleep(3)
            pygame.quit()
            client.close()
            return
        else:

            ball.updatePos()
            
            # If the ball makes it past the edge of the screen, update score, etc.
            if ball.rect.x > screenWidth:
                lScore += 1
                pointSound.play()
                ball.reset(nowGoing="right")
            elif ball.rect.x < 0:
                rScore += 1
                pointSound.play()
                ball.reset(nowGoing="left")
                
            # If the ball hits a paddle (host authoritative)
            if ball.rect.colliderect(playerPaddleObj.rect):
                bounceSound.play()
                ball.hitPaddle(playerPaddleObj.rect.center[1])
            elif ball.rect.colliderect(opponentPaddleObj.rect):
                bounceSound.play()
                ball.hitPaddle(opponentPaddleObj.rect.center[1])
                
            # If the ball hits a wall
            if ball.rect.colliderect(topWall) or ball.rect.colliderect(bottomWall):
                bounceSound.play()
                ball.hitWall()

            pygame.draw.rect(screen, WHITE, ball.rect)

        # Drawing the dotted line in the center
        for i in centerLine:
            pygame.draw.rect(screen, WHITE, i)
        # Drawing the player's new location

        #print("[DRAWING PADDLES]")
        #print("[OPPONENT PADDLE Y]:", playerPaddleObj.rect.y)

        for paddle in [playerPaddleObj, opponentPaddleObj]:
            pygame.draw.rect(screen, WHITE, paddle.rect)
            
        pygame.draw.rect(screen, WHITE, topWall)
        pygame.draw.rect(screen, WHITE, bottomWall)
        
        # New varient of updateScore + pygame.display.update as other varient (commented out) was causing problems
        #scoreRect = updateScore(lScore, rScore, screen, WHITE, scoreFont)
        #pygame.display.update([topWall, bottomWall, ball.rect, leftPaddle.rect, rightPaddle.rect, scoreRect, winMessage])
        
        updateScore(lScore, rScore, screen, WHITE, scoreFont)
        pygame.display.update()

        # Encoding and sending the game state to the server
        # Using a MSG_PATTERN that is compatible with the server's parsing function
        try:
            msg = f"PN:{playerPaddle}:PP:{playerPaddleObj.rect.y}:BX:{ball.rect.x}:BY:{ball.rect.y}:LS:{lScore}:RS:{rScore}:TM:{sync}\n"
            client.sendall(msg.encode('utf-8'))
        except:
            # If the client loses connection to the server, exit the game loop to prevent hanging
            print("Lost connection!")
            pygame.quit()
            client.close()
            return
        
        clock.tick(60)
        sync += 1

        
# Regular expression pattern to parse incoming game state messages
# Parses name, paddle position, ball x/y, left/right score, and sync time
MSG_PATTERN = re.compile(
    r'PN:(?P<name>\w+):PP:(?P<pos>-?\d+):BX:(?P<bx>-?\d+):BY:(?P<by>-?\d+):LS:(?P<lscore>\d+):RS:(?P<rscore>\d+):TM:(?P<time>\d+)')

# Parses the game state message received from the server

# Author:  Created by Jacob Blankenship
# Purpose:  Parses the Pong game state message received from the server.
# Pre:  Expects a string message formatted according to the MSG_PATTERN regex, and that this
#       is called during the PlayGame function, as well as a valid an set up queue to hold
#       incoming messages from the server.
# Post:  Returns a dictionary with the parsed game state values if successful,
#      otherwise returns None if the message could not be parsed.
def parse_game_state(message: str) -> Union[dict, None]:

    # Use regex to parse the message
    match = MSG_PATTERN.match(message)

    # If the message matches the pattern, throw vars into a dict and convert numeric values to int
    if match:
        data = match.groupdict()
        for key in ['pos', 'bx', 'by', 'lscore', 'rscore', 'time']:
            data[key] = int(data[key])
        return data
    # If the message does not match, return None (handled in the playgame function)
    else:
        print(f"[WARNING] Could not parse message: {message}")
        return None

# Thread function to continuously receive messages from the server

# Author:  Created by Jacob Blankenship
# Purpose:  Continuously receives messages from the server and adds them to a queue, threaded
#       to allow the main game loop to run while receiving messages in the background.
# Pre:  Expects a valid socket connection to the server, and a properly set up queue to hold
#       incoming messages. As well as be called during the PlayGame() function.
# Post:  Returns nothing, but continuously adds received messages to the provided queue until
#       the connection is lost or an error occurs. Queue items are split to be individual messages
#       based on newline characters so that each item is an individual game-state.
def receive_messages(sock) -> None:
    # Creates a buffer to hold incomplete messages
    buffer = ""
    while True:
        try:
            # Large amount of bytes to ensure full messages are received
            chunk = sock.recv(4096)
            if not chunk:
                print("[CLIENT] Server disconnected.")
                break
            # decode and add to buffer
            decoded = chunk.decode('utf-8')
            buffer += decoded
            
            # Split by newline to process each send gamestate
            while '\n' in buffer:
                message, buffer = buffer.split('\n', 1)  
                # Only process non-empty messages
                if message.strip():
                    msg_queue.put(message.strip())
        # Break if error
        except Exception as e:
            print("Receive error:", e)
            break

# Author:  Initially created my instructer, heavily modified by Jacob Blankenship
# Purpose:  Connects to the Pong server using the provided IP and port, initially 
#           assigns the player to a paddle side, then starts the game loop.
# Pre:  Expects valid IP address and port strings, as well as a tkinter label and app,
#       IP and port are provided by the user via the tkinter GUI in the startScreen() function.
# Post: Returns nothing, but starts the Pong game client after connecting to the server,
#       can also error out before closing the game.
def joinServer(ip:str, port:str, errorLabel:tk.Label, app:tk.Tk) -> None:

    # Purpose:      This method is fired when the join button is clicked
    # Arguments:
    # ip            A string holding the IP address of the server
    # port          A string holding the port the server is using
    # errorLabel    A tk label widget, modify it's text to display messages to the user (example below)
    # app           The tk window object, needed to kill the window
    
    print("Connecting to server at", ip, "on port", port)
    try:
        # Create and connect the socket of new client
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((ip, int(port)))  

        # Receive message from server continuously
        global msg_queue
        msg_queue = queue.Queue()

        # Create a thread for each client to receive messages and add them to the queue
        # deamon thread to make sure the thread closes when the main program exits
        receiver_thread = threading.Thread(target=receive_messages, args=(client,), daemon=True)
        receiver_thread.start()

        errorLabel.config(text=f"Connected successfully to {ip}:{port}")
        errorLabel.update()

        print("Waiting for other player to connect...")
        startMsg = msg_queue.get().strip()

        # Initial message from server should be START:<paddleSide> to assign user to paddle side
        # Cant be in regular loop as we need paddle side before starting game
        if "START" in startMsg:
            global paddleSide
            paddleSide = startMsg.split(":")[1]
            print("Starting game, Opponent Connected!")
        else:
            print(f"Unexpected message from server: {startMsg}")
            print(f"Closing game, something went wrong.")
            return
        
        # Close the tkinter window and start the game
        app.withdraw()
        print(f"Starting game as {paddleSide} paddle.")
        if paddleSide == "left" or paddleSide == "right":
            playGame(640, 480, paddleSide, client, msg_queue)
        else:
            #There was a problem with the name of paddleSide sent and extracted
            print(f"Unexpect Paddle side, disconnecting.")
            return
        print("Game Ended, closing client.")
        app.quit()
    except Exception as e:
        errorLabel.config(text=f"Connection failed: {e}")
        errorLabel.update()

    # Get the required information from your server (screen width, height & player paddle, "left or "right)
    
    # If you have messages you'd like to show the user use the errorLabel widget like so
    errorLabel.config(text=f"Some update text. You input: IP: {ip}, Port: {port}")
    # You may or may not need to call this, depending on how many times you update the label
    errorLabel.update()     

# This displays the opening screen, you don't need to edit this (but may if you like)

# Author:  Created by Instructor
# Purpose:  Displays the starting tkinter GUI to get server IP and port from user,
#           then calls joinServer() when the user clicks the Join button.
# Pre:  Expects no parameters, called when the pongClient.py file is run directly through the
#       main function.
# Post: Returns nothing, but starts the tkinter GUI for user input, then calls joinServer()
#       to connect to the server and start the game. Does display an error label to display
#       connection status messages to the user.
def startScreen() -> None: 
    print("Starting Pong Client...")
    app = tk.Tk()
    app.title("Server Info")

    image = tk.PhotoImage(file="./assets/images/logo.png")

    titleLabel = tk.Label(image=image)
    titleLabel.grid(column=0, row=0, columnspan=2)

    ipLabel = tk.Label(text="Server IP:")
    ipLabel.grid(column=0, row=1, sticky="W", padx=8)

    ipEntry = tk.Entry(app)
    ipEntry.grid(column=1, row=1)

    portLabel = tk.Label(text="Server Port:")
    portLabel.grid(column=0, row=2, sticky="W", padx=8)

    portEntry = tk.Entry(app)
    portEntry.grid(column=1, row=2)

    errorLabel = tk.Label(text="")
    errorLabel.grid(column=0, row=4, columnspan=2)

    joinButton = tk.Button(text="Join", command=lambda: joinServer(ipEntry.get(), portEntry.get(), errorLabel, app))
    joinButton.grid(column=0, row=3, columnspan=2)

    app.mainloop()

if __name__ == "__main__":
    startScreen()
