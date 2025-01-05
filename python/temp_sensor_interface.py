#!/usr/bin/env python3


import numpy as np
from numpy import random as rnd
import zmq
import time, datetime
import sys, os
import logging
import json

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

    def __init__(self, config_fname:str, DEBUG:bool=False) -> None:
        """_Construct a watches SENSOR object

        Args:
            config_fname (str): Path to config file
            DEBUG (bool, optional): Set the object to DEBUG mode. Defaults to False.
        """
        
        # Load config file
        self.load_cfg(config_fname)

        # Establish a ZMQ publishing socket
        self._ctx = zmq.Context()
        self.socket = self._ctx.socket(zmq.PUB)
        
        # Publish to the socket that the server is listening on
        self.socket.connect(str(self.config.get("server_sub_socket")))
        
        # Provision for a debug mode where we provide fake temperature data
        if not DEBUG:
            from w1thermsensor import W1ThermSensor as w1s
            self.sensor1 = w1s()
        else:
            self.sensor1 = fake_sensor()
        
        # Add message topic
        self.topics = dict(temp='temp')

    def load_cfg(self, config_fname:str) -> None:
        """ Read the config JSON in as a struct

        Args:
            config_fname (str): Config filepath
        """
        with open(config_fname) as f:
            cfg_file = json.load(f)
            
        self.config = cfg_file.get("config") 

    def add_topic(self, topic:str, message:str) -> str:
        """Simple function to add a topic to a string to be sent over ZMQ

        Args:
            topic (str): ZMQ Topic for this message
            message (str): Message contents

        Returns:
            str: Packed message
        """
        separator = '::'
        msg = topic + separator + str(message)

        return msg
    
    def c_to_f(self, data:float) -> float:
        """ Celsius to fahrenheit conversion

        Args:
            data (float): Data in Celsius units

        Returns:
            float: Data in Fahrenheit units
        """
        f = data*9/5+32
        return f

    def run(self):
        """
        Main loop of our temperature sensing driver.
        """

        # Enter forever loop
        while True:
            # Get temperature reading
            temp_data = self.c_to_f(self.sensor1.get_temperature())

            # Construct a message string to send over ZMQ
            message = self.add_topic(self.topics.get('temp'), temp_data)

            # Publish temperature data to all listeners
            print(f"Sending: {message} over ZMQ link")
            self.socket.send_string(message)
            
            # Log the temperature reading
            logger.info("SENSOR READING: %s", str(temp_data))

            # Loops are ungoverned, so we have to force a sleep every time or else we will run at 100% computing power
            time.sleep(self.config.get("update_rate"))
            
class fake_sensor():
    
    def __init__(self):
        pass
    def get_temperature(self) -> float:
        return rnd.randint(10,40)

if __name__ == "__main__":
    
    # Debug mode
    DEBUG = True

    # Specify configuration file
    cfg = os.path.join(parent_dir, "cfg", "watches_cfg.json")
    
    # Create a digital sensor object to mirror our physical one
    sensor = temp_sensor_interface(cfg, DEBUG)
    
    # Run the sensor
    sensor.run()