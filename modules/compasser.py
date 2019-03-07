#!/usr/bin/python3

# HISTORY
# 0.2 filtering by decline a bigger changes
# 0.1 initial version, added moving average filter

# TODO
# - correction for non-horizontal
# - calibration

# Commands are: HELO, GETHEADING, EXIT

from i2clibraries import i2c_hmc5883l
import socket
import time
import sys
import pickle
import math
from _thread import *

BUFSIZ = 1024
bx = 299
by = 63
bz = -48.8
heading = 0
cycle_time = 0.1
smooth = 5
headings = [0] * smooth
exiting = False

def measures_thread():
    global heading, headings
    while not exiting:
        time_start = time.clock()
        (x, y, z) = hmc5883l.getAxes()
        x += bx
        y += by
        z += bz
        headings[1:smooth] = headings[0:smooth-1]
        headings[0] = math.atan2(y,x) * 180 / math.pi
#        heading = sum( headings ) / smooth
        if abs(headings[0]-headings[1]) < 45 or abs(headings[0]+360-headings[1]) < 45 or abs(headings[0]-360-headings[1]) < 45:
            heading = headings[0]
        else:
            headings[0] = headings[1]

        waiting = cycle_time - (time.clock() - time_start)
        if waiting > 0:
            time.sleep( waiting )

def conn_thread( conn ):
    global exiting, heading
    while not exiting:
        request = pickle.loads( conn.recv(BUFSIZ) )
        time_start = time.clock()
        debug_print( "has been recieved '" + str(request) + "'" )
        if request[1] == 'HELO':
            reply = [ [request[0],time.clock()-time_start], ['OK', module_name + ' at your service'] ]
#        elif request[1] == 'CALIBRATE':
#            reply = [ [request[0],time.clock()-time_start], ["OK", ax_corr, ay_corr, az_corr] ]
#            debug_print( "ax_corr: " + str(ax_corr) + "| ay_corr: " + str(ay_corr) + "| az_corr " + str(az_corr) )
        elif request[1] == 'GETHEADING':
            reply = [ [request[0],time.clock()-time_start], ["OK", heading] ]
#            reply = [ [request[0],time.clock()-time_start], ["ERR", "data not ready"] ]
        elif request[1] == 'EXIT':
            reply = [ [request[0],time.clock()-time_start], ['OK', 'EXITING'] ]
            debug_print( "'EXITING' send" )
        else:
            reply = [ [request[0],time.clock()-time_start], ['ERR', 'UNKNOWN COMMAND'] ]
            debug_print( "sending 'UNKNOWN COMMAND'" )

        debug_print( str(reply[1]) )
        conn.sendall( pickle.dumps(reply,2) )
        
        if request[1] == 'EXIT':
            exiting = True
            debug_print( "exit request recieved, exiting" )
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
    port = 10030
    daemon = False

module_name = 'compasser_' + str(port)

debug_print( "starting at '" + host + ":" + str(port) + "'" )

debug_print( "initializing compass" )
hmc5883l = i2c_hmc5883l.i2c_hmc5883l(1)
hmc5883l.setContinuousMode()

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
debug_print( "exiting" )
