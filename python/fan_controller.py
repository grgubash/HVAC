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
#TODO verify that this needs a debug mode (IT DOES FOR SAFETY AND UNIT TESTING)

# Set up the logger
now = datetime.datetime.now()
parent_dir = os.path.split(os.getcwd())[0]
log_dir = os.path.join(parent_dir, "logs")

# Make a logs directory if it does not exist
if not os.path.isdir(log_dir):
    os.mkdir(log_dir)
    
#TODO Make the logger a fixed size

logname = os.path.join(log_dir, "FANCONTROL-" + now.strftime('%Y-%m-%dT%H-%M-%S') + ('-%02d' % (now.microsecond / 10000)) + ".log")
logging.basicConfig(filename=logname, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S%p', level=logging.INFO)
logger = logging.getLogger('WATCHES-FANCONTROL')

class fan_controller:
    """This is the code that interacts directly with the relay board to control the fan
    """

    def __init__(self, config_fname:str, DEBUG:bool=False):
        """_Construct a watches FAN_CONTROLLER object

        Args:
            config_fname (str): Path to config file
            DEBUG (bool, optional): Set the object to DEBUG mode. Defaults to False.
        """
        self.load_cfg(config_fname)
        
        #TODO Same as tepm sensor

    def load_cfg(self, config_fname:str):
        """ Read the config JSON in as a struct

        Args:
            config_fname (str): Config filepath
        """
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
        Main loop of our fan conttroller driver.
        """

        # Create our sensor object with the 1W driver library
        if not DEBUG:
            pass

        # Enter forever loop
        while True:
            # Get temperature reading
            if not DEBUG:
                # Relay board is plugged in - these might be the same
                pass
            else:
                # Make a fake relay objects
                pass
            
            time.sleep(self.config.update_rate)
            
    def parse_message(self):
        pass


if __name__ == "__main__":

    pass

