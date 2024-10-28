#!/usr/bin/env python3


import matplotlib.pyplot as plt
import numpy as np
from numpy import random as rnd
import zmq
import time
import sys

DEBUG = True

class temp_sensor_interface:
    """This is the code that interacts directly with the temperature sensor
    """

    def add_topic(topic:str, message:str):
        """
        Simple function to add a topic to a string to be sent over ZMQ
        """
        separator = '::'
        msg = topic + separator + str(message)

        return msg

    def run():
        """
        Main loop of our temperature sensing driver.
        """

        # Specify how often to publish temperature data
        looptime = 1

        # Create our sensor object with the 1W driver library
        if not DEBUG:
            from w1thermsensor import W1ThermSensor as w1s
            sensor1 = w1s()

        # Establish a ZMQ publishing socket
        context = zmq.Context()
        socket = context.socket(zmq.PUB)
        socket.connect("tcp://127.0.0.1:5556")
        topic = 'temp'

        # Enter forever loop
        while True:
            # Get temperature reading
            if not DEBUG:
                temp_data = sensor1.get_temperature()
            else:
                temp_data = rnd.randint(50,90)

            # Construct a message string to send over ZMQ
            message = add_topic(topic, temp_data)

            # Publish temperature data to all listeners
            print(f"Sending: {message} over ZMQ link")
            socket.send_string(message)

            # Loops are ungoverned, so we have to force a sleep every time or else we will run at 100% computing power
            time.sleep(looptime)

if __name__ == "__main__":

    run()

