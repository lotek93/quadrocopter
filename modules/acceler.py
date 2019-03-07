#!/usr/bin/python3

# HISTORY
# 0.5 continuous background measurings version, added correct exiting
# 0.4 added EXIT command
# 0.3 added calibration, suppress output when deamonized
# 0.2 misc addings
# 0.1 initial version

# TODO
# power management
# lowpass filter

from i2clibraries import i2c_adxl345
import socket
import time
import sys
import pickle
from _thread import *

BUFSIZ = 1024
ax, ay, az = 0, 0, 0
ax_corr, ay_corr, az_corr = 0, 0, 0 # corrections for axes accelerations
cycle_time = 0.1

def measures_thread():
    global ax, ay, az
    while not exiting:
        time_start = time.clock()
        (dataready, singletap, doubletap, activity, inactivity, freefall, watermark, overrun) = adxl345.getInterruptStatus()
        if dataready:
            (ax, ay, az) = adxl345.getAxes()
            ax -= ax_corr
            ay -= ay_corr
            az -= az_corr
#            debug_print( "ax: " + str(ax) + "|ay: " + str(ay) + "|az: " + str(az) )
        else:
            ax, ay, az = -1, -1, -1

        waiting = cycle_time - (time.clock() - time_start)
        if waiting > 0:
            time.sleep( waiting )

def conn_thread( conn ):
    global exiting, ax, ay, az, ax_corr, ay_corr, az_corr
    while not exiting:
        request = pickle.loads( conn.recv(BUFSIZ) )
        time_start = time.clock()
        debug_print( "has been recieved '" + str(request) + "'" )
        if request[1] == 'HELO':
            reply = [ [request[0],time.clock()-time_start], ['OK', module_name + ' at your service'] ]
        elif request[1] == 'CALIBRATE':
            n = 0
            ax, ay, az = 0, 0, 0
            time.sleep(1)
            for i in range(10):
                (dataready, singletap, doubletap, activity, inactivity, freefall, watermark, overrun) = adxl345.getInterruptStatus()
                if dataready:
                    (dx, dy, dz) = adxl345.getAxes()
                    ax += dx
                    ay += dy
                    az += dz
                    n += 1
                time.sleep(0.1)
            ax_corr = ax / n
            ay_corr = ay / n
            az_corr = az / n - 1.05
            reply = [ [request[0],time.clock()-time_start], ["OK", ax_corr, ay_corr, az_corr] ]
            debug_print( "ax_corr: " + str(ax_corr) + "| ay_corr: " + str(ay_corr) + "| az_corr " + str(az_corr) )
        elif request[1] == 'GETAXES':
            reply = [ [request[0],time.clock()-time_start], ["OK", ax, ay, az] ]
#            reply = [ [request[0],time.clock()-time_start], ["ERR", "data not ready"] ]
        elif request[1] == 'EXIT':
            reply = [ [request[0],time.clock()-time_start], ['OK', 'EXITING'] ]
            debug_print( "'EXITING' send" )
        else:
            reply = [ [request[0],time.clock()-time_start], ['ERR', 'UNKNOWN COMMAND'] ]
            debug_print( "sending 'UNKNOWN COMMAND'" )

#        debug_print( str(reply[1]) )
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
    port = 10010
    daemon = False

module_name = 'acceler_' + str(port)
exiting = False

debug_print( "starting at '" + host + ":" + str(port) + "'" )

debug_print( "initializing accelerometer" )
adxl345 = i2c_adxl345.i2c_adxl345(1)

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
