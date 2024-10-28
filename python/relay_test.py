#!/usr/bin/env python3

import RPi.GPIO as GPIO
import time

relayPin = 16

# SET UP THE GPIO TO BE AN OUTPUT
GPIO.setmode(GPIO.BCM)
GPIO.setup(relayPin, GPIO.OUT)

# Initial State:
GPIO.output(relayPin, GPIO.LOW)

# TURN RELAY ON
GPIO.output(relayPin, GPIO.HIGH)

# WAIT FIVE SECONDS
time.sleep(5)

# TURN RELAY OFF
GPIO.output(relayPin, GPIO.LOW)

# DO THIS WHEN WE ARE DONE
GPIO.cleanup()