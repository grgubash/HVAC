#!/usr/bin/env python3

from w1thermsensor import W1ThermSensor as w1s
import matplotlib.pyplot as plt
import numpy as np
import zmq
import time
import sys


def run():
    """
    Main loop of our temperature sensing driver.
    """

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

        # Publish temperature data
        socket.send(topic, temp_data)
        time.sleep(1)

if __name__ == "__main__":

    run()

