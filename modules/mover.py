#!/usr/bin/python3

# HISTORY
# 0.2 added correct exiting
# 0.1 initial version

# TODO

#Commands are: HELO, INIT, SET (pin,value), SETALL (values), EXIT

import socket
import time
import sys
import pickle
from _thread import *

BUFSIZ = 1024

class PWM:
    def __init__( self, pin ):
        self.pin = pin

    def set( self, value ):
        f = open( "/dev/pi-blaster", "w" )
        f.write( '%d=%.3f\n' % (self.pin,value) )
        f.close()

def conn_thread( conn ):
    global exiting
    while not exiting:
        request = pickle.loads( conn.recv(BUFSIZ) )
        time_start = time.clock()
        debug_print( "has been recieved '" + str(request) + "'" )
        if request[1] == 'HELO':
            reply = [ [request[0],time.clock()-time_start], ["OK", module_name + ' at your service'] ]
        elif request[1] == 'INIT':
            for m in motors:
                m.set( 0 )
            reply = [ [request[0],time.clock()-time_start], ["OK", "INIT OK"] ]
            debug_print( "INIT OK" )
        elif request[1] == 'SET':
            m = request[2][0]
            vol = request[2][1]
            motors[m].set( vol )
            reply = [ [request[0],time.clock()-time_start], ["OK"] ]
            debug_print( "motor " + str( m ) + ": set " + str(vol) )
        elif request[1] == 'SETALL':
            debug_msg = 'SETALL: '
            for i in range(len(motors)):
                vol = request[2][i]
                motors[i].set( vol )
                debug_msg += '{:0.3f}  '.format(vol)
            reply = [ [request[0],time.clock()-time_start], ["OK"] ]
            debug_print( debug_msg )
        elif request[1] == 'EXIT':
            for i in range(4):
                motors[i].set( 0 )
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
    port = 10100
    daemon = False

module_name = 'mover_' + str(port)
exiting = False

debug_print( "starting at '" + host + ":" + str(port) + "'" )

debug_print( "initializing motors" )
#m0 = PWM( 17 )
#m1 = PWM( 18 )
#m2 = PWM( 27 )
#m3 = PWM( 4 )
m4 = PWM( 22 )
m5 = PWM( 23 )
m6 = PWM( 24 )
m7 = PWM( 25 )
#motors = [ m0, m1, m2, m3 ]
motors = [ m4, m5, m6, m7 ]
#motors = [ m0, m1, m2, m3, m4, m5, m6, m7 ]
for m in motors:
    m.set( 0 )

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
