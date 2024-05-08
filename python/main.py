#!/usr/bin/env python3

from w1thermsensor import W1ThermSensor as w1s
import matplotlib.pyplot as plt
import numpy as np

def main():

    sensor1 = w1s()
    sensor1.get_temperature()

if __name__ == "__main__":

    main()

