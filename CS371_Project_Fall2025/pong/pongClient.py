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

import tkinter as tk
import sys
import threading
import socket
import time

from assets.code.helperCode import *

# This is the main game loop.  For the most part, you will not need to modify this.  The sections
# where you should add to the code are marked.  Feel free to change any part of this project
# to suit your needs.
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

    # Determine authority: host simulates the ball
    global isHost
    isHost = (playerPaddle == "left")

    while True:
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

        # =========================================================================================
        # PROCESS NETWORK UPDATES *BEFORE* DRAWING ANYTHING
        # This prevents old paddle/ball pixels from being left on the screen
        # =========================================================================================
            # drain the queue and apply the most recent state(s)
        print("[CHECKING QUEUE]")
        print("[QUEUE SIZE]:", msg_queue.qsize())
        while not msg_queue.empty():
            incoming = msg_queue.get_nowait()
            print("[QUEUE RECEIVED]:", incoming)
            parsed = parse_game_state(incoming)
            #if parsedL:
            # update opponent paddle based on what server told us
            if parsed is None:
                print("[WARNING] Received unparsable message, ignoring.")
                continue

            opponentPaddleObj.rect.y = int(parsed['pos'])
            opponentSync = int(parsed['time'])
            print("[OPPONENT TICK]:", opponentSync)
            print("[User TICK]:", sync)
            # Only non-host clients should adopt the authoritative ball position
            if not isHost and parsed is not None:
                # apply authoritative ball + scores from network
                ball.rect.x = int(parsed.get('bx', ball.rect.x))
                ball.rect.y = int(parsed.get('by', ball.rect.y))
                lScore = int(parsed.get('lscore', lScore))
                rScore = int(parsed.get('rscore', rScore))

        # Now clear the screen (must happen AFTER network updates)
        screen.fill((0,0,0))

        # Update the player paddle and opponent paddle's location on the screen
        if playerPaddleObj.moving == "down" and playerPaddleObj.rect.bottom < screenHeight - 10:
            playerPaddleObj.rect.y += playerPaddleObj.speed
        elif playerPaddleObj.moving == "up" and playerPaddleObj.rect.top > 10:
            playerPaddleObj.rect.y -= playerPaddleObj.speed

        # If the game is over, display the win message
        if lScore > 4 or rScore > 4:
            winText = "Player 1 Wins! " if lScore > 4 else "Player 2 Wins! "
            textSurface = winFont.render(winText, False, WHITE, (0,0,0))
            textRect = textSurface.get_rect()
            textRect.center = (int(screenWidth/2), int(screenHeight/2))
            winMessage = screen.blit(textSurface, textRect)
            pygame.display.update()
            time.sleep(3)
            pygame.quit()
            client.close()
            return
        else:

            # ==== Ball Logic =====================================================================
            # Only the host runs the physics and collision logic.
            # Clients will receive the authoritative ball position from the server and must NOT call updatePos.
            if isHost:
                ball.updatePos()

                # If the ball makes it past the edge of the screen, update score, etc.
                if ball.rect.x > screenWidth:
                    lScore += 1
                    pointSound.play()
                    ball.reset(nowGoing="left")
                elif ball.rect.x < 0:
                    rScore += 1
                    pointSound.play()
                    ball.reset(nowGoing="right")
                    
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
            # Clients do NOT call ball.updatePos(); they just draw ball at last received coordinates
            pygame.draw.rect(screen, WHITE, ball.rect)
            # ==== End Ball Logic =================================================================

        # Drawing the dotted line in the center
        for i in centerLine:
            pygame.draw.rect(screen, WHITE, i)
        # Drawing the player's new location
        print("[DRAWING PADDLES]")
        print("[OPPONENT PADDLE Y]:", playerPaddleObj.rect.y)

        for paddle in [playerPaddleObj, opponentPaddleObj]:
            pygame.draw.rect(screen, WHITE, paddle.rect)
            
        pygame.draw.rect(screen, WHITE, topWall)
        pygame.draw.rect(screen, WHITE, bottomWall)
        scoreRect = updateScore(lScore, rScore, screen, WHITE, scoreFont)

        # =========================================================================================
        # Now send our update to the server (after the host has updated the ball so it sends authoritative coords)
        try:
            msg = f"PN:{playerPaddle}:PP:{playerPaddleObj.rect.y}:BX:{ball.rect.x}:BY:{ball.rect.y}:LS:{lScore}:RS:{rScore}:TM:{sync}\n"
            client.sendall(msg.encode('utf-8'))
        except:
            print("Lost connection!")
            pygame.quit()
            client.close()
            return
        # =========================================================================================

        pygame.display.update()
        clock.tick(60)

        # This number should be synchronized between you and your opponent.  If your number is larger
        # then you are ahead of them in time, if theirs is larger, they are ahead of you, and you need to
        # catch up (use their info)
        sync += 1

        

MSG_PATTERN = re.compile(
    r'PN:(?P<name>\w+):PP:(?P<pos>\d+):BX:(?P<bx>\d+):BY:(?P<by>\d+):LS:(?P<lscore>\d+):RS:(?P<rscore>\d+):TM:(?P<time>\d+)')

def parse_game_state(message: str):
    match = MSG_PATTERN.match(message)
    if match:
        data = match.groupdict()
        # Convert numeric values to int
        for key in ['pos', 'bx', 'by', 'lscore', 'rscore', 'time']:
            data[key] = int(data[key])
        
        print(f"[DEBUG] Parsed data: {data}")
        
        # Create separate objects for left and right paddle data
        # The 'name' field tells us which paddle this data is about
        if paddleSide == "right":
            Data = {
                'pos': data['pos'] if data['name'] == 'left' else 0,
                'bx': data['bx'],
                'by': data['by'],
                'lscore': data['lscore'],
                'rscore': data['rscore'],
                'time': data['time']}
        elif paddleSide == "left":
            Data = {
                'pos': data['pos'] if data['name'] == 'right' else 0,
                'bx': data['bx'],
                'by': data['by'],
                'lscore': data['lscore'],
                'rscore': data['rscore'],
                'time': data['time']}
        else:
            print(f"[WARNING] Unknown paddle side: {paddleSide}")
            return None
        return Data
    else:
        print(f"[WARNING] Could not parse message: {message}")
        return None

def receive_messages(sock):
    buffer = ""

    while True:
        try:
            chunk = sock.recv(4096)

            if not chunk:
                print("[CLIENT] Server disconnected.")
                break
            decoded = chunk.decode('utf-8')
            print(f"[RECEIVED CHUNK]: {decoded}")
            buffer += decoded  # Add to buffer
            
            # Split by newline and process complete messages
            while '\n' in buffer:
                message, buffer = buffer.split('\n', 1)  # Get first complete message
                if message.strip():  # Only process non-empty messages
                    msg_queue.put(message.strip())
                    print(f"[QUEUED MESSAGE]: {message.strip()}")
        except Exception as e:
            print("Receive error:", e)
            break

# This is where you will connect to the server to get the info required to call the game loop.  Mainly
# the screen width, height and player paddle (either "left" or "right")
# If you want to hard code the screen's dimensions into the code, that's fine, but you will need to know
# which client is which
def joinServer(ip:str, port:str, errorLabel:tk.Label, app:tk.Tk) -> None:

    # Purpose:      This method is fired when the join button is clicked
    # Arguments:
    # ip            A string holding the IP address of the server
    # port          A string holding the port the server is using
    # errorLabel    A tk label widget, modify it's text to display messages to the user (example below)
    # app           The tk window object, needed to kill the window
    
    # Create a socket and connect to the server
    # You don't have to use SOCK_STREAM, use what you think is best
    print("Connecting to server at", ip, "on port", port)
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((ip, int(port)))  # Client connects only

        # Receive message from server continuously
        global msg_queue
        msg_queue = queue.Queue()
        # Start the receiver thread properly
        # Update UI
        receiver_thread = threading.Thread(target=receive_messages, args=(client,), daemon=True)
        receiver_thread.start()

        errorLabel.config(text=f"Connected successfully to {ip}:{port}")
        errorLabel.update()

        print("Waiting for other player to connect...")
        startMsg = msg_queue.get().strip()
        if "START" in startMsg:# Finds that START has been sent over by the server and then extracts the paddle side given their player number
            global paddleSide
            paddleSide = startMsg.split(":")[1]
            print("Starting game, Opponent Connected!")
        else:
            print(f"Unexpected message from server: {startMsg}")
            print(f"Closing game, something went wrong.")
            return

        app.withdraw()
        print(f"Starting game as {paddleSide} paddle.")
        if paddleSide == "left" or paddleSide == "right":
            playGame(640, 480, paddleSide, client, msg_queue)
        else:#There was a problem with the name of paddleSide sent and extracted
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

    #Close this window and start the game with the info passed to you from the server
    # app.withdraw()     # Hides the window (we'll kill it later)
    # playGame(screenWidth, screenHeight, ("left"|"right"), client)  # User will be either left or right paddle
    # app.quit()         # Kills the window


# This displays the opening screen, you don't need to edit this (but may if you like)
def startScreen():
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
    
    # Uncomment the line below if you want to play the game without a server to see how it should work
    # the startScreen() function should call playGame with the arguments given to it by the server this is
    # here for demo purposes only
    #playGame(640, 480,"left",socket.socket(socket.AF_INET, socket.SOCK_STREAM))
