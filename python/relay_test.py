#!/usr/bin/env python3

import RPi.GPIO as GPIO
import time

# Update for current test
relayPin = 10

# SET UP THE GPIO TO BE AN OUTPUT
GPIO.setmode(GPIO.BCM)
GPIO.setup(relayPin, GPIO.OUT)

# Initial State:
GPIO.output(relayPin, GPIO.LOW)


# TURN RELAY ON
time.sleep(1)
print('Turning on Relay for 5 seconds...')
GPIO.output(relayPin, GPIO.HIGH)

# WAIT FIVE SECONDS
time.sleep(5)

# TURN RELAY OFF
print('Turning off relay now.')
GPIO.output(relayPin, GPIO.LOW)

# DO THIS WHEN WE ARE DONE
GPIO.cleanup()