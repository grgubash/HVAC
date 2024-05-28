#!/usr/bin/env python3

import zmq
import time
import numpy as np
import matplotlib.pyplot as plt

# preallocate empty array and assign slice by chrisaycock
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

    # Specify a port to communicate over
    port = "5556"

    # Specify how often we want to update our readings
    looptime = 1

    # Establish ZMQ subscribing context (magic)
    context = zmq.Context()
    socket = context.socket(zmq.SUB)

    # Connect to our port 
    socket.connect ("tcp://localhost:%s" % port)
    
    # We are interested in any message with the topic "temp"
    topic = "temp"
    socket.subscribe(topic)

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
        message = socket.recv_string()
        #print(f"Received: {message} via ZMQ link")
       
        # Isolate the temperature reading from the entire message
        topic, messagedata = message.split('::')
        
        # Convert the temperature reading from a string to an integer
        currentTemp = int(messagedata)

        # Add our current temperature to our running array of temperatures
        temps = update_temps(temps,1,currentTemp)

        # Update our plot (magic)
        line.set_ydata(temps)
        figure.canvas.draw()
        figure.canvas.flush_events()
 
        # Loops are ungoverned, so we have to force a sleep every time or else we will run at 100% computing power
        time.sleep(looptime)

if __name__ == "__main__":

    run()
