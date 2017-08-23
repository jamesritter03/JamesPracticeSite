import time
import serial
# TODO: make serial port and speed command line parms and default to this one if not present

ser = serial.Serial('/dev/serial/by-id/usb-SimTech__Incorporated_SimTech_SIM5320-if03-port0', 115200, timeout=1)
try:
        print(ser.name)
except Exception, e:
        print "error opening serial port: " + str(e)
        exit()

if ser.isOpen():
        try:
                ser.flushInput()
                ser.flushOutput()
                ser.write('AT+CSQ\r\n')
                time.sleep(0.5)
                response = ser.read(100)
                print(response)
                ser.close()
        except Exception, e1:
                print "error communicating ....: " + str(e1)
else:
        print "cannot open serial port "
