# Water Coil Home Electronic Sensing (WATCHES): Glossary of Concepts

## The Terminal:
Also known as the console. This is a text based interface to your computer. It's a black box.


### Useful terminal commands

#### pwd: print working directory
Prints the path/address to the folder/directory that you are currently in

#### ls: list
List the contents of the folder/directory you are currently in. 

#### cd: change directory
Change from your current directory to a different directory. Note that "cd .." will move you UP one directory.

#### history
See a print out of your terminal history, everything you have types in recently. 

## The Text Editor
The text editor is the place we edit our code, or read documentation, or otherwise interact with text based files. There are many text editors, but the one built in to your Raspberry Pi is called "geany". 

### Starting the text editor
To open a file in the text editor:

"geany  < filename >"

OR use the following to open the text editor in the folder you are currently in:

"geany ."

## PYTHON
A general purpose programming language. There are tons of programming languages, but this is the one we want to use. To the naked eye, a python program file looks just like any other text file. However the .py filetype tells the computer that it is a special file that can be executed by the Python interpreter.

### The Python Interpreter
The interpreter is simply language to describe the underlying mechanics of python -- it is the underlying software that reads the .py textfiles and "interprets" the meaning, and then executes them. To a person, "5 + 5" looks like a pair of numbers and a symbol. To the Python interpreter, "5 + 5" is the number '10'.

### Running or Executing a Python Program
To run a python program, first navigate (cd) to the folder containing the program in the terminal. Then:

"python < filename.py >"

## Basic Programming / Computer Architecture Concepts

### Variables

Variables are abstract representations of data. They are symbols we use to represent numbers. They can be re-used and re-assigned. For example, we have used the variable "currentTemp" to represent a the most recent temperature reading from the system. Every second we poll the temperature sensor, and every time we overwrite the value "currentTemp". That way, at any moment, all we have to do is query the value of currentTemp to get the most recent temperature reading of our system. 

Variables can also hold more than one number. If you wanted a variable to contain a history of all the temperature measurements, you could make a variable called "allTemps" and append the value of currentTemp to it every time a measurement is taken. This will result in an ever growing list of temperature values.

Example:

dummyVariable = 15

We just created a variable, named dummyVariable, and set its value to 15. Consider:

dummyVariable + dummyVariable = 30

### Datatypes
This is a somewhat abstract notion. In programming variables can take on different datatypes. For instance:

dummyVariable = 5

Here, we create a variable, called dummyVariable, and set it equal to the number 5. 

dummyVariable = "5"

Here, we do the same thing, except python interprets this not as the NUMBER 5, but as the CHARACTER 5. The CHARACTER 5 is not a number and cannot be treated as a number. It can, however, be converted to a number. 

To convert a character to a number, you would do

dummyVariable = float(dummyVariable)

Here, we have taken our old variable, dummyVariable, converted it to a number using float(), and then overwrote its old value. "Float" is short for "floating point", which means that the number can have decimal points. There are other datatypes besides floats (numbers) and characters, but we will not consider them here.
