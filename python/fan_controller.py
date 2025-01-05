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
                
        # Load config file
        self.load_cfg(config_fname)
        self.DEBUG = DEBUG
        
        # Add message topics (self documenting)
        self.topics = dict(fansstate='fanstate', fancontrol='fancontrol', error='error')
        
        # Default state to off
        self.state = False

        # Establish a ZMQ publishing socket
        self._ctx = zmq.Context()
        self.socket = self._ctx.socket(zmq.PUB)
        self.socket.connect(str(self.config.get("server_sub_socket")))
        
        # Establish a ZMQ subscriber socket to listen to command and control from the server
        self.subscriber = self._ctx.socket(zmq.SUB)
        self.subscriber.connect(str(self.config.get("server_sub_socket")))
        
        # Subscribe to get fanstate commands
        self.subscriber.subscribe(self.topics.get('fanstate')) 
        
        # Subscribe to fancontrol commands
        self.subscriber.subscribe(self.topics.get('fancontrol'))
                
        # Provision for a debug mode where we provide fake temperature data
        if not DEBUG:
            import RPi.GPIO as GPIO

            # Set the relay pin per the spec sheet of the relay hat and the wiring spec
            self.relay_pin = self.config.relay_pin
            # Set up the GPIO fan control pin
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.relay_pin, GPIO.OUT)

            # Set initial state to OFF
            self.set_OFF()
        else:
            # If in debug mode, don't invoke the actual relays. Handle in ON/OFF calls
            self.set_OFF()
        
        

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
            pass
            
            time.sleep(self.config.update_rate)
            
    def parse_message(self):
        pass
    
    def set_ON(self) -> int:
        """Set the relay GPIO to high, thereby turning the fan circuit ON

        Returns:
            int: Status
        """
        status = 1
        
        try:
            # Set the fan state via GPIO
            GPIO.output(self.relay_pin, GPIO.HIGH) 
            
            # Update the state tracker   
            state = self.get_GPIO_state()
            
            # Potentially add error checking here
                                    
            # Log event
            logging.info("FANCONTROL: Fan turned ON")
            
            # Send ack message to server
            msg = self.add_topic(self.topics.get('fanstate'), str(state))
            self.publisher.send_string(msg)
            logger.info("FANCONTROL: Sent state to server")
            
        except:
            
            # If we are in debug mode, the above wont work so go here.
            if self.DEBUG:
                logging.info("FANCONTROL DEBUG MODE: Fan turned ON")
                
                # Set the state variable without actually turning on the relay/fan assembly
                self.state = True
                
            # If we are not in debug mode but we get here, it is an error
            else:
                logger.warning("FANCONTROL: Unable to turn fan ON.")
                status = -100
                
                # Send the current state with an error message
                msg = self.add_topic(self.topics.get('error'), str(self.get_GPIO_state()))
                self.publisher.send_string(msg)
                logger.info("FANCONTROL: Sent error message and current state to server")
                
        return status
                

    def set_OFF(self) -> int:
        """Set the relay GPIO to low, thereby turning the fan circuit OFF

        Returns:
            int: Status
        """
        
        status = 1
        
        try:
            # Set the fan state via GPIO
            GPIO.output(self.relay_pin, GPIO.LOW) 
            
            # Update the state tracker   
            state = self.get_GPIO_state()
            
            # Potentially add error checking here
                                    
            # Log event
            logging.info("FANCONTROL: Fan turned OFF")
            
            # Send ack message to server
            msg = self.add_topic(self.topics.get('fanstate'), str(state))
            self.publisher.send_string(msg)
            logger.info("FANCONTROL: Sent state to server")
            
        except:
            
            # If we are in debug mode, the above wont work so go here.
            if self.DEBUG:
                logging.info("FANCONTROL DEBUG MODE: Fan turned OFF")
                
                # Set the state variable without actually turning on the relay/fan assembly
                self.state = False
                
            # If we are not in debug mode but we get here, it is an error
            else:
                logger.warning("FANCONTROL: Unable to turn fan OFF.")
                status = -100
                
                # Send the current state with an error message
                msg = self.add_topic(self.topics.get('error'), str(self.get_GPIO_state()))
                self.publisher.send_string(msg)
                logger.info("FANCONTROL: Sent error message and current state to server")
                
        return status
        
    def get_GPIO_state(self) -> bool:
        """Get the current state of the relay GPIO pin

        Returns:
            bool: Return the state of the GPIO pin
        """
        self.state = GPIO.input(self.relay_pin)

        return self.state

    
    
class fake_GPIO():
    def __init__(self):
        pass
    def get_temperature(self) -> float:
        return rnd.randint(10,40)


if __name__ == "__main__":

    # DEBUG Mode
    DEBUG = True

