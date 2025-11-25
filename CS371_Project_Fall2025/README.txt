Contact Info
============

Group Members & Email Addresses:

    Daniel Krutsick, djkr228@uky.edu
    Jacob Blankenship, jrbl245@uky.edu

Versioning
==========

Github Link: https://github.com/PixelatedLatte/CS371PongProject

General Info
============
# How to install and run
1. Extract the files from the zip file
2. Have one person run the pongServer.py on their computer and use the terminal command 'ipconfig' to find your IPv4 address on the current Network you
are connected to
3. The server code should input that IPv4 address and then input a port number, by default it is "50007", but if you want to pick a different port number,
pick a number that is either the previous number or higher than that number. We have found that this works the best
4. After inputting the server's HOST and PORT number into the prompts, the other two people should run the pongClient.py on their computers and type in
the same HOST and PORT numbers into their input boxes
5. After both clients connect, you can now play pong over the connection to the host server!!!


Install Instructions
====================

Run the following line to install the required libraries for this project:

`pip3 install -r requirements.txt`

Known Bugs
==========
- If you only have two computers, the 1st user should be the one with the server code running. We have not figured it out, but there are some extreme lag
spikes if you have Player 1 as a client user on another computer as opposed to Player 1 being a client user on the same computer that the server is running
on
- Do not attempt to connect a 3rd player(specator) to the server, it will not go well and both client and server code are not set up to handle this
interaction properly