#!/bin/bash

## lxterminal -e "./server.py" 
## lxterminal -e "./sensor.py" 
## lxterminal -e "./fanEmulator.py" 

lxterminal --command="/bin/bash --init-file ./server.py"
lxterminal --command="/bin/bash --init-file ./sensor.py"
lxterminal --command="/bin/bash --init-file ./fanEmulator.py"
