#!/usr/bin/env python3

from w1thermsensor import W1ThermSensor as w1s
import matplotlib.pyplot as plt
import numpy as np
from numpy import random as rnd
import zmq
import time
import sys

def add_topic(topic, message):
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
    sensor1 = w1s()

    # Establish a ZMQ publishing socket
    port = "5556"

    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind("tcp://*:%s" % port)
    topic = 'temp'

    # Enter forever loop
    while True:

        # Get temperature reading
        temp_data = sensor1.get_temperature()

        # Construct a message string to send over ZMQ
        message = add_topic(topic, temp_data)

        # Publish temperature data to all listeners
        print(f"Sending: {message} over ZMQ link")
        socket.send_string(message)

        # Loops are ungoverned, so we have to force a sleep every time or else we will run at 100% computing power
        time.sleep(looptime)

if __name__ == "__main__":

    run()

