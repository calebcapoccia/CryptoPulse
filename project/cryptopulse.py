# This is the main program that runs the subcomponents of CryptoPulse by using Python threading. I borrowed code from https://www.geeksforgeeks.org/multithreading-python-set-1/
# to figure out how to run threads and https://stackoverflow.com/questions/1489669/how-to-exit-the-entire-application-from-a-python-thread to figure out how to quit threads.
from backend import main
from app import app
from threading import Thread
import os

# This function ends the program when the user enters "q" for quit
def quit():
    x = ""
    while "q" not in x:
        x = input("")
    os._exit(1)

# Create the threads for the different components of CryptoPulse, along with the ability to quit
t1 = Thread(target=app.run)
t2 = Thread(target=main)
t3 = Thread(target=quit)

# Start the threads
t1.start()
t2.start()
t3.start()

# Wait for the current programs to finish running before moving on. Because main in backend.py has a forever loop, the program will only end when the user
# enters q to quit.
t1.join()
t2.join()
t3.join()
