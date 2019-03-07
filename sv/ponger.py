#!/usr/bin/python

# HISTORY
# 0.4 added commands HELO, PING, EXIT

#from socket import *
import socket
import time
import sys
import pickle
from thread import *

BUFSIZ = 1024

def conn_thread( conn ):
#    conn.send( module_name + ' welcomes you. waiting for commands' )
    while True:
        request = pickle.loads( conn.recv(BUFSIZ) )
#        print module_name + ": has been recieved '" + str(request) + "'"
        if request == 'HELO':
            reply = module_name + ' at your service'
        elif request == 'PING':
            reply = module_name + ' PONG'
            time.sleep( 3 )
        elif request == 'EXIT':
            reply = module_name + ' EXITING'
        conn.sendall( pickle.dumps(reply) )
#        print module_name + ": '" + reply + "' send"
        
        if request == 'EXIT': 
            time.sleep(1)
            print module_name + ": exit request recieved, exiting"
            break
    conn.close()

if len(sys.argv) == 3:
    ponger_host = sys.argv[1]
    ponger_port = int(sys.argv[2])
else:
    ponger_host = 'localhost'
    ponger_port = 8888

module_name = 'ponger_' + str(ponger_port)

print module_name + ": starting with '" + ponger_host + "'" + ", '" + str(ponger_port) + "'"
s = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
try:
    s.bind( (ponger_host,ponger_port) )
except socket.error , msg:
    print module_name + ': bind failed. error code : ' + str(msg[0]) + ' message ' + msg[1]
    sys.exit()
    
s.listen(2)
print module_name + ': now listening port'

while True:
    conn,addr = s.accept()
    print module_name + ": connected from " + str(addr[0]) + ':' + str(addr[1])
    start_new_thread( conn_thread, (conn,) )
s.close()
print module_name + ": exiting"

