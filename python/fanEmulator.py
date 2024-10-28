#!/usr/bin/env python3

import zmq
import time
import numpy as np
import matplotlib.pyplot as plt

class bcolors:
    OKBLUE = '\033[94m'
    OKRED = '\033[93m'
    OKGREEN = '\033[92m'
    ENDC = '\033[0m'
class fan_relay_controller:

def run():

    # Specify how often we want to update our readings
    looptime = 1

    # Establish ZMQ subscribing context (magic)
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)

    # Bind to our listener port 
    subscriber.connect("tcp://127.0.0.1:5557")
    
    # We are interested in any message with the topic "fancontrol"
    topic = "fancontrol"
    subscriber.subscribe(topic)   
    colors = bcolors()

    # Initialize a plot to view our data
    while True:
        
        # Receive messages over the ZMQ link
        message = subscriber.recv_string()

        # Isolate the temperature reading from the entire message
        topic, messagedata = message.split('::')
        
        if messagedata == "on":
            fanstate = "on"
            color = colors.OKBLUE
        else:
            fanstate = "off"
            color = colors.OKRED
            
        print(f'FAN STATE: {color}{fanstate}{colors.ENDC}')


if __name__ == "__main__":

    run()
