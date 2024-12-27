#!/usr/bin/env python3


import matplotlib.pyplot as plt
import numpy as np
from numpy import random as rnd
import zmq
import time, datetime
import sys, os
import logging
import json

DEBUG = True

# Set up the logger
now = datetime.datetime.now()
parent_dir = os.path.split(os.getcwd())[0]
log_dir = os.path.join(parent_dir, "logs")

# Make a logs directory if it does not exist
if not os.path.isdir(log_dir):
    os.mkdir(log_dir)

logname = os.path.join(log_dir, "SENSOR-" + now.strftime('%Y-%m-%dT%H-%M-%S') + ('-%02d' % (now.microsecond / 10000)) + ".log")
logging.basicConfig(filename=logname, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S%p', level=logging.INFO)
logger = logging.getLogger('WATCHES-SENSOR')

class temp_sensor_interface:
    """This is the code that interacts directly with the temperature sensor
    """

    def __init__(self, config_fname:str, DEBUG:bool=False):


    def load_cfg(self, config_fname:str):
        with open(config_fname) as f:
            cfg_file = json.load(f)
            
        self.config = cfg_file.get("config") 

    def add_topic(self, topic:str, message:str):
        """
        Simple function to add a topic to a string to be sent over ZMQ
        """
        separator = '::'
        msg = topic + separator + str(message)

        return msg

    def run(self):
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
            message = self.add_topic(topic, temp_data)

            # Publish temperature data to all listeners
            print(f"Sending: {message} over ZMQ link")
            socket.send_string(message)

            # Loops are ungoverned, so we have to force a sleep every time or else we will run at 100% computing power
            time.sleep(looptime)

if __name__ == "__main__":

    run()

