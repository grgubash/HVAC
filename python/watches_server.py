#!/usr/bin/env python3

import zmq
import time, datetime
import numpy as np
import math
import matplotlib
import matplotlib.pyplot as plt
import json
import logging
import logging.handlers
import os

# TODO: Add proper state setting

matplotlib.use('TkAgg')

# Set up the logger
now = datetime.datetime.now()
parent_dir = os.path.split(os.getcwd())[0]
log_dir = os.path.join(parent_dir, "logs")

# Make a logs directory if it does not exist
if not os.path.isdir(log_dir):
    os.mkdir(log_dir)

# Set up the logger
logname = os.path.join(log_dir, "PLANTMANAGER-" + now.strftime('%Y-%m-%dT%H-%M-%S') + ('-%02d' % (now.microsecond / 10000)) + ".log")

rfh = logging.handlers.RotatingFileHandler(filename=logname, 
    mode='a',
    maxBytes=5*1024*1024,
    backupCount=2,
    encoding=None,
    delay=0,
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                    datefmt='%m/%d/%Y %I:%M:%S%p', 
                    level=logging.INFO,
                    handlers=[rfh])

logger = logging.getLogger('WATCHES-PLANT-MANAGER')

class plant_manager:
    def __init__(self, config_fname:str, verbose:bool=True) -> None:
        """Construct a WATCHES server object

        Args:
            config_fname (str): Path to configuration file
            verbose (bool): Runtime option to generate verbose output
        """
        # Load the configuration file
        self.load_cfg(config_fname)
        self.request_state_intvl = round(self.config.get("fan_update_rate") / self.config.get("server_update_rate"))
        self.loop_ctr = 0
        self._verbose = verbose
        
        # Create a dict to contain our topics list and states
        self.topics = dict(fancontrol='fancontrol', fanstate='fanstate', temp='temp')
        self.requests = dict(getstate="getstate", turnon="turnon", turnoff = "turnoff")
        self.states = dict(on="on", off="off", error="error", warning="warning")
        self.state = self.states.get("off")
        
        # Allocate temperature log
        self.temp_log = np.zeros(self.config.get("log_size"))
        
        # Create a ZMQ publisher to talk to other hardware systems
        self._ctx = zmq.Context()
        self.publisher = self._ctx.socket(zmq.PUB)
        self.publisher.bind(str(self.config.get("server_pub_socket")))
        
        # Create a ZMQ subscriber to listen to other hardware systems
        self.subscriber = self._ctx.socket(zmq.SUB)
        self.subscriber.bind(str(self.config.get("server_sub_socket")))
        self.subscriber.subscribe(self.topics.get("temp")) 
        self.subscriber.subscribe(self.topics.get("fanstate"))

        
        # Flag to let us know if we are waiting on a request
        self.waiting_for_fan_state = False
        self.commanded_fan_state = self.states.get("off")
        self.reported_fan_state =  self.states.get("off")
            
        # Create a log
        logger.info("Server initialzed")

    def __str__(self) -> str:
        """ __str__ method

        Returns:
            str: String representation of the class config
        """
        return json.loads(self.config, indent=4)
        
    def load_cfg(self, config_fname:str) -> None:
        """Load the WATCHES configuration JSON file

        Args:
            config_fname (str): JSON file specifying the operating parameters of this instance of the server
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
    
    def relay_control_fsm(self, temp_reading:float, relay_state:bool) -> str:
        """This is the logic that controls the fan. It is a simple threshold with 
        hysteresis state control implementation. 

        Args:
            temp_reading (float): Temperature reading sent from the temperature sensor driver process
            relay_state (bool): Current state of the fan relay, as inferred from the relay driver process

        Returns:
            int: Status
        """
        status = 1
        
        if relay_state == self.states.get("on"):
            # Case: The fan is currently on
            if temp_reading > (self.config.get("set_point") - self.config.get("hysteresis")):
                # Case: temp > set point, stay on 
                #self.set_fan_on()
                pass
            elif temp_reading <= (self.config.get("set_point") - self.config.get("hysteresis")):
                # Case: temp < set point, turn off
                self.set_fan_off()
            else:
                logger.warning('Unrecognized Inputs. Issuing error.')
                status = -100
                
        elif relay_state == self.states.get("off"):
            # Case: The fan is currently on and heating
            if temp_reading > (self.config.get("set_point") + self.config.get("hysteresis")):
                # Case: temp > set point, turn on
                self.set_fan_on()
            elif temp_reading <= (self.config.get("set_point") + self.config.get("hysteresis")):
                # Case: temp < set point,stay off
                #self.set_fan_off()
                pass
            else:
                logger.warning('Unrecognized Inputs. Issuing error.')
                status = -1
        else:
            # Error state
            logger.warning('Unrecognized Inputs. Issuing error.')
            status = -100
            self.state = self.states.get("error")
            
        return status
    
    def update_temp_log(self, value:float=np.nan) -> None:
        """
        Update the temperature vector by shifting the numpy array and filling in the lost value
        """
        result = np.empty_like(self.temp_log)
        result[:1] = value
        result[1:] = self.temp_log[:-1]
        self.temp_log = result
        
        # Log it
        logger.info(f"Got temperature reading {value} degF")
                
    def celsius_to_fahrenheit(self, input_temp_c:float) -> float:
        """ A function to take a temperature in celsius, and convert it to 
        fahrenheit.

        Args:
            temp_c (float): The temperature in celsius

        Returns:
            float: The temperature in fahrenheit. 
        """
        output_temp_f = (input_temp_c * 9/5) + 32 # equation for converting C -> F
        
        return output_temp_f

    def run(self) -> None:
        """ Run the control loop
        """
        
        logger.info("Entering run loop")

        # Initialize a plot to view our data
        if self._verbose:
            
            #TODO: Properly scale the time axis
            time_axis = np.arange(0,self.config.get("log_size"))*self.config.get("server_update_rate")
            
            plt.ion() 
            figure, ax = plt.subplots()
            line, = ax.plot(time_axis, self.temp_log)
            plt.title('Running Temperature Reading')
            plt.ylabel('Temperature (F)')
            plt.xlabel('time')
            plt.ylim([0,200])
            plt.grid()

        while True:

            # Receive messages over the ZMQ link
            try:
                message = self.subscriber.recv_string(flags=zmq.NOBLOCK)
                
                # Parse the received message
                self.parse_message(message)
            
            except zmq.Again as e:
                # If no message rx'd, do nothing
                pass                
            
            # Update our plot (magic)
            if self._verbose:
                line.set_ydata(self.temp_log)
                figure.canvas.draw()
                figure.canvas.flush_events()
            
            
            # Every so often, ask the fan what state it is in so we can maintain an up to date state
            self.loop_ctr+=1
            if not self.loop_ctr % self.request_state_intvl:
                # Request the fan state every self.config.fan_update_rate seconds
                # This somewhat math abstracted conditional does that
                self.get_fan_state()
                self.loop_ctr = 0

            # Loops are ungoverned, so we have to force a sleep every time or else we will run at 100% computing power
            # Run the main loop ~4 times faster than the hardware drivers (these are not strictly timed loops)
            time.sleep(self.config.get("server_update_rate"))
            
    def set_fan_on(self) -> int:
        """ Request set fan control relay on

        Returns:
            int: Status
        """
        status = 1
        
        try:
            msg = self.add_topic(self.topics.get('fancontrol'), self.requests.get("turnon"))
            self.publisher.send_string(msg)
            logger.info("Set Fan ON")
            self.commanded_fan_state = self.states.get("on")
        except:
            logger.warning("Unable to set fan to on")
            status = -100
    
            return status
        
    def set_fan_off(self) -> int:
        """ Request set fan control relay off

        Returns:
            int: Status
        """
        status = 1

        try:
            msg = self.add_topic(self.topics.get('fancontrol'), self.requests.get("turnoff"))
            self.publisher.send_string(msg)
            logger.info("Set Fan OFF")
            self.commanded_fan_state = self.states.get("off")
        except:
            logger.warning("Unable to set fan to off")
            status = -100
            
        return status
    
    def get_fan_state(self) -> int:
        """Request get the status of the fan relay

        Returns:
            int: Status
        """
        status = 1
        topic = self.topics.get('fancontrol')
        
        try:
            msg = self.add_topic(topic, self.requests.get("getstate"))
            self.publisher.send_string(msg)
            logger.info("Asked for fan state")
            self.waiting_for_fan_state = True
        except:
            logger.warning("Unable to request fan state")
            status = -100
            
        return status
    
    def parse_message(self, msg:str) -> int:
        """Parse messages received over the ZMQ server subscriber port

        Args:
            msg (str): Message received over the ZMQ interface

        Returns:
            int: Status
        """
        
        status = 1
        
        # Split the topic and the message
        topic, messagedata = msg.split('::')
        
        if topic == self.topics.get('fanstate'):
            # Update our received fan state
            
            # Rx'd fan state data
            fan_state = messagedata
            self.reported_fan_state = fan_state
            self.waiting_for_fan_state = False
            
            if self.commanded_fan_state != self.reported_fan_state:
                self.state = self.states.get("warning")
                logger.warning("Fan reported state inconsistent with commanded state")
            elif self.commanded_fan_state == self.reported_fan_state:
                self.state = self.states.get("on")
            
            logger.info(f"Got fan state {fan_state} from FANCONTROL")                               
            
        elif topic == self.topics.get('temp'):
            # Update our temperature log
            # Rx'd sensor data
            temp_reading_f = float(messagedata)
            
            # Logic for controlling the fan relay
            fan_state = self.reported_fan_state
            
            # Update temp log
            self.update_temp_log(temp_reading_f)
            
            # Execute our fan control state machine
            self.relay_control_fsm(temp_reading_f, fan_state)
            

            
        else:
            logger.warning("Received unrecognized message over ZMQ")
            status = -100
            
        return status
   
if __name__ == "__main__":
    config_path = os.path.join(parent_dir, "cfg","watches_cfg.json")

    # Create WATCHES server objectour
    manager = plant_manager(config_path, verbose=False)
    manager.run()