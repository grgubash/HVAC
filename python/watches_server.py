#!/usr/bin/env python3

import zmq
import time
from datetime import datetime as dt
import numpy as np
import math
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import json
import logging
import logging.handlers
import os, sys
import signal

# TODO: Add proper state setting

# Set up the logger
now = dt.now()
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
    backupCount=1,
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
        
        # Determine log size
        log_array_size = 60 * 60 * 24 # We always want our plot to be at 1 second resolution
        
        # Allocate temperature log
        self.temp_log = np.empty(log_array_size)
        self.temp_log[:] = np.nan
        
        # Our time axis will be on the 24hr clock seconds index
        self.time_axis = np.arange(log_array_size)
        self.xlim_min = 0
        self.xlim_max = log_array_size # we can do this since it is equal to the time in seconds we are logging
        
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
        
        # If the fan is on, it needs to drop below set point - hysteresis to turn off
        if relay_state == self.states.get("on"):
            # Case: The fan is currently on
            if temp_reading > (self.config.get("set_point") - self.config.get("hysteresis")): #TODO: VERIFY THE SETPOINT LEVELS WITH SENIOR
                # Case: temp > set point, stay on 
                #self.set_fan_on()
                pass
            elif temp_reading <= (self.config.get("set_point") - self.config.get("hysteresis")):
                # Case: temp < set point, turn off
                self.set_fan_off()
            else:
                logger.warning('Unrecognized Inputs. Issuing error.')
                status = -100
                
        # If the fan is off, temp needs to reach set point to turn on
        elif relay_state == self.states.get("off"):
            # Case: The fan is currently on and heating
            if temp_reading > (self.config.get("set_point")):
                # Case: temp > set point, turn on
                self.set_fan_on()
            elif temp_reading <= (self.config.get("set_point")):
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
    
    def update_temp_log(self, value:float, timestamp:str) -> None:
        """ Maintain a time aligned vector of temperature readings from the temperature sensor

        Args:
            value (float): Input temperature reading
            timestamp (str): Input timestamp, from temp sensor
        """
        
        # convert the timestamp string to its seconds-in-the-day index
        h,m,s = list(map(int,timestamp.split(':')))
        seconds_idx = round(h*60*60 + m*60 + s)
        
        # Update the temp log for the given temperature index
        self.temp_log[seconds_idx] = value
        
        # Update our plot (magic)
        if self._verbose:
            self.plot_update(value, seconds_idx)

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
            self.plot_setup()

        while True:
            # Receive messages over the ZMQ link
            try:
                message = self.subscriber.recv_string(flags=zmq.NOBLOCK)
                
                # Parse the received message
                self.parse_message(message)
            
            except zmq.Again as e:
                # If no message rx'd, do nothing
                pass                
            
            # Every so often, ask the fan what state it is in so we can maintain an up to date state
            self.loop_ctr+=1
            if not self.loop_ctr % self.request_state_intvl:
                # Request the fan state every self.config.fan_update_rate seconds
                # This somewhat math abstracted conditional does that
                self.get_fan_state()
                self.loop_ctr = 0

            # Loops are ungoverned, so we have to force a sleep every time or else we will run at 100% computing power
            # Run the main loop faster than the hardware drivers (these are not strictly timed loops)
            time.sleep(self.config.get("server_update_rate"))
            
    def plot_setup(self) -> None:
        """ Initialie a matplotlib window to plot the temperature log
        """       
        # Set interactive on and create axes objects
        plt.ion() 
        self.figure, self.ax = plt.subplots()
        self.figure.set_figheight(6)
        self.figure.set_figwidth(10)
        
        # Plot the last 24 hours of readings
        self.line, = self.ax.plot(self.time_axis, self.temp_log, 'b', label="Historic readings")
        
        # Plot the current reading
        self.stem = self.ax.stem([0],[0],'r',  markerfmt ='D', label="Current reading")
        
        # Plot the set points
        setpoint_line = self.config.get("set_point") * np.ones(60*60*24)
        hysteresis_line = (self.config.get("set_point") - self.config.get("hysteresis")) * np.ones(60*60*24)
        
        # Don't expect to update these in realtime
        self.ax.plot(self.time_axis, setpoint_line, '#008000', label="Upper range")        
        self.ax.plot(self.time_axis, hysteresis_line, 'k', label="Lower range")

        # Set ax limits
        self.ax.set_xlim(left=0, right=len(self.time_axis))
        self.ax.set_ylim(bottom=80, top=160) #TODO: Add these to config file
        
        # Tick at every hour
        tick_idx = np.arange(0,60*60*24, 60*60 , dtype=int)
        self.ax.set_xticks(list(tick_idx))
        
        tick_labels =  [str(label) for label in range(24)]    
            
        for idx in np.arange(24):
            tick_labels[idx] =  tick_labels[idx] +'00'
            if idx < 10:
                tick_labels[idx] = '0' + tick_labels[idx] 
                    
        self.ax.set_xticklabels(tick_labels)
        self.ax.xaxis.set_tick_params(rotation=75)

        # Format the plot
        plt.title('Return Temperature')
        plt.ylabel('Temperature (F)')
        plt.xlabel('Time of Day (Hrs)')
        plt.grid()
            
        # Legend at bottom - make some space
        box = self.ax.get_position()
        self.ax.set_position([box.x0, box.y0 + box.height * 0.1,
                        box.width, box.height * 0.9])

        # Put a legend below current axis
        self.ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15),
                fancybox=True, shadow=True, ncol=5)
        
    def plot_update(self, current_temp_reading:float, current_time_idx:int) -> None:
        """Update the temperature log plot with the current reading

        Args:
            current_temp_reading (float): Most recent reported temperature reading
            current_time_idx (int): Time index corresponding
        """

        # Update the trace with new data        
        self.line.set_ydata(self.temp_log)
        
        # Highlight the current reading
        self.stem[0].set_ydata([current_temp_reading])
        self.stem[0].set_xdata([current_time_idx])
        
        self.figure.canvas.draw()
        self.figure.canvas.flush_events()
            
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
        topic, messagedata, timestamp = msg.split('::')
        
        if topic == self.topics.get('fanstate'):
            # Update our received fan state
            
            # Rx'd fan state data
            fan_state = messagedata
            self.reported_fan_state = fan_state
            self.waiting_for_fan_state = False
            
            if self.commanded_fan_state != self.reported_fan_state:
                self.state = self.states.get("warning")
                logger.warning("Fan reported state inconsistent with commanded state")
                
                # If this occurs, request again
                if self.commanded_fan_state == self.states.get("on"):
                    self.set_fan_off
                elif self.commanded_fan_state == self.states.get("off"):
                    self.set_fan_off
                else:
                    logger.warning('Unknown fan state')

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
            self.update_temp_log(temp_reading_f, timestamp)
            
            # Execute our fan control state machine
            self.relay_control_fsm(temp_reading_f, fan_state)
            
        else:
            logger.warning("Received unrecognized message over ZMQ")
            status = -100
            
        return status
    
    def exit(self):
        """Gracefully shutdown zmq ports and exit the program
        """
        logger.info("Gracefully exiting")
        self.publisher.close()
        self.subscriber.close()
        self._ctx.term()
        plt.close('all')
        print("\nshutdown")
        sys.exit(0)

if __name__ == "__main__":
    config_path = os.path.join(parent_dir, "cfg","watches_cfg.json")

    # Create WATCHES server objectour
    manager = plant_manager(config_path, verbose=True)

    # Handle exits
    try:
        manager.run()
    except KeyboardInterrupt:
        logger.info("Got shutdown signal")
        manager.exit()