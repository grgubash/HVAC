#!/usr/bin/env python3

import numpy as np
from numpy import random as rnd
import zmq
import time
from datetime import datetime as dt
import sys, os
import logging
import logging.handlers
import json

#DONE

# Set up the logger
now = dt.now()
parent_dir = os.path.split(os.getcwd())[0]
log_dir = os.path.join(parent_dir, "logs")

# Make a logs directory if it does not exist
if not os.path.isdir(log_dir):
    os.mkdir(log_dir)
    
logname = os.path.join(log_dir, "SENSOR-" + now.strftime('%Y-%m-%dT%H-%M-%S') + ('-%02d' % (now.microsecond / 10000)) + ".log")

rfh = logging.handlers.RotatingFileHandler(filename=logname, 
    mode='a',
    maxBytes=5*1024*1024,
    backupCount=1,
    encoding=None,
    delay=0,
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S%p', 
                    level=logging.INFO,
                    handlers=[rfh])

logger = logging.getLogger('WATCHES-SENSOR')

class temp_sensor_interface:
    """This is the code that interacts directly with the temperature sensor
    """

    def __init__(self, config_fname:str) -> None:
        """_Construct a watches SENSOR object

        Args:
            config_fname (str): Path to config file
        """
        
        # Load config file
        self.load_cfg(config_fname)
        
        # Contingency for unable to read sensor
        self.last_reading = 0

        # Establish a ZMQ publishing socket
        self._ctx = zmq.Context()
        self.publisher = self._ctx.socket(zmq.PUB)
        
        # Publish to the socket that the server is listening on
        self.publisher.connect(str(self.config.get("server_sub_socket")))
        
        # Provision for a debug mode where we provide fake temperature data
        if not self.config.get("sensor_debug"):
            from w1thermsensor import W1ThermSensor as w1s
            self.sensor1 = w1s()
        else:
            logger.info("Sensor started in Debug mode")
            self.sensor1 = fake_sensor(self.config.get("enable_temp_override"),
                                       self.config.get("override_temp_c"))
        
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
        msg = topic + separator + str(message)  + "::" + dt.now().strftime("%H:%M:%S")

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
        
        logger.info("Entering run loop")

        # Enter forever loop
        while True:
            # Get temperature reading and convert to F
            try: 
                temp_data = self.c_to_f(self.sensor1.get_temperature())
                self.last_reading = temp_data
            except Exception as e:
                temp_data = self.last_reading
                logger.warning(f"Sensor error {e}, reporting last sensor reading")

            # Construct a message string to send over ZMQ
            message = self.add_topic(self.topics.get('temp'), temp_data)

            # Publish temperature data to all listeners
            self.publisher.send_string(message)
            
            # Log the temperature reading
            logger.info(f"Sensor Reading: {temp_data}")

            # Loops are ungoverned, so we have to force a sleep every time or else we will run at 100% computing power
            time.sleep(self.config.get("temp_update_rate"))
            
    def exit(self):
        """Gracefully shutdown zmq ports and exit the program
        """
        logger.info("Gracefully exiting")
        self.publisher.close()
        self._ctx.term()
        print("\nshutdown")
        sys.exit(0)
            
class fake_sensor():
    """Lets use this to plot a sin wave to demonstrate the plot function of the server. 
        Over 24 hours (86400), want a couple periods with amplitude of 20, centered at 55d c
    """

    def __init__(self, override, override_temp):
        self.override = override
        self.override_temp = override_temp
        self.ctr = 0
        self.f = 25/(60*60*24) # Want it to be discontinuous a bit
        
    def get_temperature(self) -> float:
        if self.override:
            return self.override_temp
        else:
            value = 30*np.sin(2 * np.pi * self.f * self.ctr) + 40
            self.ctr += 1
            return value        

if __name__ == "__main__":

    # Specify configuration file
    cfg = os.path.join(parent_dir, "cfg", "watches_cfg.json")
    
    # Create a digital sensor object to mirror our physical one
    sensor = temp_sensor_interface(cfg)
    
    # Run the sensor
    try:
        sensor.run()
    except KeyboardInterrupt:
        logger.info("Got shutdown signal")
        sensor.exit()
