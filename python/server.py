#!/usr/bin/env python3

import zmq
import time
import numpy as np
import matplotlib.pyplot as plt
from sensor import add_topic

class fanHandler:
    def __init__(self): 
        self.relay_state = []
        pass
    def handle_logic(self, temp):
        pass
    
def relay_state_logic(currentTemp, on_threshold, off_threshold, current_state_of_relay):
    # Write our function here
    # True == on
    # False == off
    # Comparators:
    # Less than <
    # Greater than >
    # Equal to ==
    # Less than or equal to <=
    # Greater than or equal to >=
    # logical and &
    # logical or |

    if current_state_of_relay == True:
        if currentTemp > 140:
            command = "on"
        elif currentTemp <= 140:
            command = "off"
            
    elif current_state_of_relay == False:
        if currentTemp > 175:
            command = "on"
        elif currentTemp <= 175:
            command ="off"
            
    else:
        # Error state
        Warning('Somethings not right.')
    
    return command

# preallocate empty array and assign slice
def update_temps(arr, num=1, fill_value=np.nan):
    """
    Update the temperature vector by shifting the numpy array and filling in the lost value
    """
    result = np.empty_like(arr)
    if num > 0:
        result[:num] = fill_value
        result[num:] = arr[:-num]
    elif num < 0:
        result[num:] = fill_value
        result[:num] = arr[-num:]
    else:
        result[:] = arr
    return result

def run():

    # Specify how often we want to update our readings
    looptime = 1

    # Establish ZMQ subscribing context (magic)
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)

    # Bind to our listener port 
    subscriber.bind("tcp://127.0.0.1:5556")
    
    # We are interested in any message with the topic "temp"
    topic = "temp"
    subscriber.subscribe(topic)
    
    # Create a publisher    
    context = zmq.Context()
    publisher = context.socket(zmq.PUB)
    publisher.bind("tcp://127.0.0.1:5557")

    # Initialize an empty array to store our temperature readings
    # 60 entries = 1 minute
    temps = np.zeros(60)

    # Initialize a plot to view our data
    plt.ion() 
    figure, ax = plt.subplots()
    line, = ax.plot(temps)
    plt.title('Running Temperature Reading')
    plt.ylabel('Temperature (C)')
    plt.ylim([0,40])
    plt.grid()

    while True:

        # Receive messages over the ZMQ link
        message = subscriber.recv_string()
        
        # Isolate the temperature reading from the entire message
        topic, messagedata = message.split('::')
        
        # Convert the temperature reading from a string to an integer
        currentTemp = float(messagedata)

        # Add our current temperature to our running array of temperatures
        temps = update_temps(temps,1,currentTemp)

        # Update our plot (magic)
        line.set_ydata(temps)
        figure.canvas.draw()
        figure.canvas.flush_events()
                
        # Logic for controlling the fan relay
        on_threshold = 175
        off_threshold = 140
        relay_state = 0#TODO ASK RELAY CONTROLLER FOR ITS CURRENT STATE
        message_to_send_to_relay_controller = relay_state_logic(currentTemp, on_threshold, off_threshold, relay_state)
        publisher.send_string(message_to_send_to_relay_controller)
        print(f"sent message: {message_to_send_to_relay_controller}")
            
        # Loops are ungoverned, so we have to force a sleep every time or else we will run at 100% computing power
        time.sleep(looptime)

if __name__ == "__main__":

    run()
