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

# TODO: Add proper state setting

# Set up the logger
now = dt.now()
parent_dir = os.path.split(os.getcwd())[0]
log_dir = os.path.join(parent_dir, "logs")

# Make a logs directory if it does not exist
if not os.path.isdir(log_dir):
    os.mkdir(log_dir)
    
logname = os.path.join(log_dir, "FANCONTROL-" + now.strftime('%Y-%m-%dT%H-%M-%S') + ('-%02d' % (now.microsecond / 10000)) + ".log")

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

logger = logging.getLogger('WATCHES-FANCONTROL')

class fan_controller:
    """This is the code that interacts directly with the relay board to control the fan
    """

    def __init__(self, config_fname:str):
        """_Construct a watches FAN_CONTROLLER object

        Args:
            config_fname (str): Path to config file
        """
                
        # Load config file
        self.load_cfg(config_fname)
        
        # Add message topics (self documenting)
        self.topics = dict(fanstate='fanstate', fancontrol='fancontrol', error='error')
        self.requests = dict(getstate="getstate", turnon="turnon", turnoff="turnoff")
        self.states = dict(on="on", off="off", error="error")
        
        # Default state to off
        self.state = self.states.get("off")

        # Establish a ZMQ publishing socket
        self._ctx = zmq.Context()
        self.publisher = self._ctx.socket(zmq.PUB)
        
        # Publish to the socket that the server is listening on
        self.publisher.connect(str(self.config.get("server_sub_socket")))
        
        # Establish a ZMQ subscriber socket to listen to command and control from the server
        # Subscribe to server publish socket
        self.subscriber = self._ctx.socket(zmq.SUB)
        self.subscriber.connect(str(self.config.get("server_pub_socket")))
        
        # Subscribe to get fanstate commands
        self.subscriber.subscribe(self.topics.get('fanstate')) 
        
        # Subscribe to fancontrol commands
        self.subscriber.subscribe(self.topics.get('fancontrol'))
                
        # Provision for a debug mode where we provide fake temperature data
        if not self.config.get("fan_debug"):
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
            logger.info("Started fan controller in Debug mode:")
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
        msg = topic + separator + str(message) + "::" + dt.now().strftime("%H:%M:%S")

        return msg

    def run(self):
        """
        Main loop of our fan conttroller driver.
        """
        logger.info("Entering run loop")

        # Enter forever loop
        while True:
            
            try:
                # Look for any messages from the server - don't block
                message = self.subscriber.recv_string(flags=zmq.NOBLOCK)
                
                # Parse the message from the server
                self.parse_message(message)
            
            except zmq.Again as e:
                # If no message rx'd, do nothing
                pass            
            
            time.sleep(self.config.get("server_update_rate"))
            
    def parse_message(self, msg):
        """Parse messages received over the ZMQ server subscriber port and execute function

        Args:
            msg (str): Message received over the ZMQ interface

        Returns:
            int: Status
        """
        
        status = 1
        
        # Split the topic and the message
        topic, messagedata = msg.split('::')
        
        if topic == self.topics.get("fancontrol"):
            
            logger.info(f"Got request {messagedata} from plant manager")

            if messagedata == self.requests.get("getstate"):
                self.send_GPIO_state()
            elif messagedata == self.requests.get("turnoff"):
                self.set_OFF()
            elif messagedata == self.requests.get("turnon"):
                self.set_ON()
            else:
                logger.warning("Received unrecognized request over ZMQ")
                status = -100
        else:
            logger.warning("Received unrecognized topic over ZMQ")
            status = -100
                     
        return status          

        
            
    def set_ON(self) -> int:
        """Set the relay GPIO to high, thereby turning the fan circuit ON, and report to server

        Returns:
            int: Status
        """
        status = 1
        
        try:
            # Set the fan state via GPIO
            GPIO.output(self.relay_pin, GPIO.HIGH) 
            
            # Update the state tracker   
            read_state = self.get_GPIO_state()
            
            if read_state == self.states.get("on"):
                # Log event
                logger.info("Fan turned ON")
                
            elif read_state == self.states.get("off"):
                logger.warning("Asked for ON, got OFF")
                
            else:
                logger.warning("Relay pin reported unrecognized state")
                                                
            # Send ack message to server
            self.send_GPIO_state()       
            
        except:
            # If we are in debug mode, the above wont work so go here.
            if self.config.get("fan_debug"):
                logger.info("DEBUG MODE: Fan turned ON")
                
                # Set the state variable without actually turning on the relay/fan assembly
                self.state = self.states.get("on")
                self.send_GPIO_state()

            # If we are not in debug mode but we get here, it is an error
            else:
                logger.warning("Unable to turn fan ON.")
                status = -100
                
                # Send the current state with an error message
                msg = self.add_topic(self.topics.get('error'), self.get_GPIO_state())
                self.publisher.send_string(msg)
                logger.info("Sent error message and current state to plant manager")
                
        return status
                

    def set_OFF(self) -> int:
        """Set the relay GPIO to low, thereby turning the fan circuit OFF, and report to server

        Returns:
            int: Status
        """
        
        status = 1
        
        try:
            
            # Set the fan state via GPIO
            GPIO.output(self.relay_pin, GPIO.LOW) 
            
            # Update the state tracker   
            read_state = self.get_GPIO_state()
            
            if read_state == self.states.get("off"):
                # Log event
                logger.info("Fan turned OFF")
                
            elif read_state == self.states.get("off"):
                logger.warning("Asked for OFF, got ON")
                
            else:
                logger.warning("Relay pin reported unrecognized state")
            
            # Send ack message to server
            self.send_GPIO_state()
            
        except:
            
            # If we are in debug mode, the above wont work so go here.
            if self.config.get("fan_debug"):
                logger.info("DEBUG MODE: Fan turned OFF")
                
                # Set the state variable without actually turning on the relay/fan assembly
                self.state = self.states.get("off")
                self.send_GPIO_state()

                
            # If we are not in debug mode but we get here, it is an error
            else:
                logger.warning("Unable to turn fan OFF.")
                status = -100
                
                # Send the current state with an error message
                msg = self.add_topic(self.topics.get('error'), str(self.get_GPIO_state()))
                self.publisher.send_string(msg)
                logger.info("Sent error message and current state to plant manager")
                
        return status
        
    def get_GPIO_state(self) -> bool:
        """Get the current state of the relay GPIO pin

        Returns:
            bool: Return the state of the GPIO pin
        """
        read_state = GPIO.input(self.relay_pin)
        
        if read_state == True:
            self.state = self.states.get("on")
        elif read_state == False:
            self.state = self.states.get("off")
        else:
            return -100
            
        logger.info(f"Requested fan state, got {read_state}")

        return self.state
    
    def send_GPIO_state(self) -> None:
        """Send relay state to server
        """
        msg = self.add_topic(self.topics.get('fanstate'), self.state)
        self.publisher.send_string(msg)
        logger.info(f"Sent state {self.state} to plant manager")

        return
    
    def exit(self):
        """Gracefully shutdown zmq ports and exit the program
        """
        logger.info("Gracefully exiting")
        self.publisher.close()
        self.subscriber.close()
        self._ctx.term()
        print("\nshutdown")
        sys.exit(0)
    
if __name__ == "__main__":

    # Specify configuration file
    cfg = os.path.join(parent_dir, "cfg", "watches_cfg.json")
    
    # Create a digital sensor object to mirror our physical one
    fan = fan_controller(cfg)
    
    # Handle exits
    try:
        fan.run()
    except KeyboardInterrupt:
        logger.info("Got shutdown signal")
        fan.exit()
