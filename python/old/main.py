#!/usr/bin/env python3

from w1thermsensor import W1ThermSensor as w1s
import matplotlib.pyplot as plt
import numpy as np
import time

def main():

    sensor1 = w1s()

    while True:
        current_temp = sensor1.get_temperature()
        #print("Current Temperature in Celsius:")
        print(str(current_temp))

        time.sleep(0.2)


if __name__ == "__main__":

    main()

