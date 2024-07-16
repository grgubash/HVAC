#!/bin/bash

lxterminal -e "./server.py" &
lxterminal -e "./sensor.py" &
lxterminal -e "./fanEmulator.py" &
