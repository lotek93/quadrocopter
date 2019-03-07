#!/usr/bin/python3

# HISTORY
# 0.3 added fixed cycle_time for measures, added reinit when fail
# 0.2 continuous background measurings version, adding moving average filter, added correct exiting
# 0.1 initial version

# TODO

# Commands are: HELO, CALIBRATE, GETDIST, EXIT

import RPi.GPIO as GPIO
import socket
import time
import sys
import pickle
from _thread import *

BUFSIZ = 1024
zero_height = 0 # correction
pin_echo = 17
pin_trig = 18
height = 1
cycle_time = 0.1
smooth = 5
heights = [0] * smooth
new_data_ready = False
dont_measure = True

def init():
    global dont_measure
    debug_print( "initializing soner" )
    dont_measure = True
    GPIO.setmode( GPIO.BCM )
    GPIO.cleanup( pin_trig )
    GPIO.cleanup( pin_echo )
    GPIO.setup( pin_trig, GPIO.OUT )
    GPIO.setup( pin_echo, GPIO.IN )
    GPIO.output( pin_trig, GPIO.LOW )
    time.sleep( 0.3 )
    dont_measure = False

def measures_thread():
    global height, heights, new_data_ready, dont_measure
    while not exiting:
        time_start = time.clock()
        GPIO.output( pin_trig, True )
        time.sleep( 0.00001 )
        GPIO.output( pin_trig, False )
        while GPIO.input(pin_echo) == 0:
            signaloff = time.time()
        while GPIO.input(pin_echo) == 1:
            signalon = time.time()
        timepassed = signalon - signaloff
        heights[1:smooth] = heights[0:smooth-1]
        heights[0] = timepassed * 17000 - zero_height
#        height = sum( heights ) / smooth
        height = heights[0]
        new_data_ready = True

        while dont_measure:
            dont_measure = dont_measure
        waiting = cycle_time - (time.clock() - time_start)
        if waiting > 0:
            time.sleep( waiting )
#    GPIO.cleanup()

def conn_thread( conn ):
    global exiting, zero_height, new_data_ready
    while not exiting:
        request = pickle.loads( conn.recv(BUFSIZ) )
        time_start = time.clock()
        debug_print( "has been recieved '" + str(request) + "'" )
        if request[1] == 'HELO':
            reply = [ [request[0],time.clock()-time_start], ['OK', module_name + ' at your service'] ]
        elif request[1] == 'CALIBRATE':
            GPIO.output( pin_trig, True )
            time.sleep( 0.00001 )
            GPIO.output( pin_trig, False )
            while GPIO.input(pin_echo) == 0:
                signaloff = time.time()
            while GPIO.input(pin_echo) == 1:
                signalon = time.time()
            timepassed = signalon - signaloff
            zero_height = timepassed * 17000
            reply = [ [request[0],time.clock()-time_start], ["OK", zero_height] ]
            debug_print( "zero_height= " + str(zero_height) )
        elif request[1] == 'GETDIST':
            if new_data_ready:
                reply = [ [request[0],time.clock()-time_start], ["OK", height] ]
                debug_print( "height: " + str(height) )
                new_data_ready = False
            else:
                reply = [ [request[0],time.clock()-time_start], ['ERR', 'data not ready'] ]
                debug_print( "*** DATA NOT READY!" )
                init()
        elif request[1] == 'EXIT':
            reply = [ [request[0],time.clock()-time_start], ['OK', 'EXITING'] ]
            debug_print( "'EXITING' send" )
        else:
            reply = [ [request[0],time.clock()-time_start], ['ERR', 'UNKNOWN COMMAND'] ]
            debug_print( "sending 'UNKNOWN COMMAND'" )

        conn.sendall( pickle.dumps(reply,2) )
        
        if request[1] == 'EXIT':
            exiting = True
            debug_print( "exit command recieved, exiting" )
            s.shutdown( socket.SHUT_RDWR )
    conn.close()

def debug_print( msg ):
    if not daemon:
#    m = "[" + mname + "] " + format(time.clock()-start_clock,"0.3f") + ": " + msg
        m = "[" + module_name + "]: " + msg
        print( m )


if len(sys.argv) == 3:
    host = sys.argv[1]
    port = int(sys.argv[2])
    daemon = True
else:
    host = 'localhost'
    port = 10020
    daemon = False

module_name = 'soner_' + str(port)
exiting = False

debug_print( "starting at '" + host + ":" + str(port) + "'" )

init()

debug_print( 'starting measures' )
start_new_thread( measures_thread, () )

s = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
try:
    s.bind( (host,port) )
except socket.error as msg:
    debug_print( 'bind failed. error code : ' + str(msg) )
    sys.exit()

s.listen(2)
debug_print( 'now listening port' )

while not exiting:
    try:
        conn,addr = s.accept()
    except socket.error as msg:
        if exiting:
            debug_print( 'exiting exception' )
            time.sleep( 1 )
            break
        else:
            debug_print( 'accept failed. error code : ' + str(msg) )
            sys.exit()

    debug_print( "connected from " + str(addr[0]) + ':' + str(addr[1]) )
    start_new_thread( conn_thread, (conn,) )
s.close()
#GPIO.cleanup()
GPIO.cleanup( pin_trig )
GPIO.cleanup( pin_echo )
debug_print( "exiting" )
