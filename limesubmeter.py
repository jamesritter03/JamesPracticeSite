#!/usr/bin/python

import RPi.GPIO as GPIO
import sqlite3 as sqlite
import thread                                               # maybe implement the newer threading module if we need it later
import time                                                 # used for sleeping threads
import datetime
import logging
import logging.handlers
import argparse
import sys

# Defaults
LOG_FILENAME = "/var/log/limesubmeter.log"
LOG_LEVEL = logging.INFO # Could be e.g. "DEBUG" or "WARNING"
dbConnection = None
myTable_Exists = None
myEXIT = False
myDB_Name = '/usr/local/bin/limesubmeter/lime.db'			# TODO: make this a cmd line arg later
dbUpdateRate = 60                                           # what should a good value for this be ?
subMeterPulseCounter = 0
metersn = 'submeter1000'                                    # TODO: make this a cmd line arg later

# Define and parse command line arguments
parser = argparse.ArgumentParser(description="Lime Submeter service")
parser.add_argument("-l", "--log", help="file to write log to (default '" + LOG_FILENAME + "')")

# If the log file is specified on the command line then override the default
args = parser.parse_args()
if args.log:
	LOG_FILENAME = args.log
# Configure logging to log to a file, making a new file at midnight and keeping the last 3 day's data
# Give the logger a unique name (good practice)
logger = logging.getLogger(__name__)
# Set the log level to LOG_LEVEL
logger.setLevel(LOG_LEVEL)
# Make a handler that writes to a file, making a new file at midnight and keeping 3 backups
handler = logging.handlers.TimedRotatingFileHandler(LOG_FILENAME, when="midnight", backupCount=3)
# Format each log message like this
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
# Attach the formatter to the handler
handler.setFormatter(formatter)
# Attach the handler to the logger
logger.addHandler(handler)	

# Make a class we can use to capture stdout and sterr in the log
class MyLogger(object):
        def __init__(self, logger, level):
                """Needs a logger and a logger level."""
                self.logger = logger
                self.level = level

        def write(self, message):
                # Only log if there is a message (not just a new line)
                if message.rstrip() != "":
                        self.logger.log(self.level, message.rstrip())

# Replace stdout with logging to file at INFO level

sys.stdout = MyLogger(logger, logging.INFO)
# Replace stderr with logging to file at ERROR level
sys.stderr = MyLogger(logger, logging.ERROR)

def subMeterPulseCallback(channel):
        global  subMeterPulseCounter
        subMeterPulseCounter += 1                  # NOTE: increment the pulse counter when the interrupt fires
        print ("Pulse event fired now there are %d total pulses" % subMeterPulseCounter)

def updateDatabasePulseCount(updateRate,endpointsn):
        global subMeterPulseCounter
        global myDB_Name
        global myEXIT
        dbConnection = None
        dbConnection = sqlite.connect(myDB_Name)
        lastValue = None
        with dbConnection:
                dbConnection.row_factory = sqlite.Row
                myDB_Cursor = dbConnection.cursor()
                lastValue = subMeterPulseCounter                    # NOTE: keep track locally so we don't need to do unnecessary db writes
                while (myEXIT < 1):
                        if (lastValue == subMeterPulseCounter):
                                print ("skipped writing to db because the pulse count is the same %d" % subMeterPulseCounter)
                        else:
                                myDB_Cursor.execute("UPDATE SubMeter SET consumption=:Counter WHERE endpointsn='submeter1'",{"Counter": subMeterPulseCounter})  # TODO: make the table a paramater also
                                dbConnection.commit()
                                lastValue = subMeterPulseCounter
                        		print ("just updated the db %d" % subMeterPulseCounter)
                        time.sleep(updateRate)

GPIO.setmode(GPIO.BCM)
GPIO.setup(5, GPIO.IN, pull_up_down=GPIO.PUD_UP)           # GPIO 5 (pin 29) set up as input. It is pulled up to stop false signals (note you can use pin 39 at the bottom of the same side as ground)
GPIO.add_event_detect(5, GPIO.FALLING, callback=subMeterPulseCallback, bouncetime=100)    # TODO: ******* do the math to figure out how big the bouncetime needs to be

print "TASK ------> Check if database exists if not create it and give permissions"

dbConnection = sqlite.connect(myDB_Name)                            # this will attach to the database if it exists or create it if it doesn't exist *** problem is when it creates a new one the permissions aren't set

with dbConnection:                                                  # NOTE: the "with" automatically releases resources and automatically handles errors

        dbConnection.row_factory = sqlite.Row                           # NOTE: this is a dictionary cursor it makes it easier to grab information from tuples by name
        myDB_Cursor = dbConnection.cursor()
        myDB_Cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table';")    # get the list of tables from the database
        rows = myDB_Cursor.fetchall()
        for row in rows:
                if (row["name"] == "SubMeter"):                         # NOTE: see if any tables are named SubMeter
                        myTable_Exists = True

                if (myTable_Exists < 1):
                        myDB_Cursor.execute("CREATE TABLE SubMeter(endpointsn TEXT, consumption INT);" )  # NOTE: create SubMeter table if it isn't found
                        myDB_Cursor.execute("INSERT INTO SubMeter VALUES('submeter1',0);")                # NOTE: initialize table with 1 record with sn = unassigned and a count of 0
                        dbConnection.commit()
                        print "Created SubMeter Table because it didn't exist "

                print ("TASK ------> need to add routine to check table schema of existing SubMeter table and fix it if it doesn't match")

                myDB_Cursor.execute("SELECT consumption FROM SubMeter WHERE endpointsn ='submeter1'")  # FIXME make this a paramater
                row = myDB_Cursor.fetchone()
                print "Starting pulse count %d " % row[0]
                subMeterPulseCounter = row[0]
                print ("Done with DB Init")

                try:
                        thread.start_new_thread( updateDatabasePulseCount, (dbUpdateRate,metersn))
                        print "launched db update thread"

                except:
                        print "error launching thread"

                while (myEXIT < 1):
                        mytime = datetime.datetime.now().isoformat()
                        print("main script loop heartbeat at %s " % mytime)
                        time.sleep(60)

GPIO.cleanup()                                                                                  # clean up GPIO on normal exit
print ("Pulse Counter is exiting...")
