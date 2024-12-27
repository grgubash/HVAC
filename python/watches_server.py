#!/usr/bin/env python3

import zmq
import time, datetime
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import json
import logging
import os

matplotlib.use('TkAgg')

#TODO See what happens when multiple zmq messages queue up

# Set up the logger
now = datetime.datetime.now()
parent_dir = os.path.split(os.getcwd())[0]
log_dir = os.path.join(parent_dir, "logs")

# Make a logs directory if it does not exist
if not os.path.isdir(log_dir):
    os.mkdir(log_dir)

logname = os.path.join(log_dir, "SERVER-" + now.strftime('%Y-%m-%dT%H-%M-%S') + ('-%02d' % (now.microsecond / 10000)) + ".log")
logging.basicConfig(filename=logname, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S%p', level=logging.INFO)
logger = logging.getLogger('WATCHES-SERVER')

class plant_manager:
    def __init__(self, config_fname:str, verbose:bool=True):
        """Construct a WATCHES server object

        Args:
            config_fname (str): Path to configuration file
        """
        # Load the configuration file
        self.load_cfg(config_fname)
        self._verbose = verbose
        
        # Allocate temperature log
        self.temp_log = np.zeros(self.config.get("log_size"))
        
        # Create a ZMQ publisher to talk to other hardware systems
        self._ctx = zmq.Context()
        self.publisher = self._ctx.socket(zmq.PUB)
        self.publisher.bind("tcp://127.0.0.1:" + str(self.config.get("server_pub_socket")))
        
        # Create a ZMQ subscriber to listen to other hardware systems
        self.subscriber = self._ctx.socket(zmq.SUB)
        self.subscriber.bind("tcp://127.0.0.1:" + str(self.config.get("server_sub_socket")))
        self.subscriber.subscribe("temp") 
        
        # Create a dict to contain our topics list
        self.topics = dict(fancontrol='fancontrol', temp='temp')
        
        # Flag to let us know if we are waiting on a request
        self.waiting_for_fan_state = False
            
        # Create a log
        logger.info("PLANT_MANAGER: Server initialzed")

    def __str__(self):
        return json.loads(self.config, indent=4)
        
    def load_cfg(self, config_fname:str):
        with open(config_fname) as f:
            cfg_file = json.load(f)
            
        self.config = cfg_file.get("config") 
        
    def add_topic(self, topic:str, message:str) -> str:
        """
        Simple function to add a topic to a string to be sent over ZMQ
        """
        separator = '::'
        msg = topic + separator + str(message)
        return msg
    
    def relay_control_fsm(self, temp_reading:float, relay_state:bool) -> str:
        """This is the logic that controls the fan.

        Args:
            temp_reading (float): _description_
            relay_state (bool): _description_

        Returns:
            str: _description_
        """
        status = 1
        
        if relay_state == True:
            # Case: The fan is currently on
            if temp_reading > (self.config.get("set_point") - self.config.get("hysteresis")):
                # Case: temp > 140, stay on 
                self.set_fan_on()
            elif temp_reading <= (self.config.get("set_point") - self.config.get("hysteresis")):
                # Case: temp < 140, turn off
                self.set_fan_off()
            else:
                logger.warning('Unrecognized Inputs. Issuing error.')
                status = -100
                
        elif relay_state == False:
            # Case: The fan is currently on and heating
            if temp_reading > (self.config.get("set_point") + self.config.get("hysteresis")):
                # Case: temp > 180, turn on
                self.set_fan_on()
            elif temp_reading <= (self.config.get("set_point") + self.config.get("hysteresis")):
                # Case: temp < 180, turn off
                self.set_fan_off()
            else:
                logger.warning('Unrecognized Inputs. Issuing error.')
                status = -1
        else:
            # Error state
            logger.warning('Unrecognized Inputs. Issuing error.')
            status = -100
            
        return status
    
    def update_temp_log(self, value:float=np.nan):
        """
        Update the temperature vector by shifting the numpy array and filling in the lost value
        """
        result = np.empty_like(self.temp_log)
        result[:1] = value
        result[1:] = self.temp_log[:-1]
        self.temp_log = result
        
        return 1
        
    def celsius_to_fahrenheit(self, input_temp_c:float):
        """ A function to take a temperature in celsius, and convert it to 
        fahrenheit.

        Args:
            temp_c (float): The temperature in celsius

        Returns:
            float: The temperature in fahrenheit. 
        """
        output_temp_f = (input_temp_c * 9/5) + 32 # equation for converting C -> F
        
        return output_temp_f

    def run(self):
        """ Run the control loop
        """
        
        logger.info("PLANT_MANAGER: Entering run loop")

        # Initialize a plot to view our data
        if self._verbose:
            time_axis = np.arange(0,self.config.get("log_size"))*self.config.get("update_rate")
            
            plt.ion() 
            figure, ax = plt.subplots()
            line, = ax.plot(time_axis, self.temp_log)
            plt.title('Running Temperature Reading')
            plt.ylabel('Temperature (F)')
            plt.xlabel('time')
            plt.ylim([100,200])
            plt.grid()

        while True:

            # Receive messages over the ZMQ link
            message = self.subscriber.recv_string()
            
            # Parse the received message
            #TODO

            # Isolate the temperature reading from the entire message
            topic, messagedata = message.split('::')
            
            # Convert the temperature reading from a string to an integer
            temp_reading_f = self.celsius_to_fahrenheit(float(messagedata))

            # Add our current temperature to our running array of temperatures
            self.update_temp_log(temp_reading_f)
            
            # Update our plot (magic)
            if self._verbose:
                line.set_ydata(self.temp_log)
                figure.canvas.draw()
                figure.canvas.flush_events()
                        
            # Logic for controlling the fan relay
            fan_state = self.get_fan_state()
            self.relay_control_fsm(temp_reading_f, fan_state)
                
            # Loops are ungoverned, so we have to force a sleep every time or else we will run at 100% computing power
            time.sleep(self.config.get("update_rate"))
            
    def set_fan_on(self) -> int:
        """ Request set fan control relay on

        Returns:
            int: Status
        """
        status = 1
        
        try:
            msg = self.add_topic(self.topics.get('fancontrol'), "on")
            self.publisher.send_string(msg)
            logger.info("PLANT_MANAGER: Set Fan ON")
        except:
            logger.warning("PLANT_MANAGER: Unable to set fan to on")
            status = -100
    
            return status
        
    def set_fan_off(self) -> int:
        """ Request set fan control relay off

        Returns:
            int: Status
        """
        status = 1

        try:
            msg = self.add_topic(self.topics.get('fancontrol'), "off")
            self.publisher.send_string(msg)
            logger.info("PLANT_MANAGER: Set Fan OFF")
        except:
            logger.warning("PLANT_MANAGER: Unable to set fan to off")
            status = -100
            
        return status
    
    def get_fan_state(self):
        """Request get the status of the fan relay

        Returns:
            relay state (bool): Current state of the fan control relay
        """
        status = 1
        topic = self.topics.get('fancontrol')
        
        try:
            msg = self.add_topic(topic, "get_state")
            self.publisher.send_string(msg)
            logger.info("PLANT MANAGER: Asked for fan state")
            self.waiting_for_fan_state = True
        except:
            logger.warning("PLANT_MANAGER: Unable to request fan state")
            status = -100
            
        return status
    
    def parse_message(self, msg:str):
        
        # Split the topic and the message
        topic, messagedata = msg.split('::')
        
        #TODO parse temp readings from the temp sensor and relay state message from the fan controller

        pass
        
if __name__ == "__main__":
    config_path = os.path.join(parent_dir, "cfg","watches_cfg.json")

    # Create WATCHES server objectour
    manager = plant_manager(config_path, verbose=True)
    manager.run()