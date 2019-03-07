#!/usr/bin/python3

# HISTORY
# 0.5 continuous background measurings version, added correct exiting
# 0.4 added EXIT command
# 0.3 added calibration, suppress logs when daemonize
# 0.2 added request/reply time measuring
# 0.1 initial version

# TODO
# power management
# lowpass filter

# Commands are: HELO, CALIBRATE, GETVEL, EXIT

from i2clibraries import i2c_itg3205
import socket
import time
import sys
import pickle
from _thread import *

BUFSIZ = 1024
alpha_corr, beta_corr, gamma_corr = 0, 0, 0 # corrections for angle velocities
alpha, beta, gamma = 0, 0, 0
cycle_time = 0.1
new_data_ready = False


def measures_thread():
    global alpha, beta, gamma, new_data_ready
    while not exiting:
        time_start = time.clock()
        (itgready, dataready) = itg3205.getInterruptStatus()
        if dataready:
            (d_alpha, d_beta, d_gamma) = itg3205.getDegPerSecAxes()
            d_alpha -= alpha_corr
            d_beta -= beta_corr
            d_gamma -= gamma_corr
#            debug_print( "ax: " + str(ax) + "|ay: " + str(ay) + "|az: " + str(az) )
            new_data_ready = True
        else:
            new_data_ready = False

        waiting = cycle_time - (time.clock() - time_start)
        if waiting > 0:
            time.sleep( waiting )

def conn_thread( conn ):
    global alpha, beta, gamma, alpha_corr, beta_corr, gamma_corr
    while True:
        request = pickle.loads( conn.recv(BUFSIZ) )
        time_start = time.clock()
        debug_print( "has been recieved '" + str(request) + "'" )
        if request[1] == 'HELO':
            reply = [ [request[0],time.clock()-time_start], ['OK', module_name + ' at your service'] ]
        elif request[1] == 'CALIBRATE':
            n = 0
            a, b, g = 0, 0, 0
            time.sleep(1)
            for i in range(20):
                (itgready, dataready) = itg3205.getInterruptStatus()
                if dataready:
                    (da, db, dg) = itg3205.getDegPerSecAxes()
                    a += da
                    b += db
                    g += dg
                    n += 1
                time.sleep(0.1)
            alpha_corr = a / n
            beta_corr = b / n
            gamma_corr = g / n
            reply = [ [request[0],time.clock()-time_start], ["OK", alpha_corr, beta_corr, gamma_corr] ]
            debug_print( "alpha_corr: " + str(alpha_corr) + "| beta_corr: " + str(beta_corr) + "| gamma_corr: " + str(gamma_corr) )
        elif request[1] == 'GETAXES':
            (itgready, dataready) = itg3205.getInterruptStatus()
            if dataready:
                (x, y, z) = itg3205.getAxes()
                reply = [ [request[0],time.clock()-time_start], ["OK", x, y, z] ]
                debug_print( "X: " + str(x) + "|Y: " + str(y) + "|Z: " + str(z) )
            else:
                reply = [ [request[0],time.clock()-time_start], ["ERR", "data not ready"] ]
                debug_print( "sending 'data not ready'" )
        elif request[1] == 'GETVEL':
            if new_data_ready:
                reply = [ [request[0],time.clock()-time_start], ["OK", d_alpha, d_beta, d_gamma] ]
                debug_print( "d_alpha: " + str(d_alpha) + "|d_beta: " + str(d_beta) + "|d_gamma: " + str(d_gamma) )
            else:
                reply = [ [request[0],time.clock()-time_start], ["ERR", "data not ready"] ]
                debug_print( "*** DATA NOT READY!" )
        elif request[1] == 'EXIT':
            reply = [ [request[0],time.clock()-time_start], ['OK', 'EXITING'] ]
            debug_print( "'EXITING' send" )
        else:
            reply = [ [request[0],time.clock()-time_start], ['ERR', 'UNKNOWN COMMAND'] ]
            debug_print( "sending 'UNKNOWN COMMAND'" )
            
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
    port = 10000
    daemon = False

module_name = 'gyroer_' + str(port)
exiting = False
debug_print( "starting at '" + host + ":" + str(port) + "'" )

debug_print( "initializing gyro" )
itg3205 = i2c_itg3205.i2c_itg3205(1,0x68)

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
