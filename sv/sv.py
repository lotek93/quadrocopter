#!/usr/bin/python
# HISTORY:
# 0.20 added compasser
# 0.19 manual guiding
# 0.18 added soner
# 0.17 added mover, speed up & slow down
# 0.16 added acceler angles
# 0.15 added EXIT command
# 0.14 added python versions for modules, keyboard input
# 0.13 added calibration request for modules
# 0.12 added coordinates to gyroer, changed time.clock() to time.time()
# 0.11 added curses
# 0.10 changed main cycle
# 0.9 added request/reply times measuring
# 0.8 applying gyroer
# 0.7 another thread for select; adding times
# 0.6 added select for sockets
# 0.5 added commands HELO, PING, EXIT
# 0.4 added pickle transmission

# TODO
# - launch modules in parallel

import curses
import time
import os
import socket
import sys
import pickle
import select
import thread
import math

BUFSIZ = 1024

gyroer = {'name':'gyroer','pyversion':3,'script':'../modules/gyroer.py','host':'localhost','port':10000,'connected':False,'ready':False}
acceler = {'name':'acceler','pyversion':3,'script':'../modules/acceler.py', 'host':'localhost', 'port':10010, 'connected':False, 'ready':False}
soner = {'name':'soner','pyversion':3,'script':'../modules/soner.py', 'host':'localhost', 'port':10020, 'connected':False, 'ready':False}
compasser = {'name':'compasser','pyversion':3,'script':'../modules/compasser.py','host':'localhost','port':10030,'connected':False,'ready':False}
mover = {'name':'mover','pyversion':3,'script':'../modules/mover.py','host':'localhost','port':10100,'connected':False,'ready':False}
ponger1 = {'name':'ponger1','pyversion':3,'script':'ponger.py', 'host':'localhost', 'port':8888, 'connected':False, 'ready':False}
ponger2 = {'name':'ponger2','pyversion':3,'script':'ponger.py', 'host':'localhost', 'port':9999, 'connected':False, 'ready':False}
leder =  {'name':'leder','pyversion':3,'script':'leder.py',  'host':'localhost', 'port':8889, 'connected':False, 'ready':False}

modules = [soner, compasser, mover, acceler, gyroer, ponger1] #,ponger2]#,leder]

x, y, z = 0, 0, 0
vx, vy, vz = 0, 0, 0
alpha, beta, gamma = 0, 0, 0
height = 0
heading = 45
keep_heading = 45
rotation = 0
rotscale = 7
motors = [0, 0, 0, 0]
#motors = [0, 0, 0, 0, 0, 0, 0, 0]

start_time = time.time()
stdscr = curses.initscr()
curses.noecho()
curses.cbreak()
stdscr.keypad(True)
#stdscr.scrollok(True)
stdscr.nodelay(True)

win_x = 0; win_y = 0
win_h = 50; win_w = 100
win = curses.newwin(win_h, win_w, win_y, win_x)
win.border('|','|','-','-','/','\\','\\','/')
win.scrollok(True)

def debug_print( mname, msg ):
    global start_time
    m = "[" + mname + "] " + format(time.time()-start_time,"0.3f") + ": " + msg
    print m 

def log_print( mname, msg ):
    global start_time
    m = "[" + mname + "] " + format(time.time()-start_time,"0.3f") + ": " + msg
    print m 

def debug_cprint( mname, msg ):
    x = 2
    if mname == 'sv':
        y = 1
    elif mname == 'acceler':
        y = 3
    elif mname == 'acceler_angles':
        y = 4
    elif mname == 'gyroer':
        y = 6
    elif mname == 'soner':
        y = 7
    elif mname == 'compasser':
        y = 8
    elif mname == 'mover':
        y = 10
    win.addstr( y, x, mname + ': ' + msg + '          ' )
#    win.refresh()

def log_cprint( mname, msg ):
    win.setscrreg( 15, 40 )
    win.scroll()
    win.addstr( 40, 1, '[' + mname + '] ' + format(time.time()-start_time,"0.3f") + ": " + msg )
    win.refresh()
    
def socks_thread():
#    global modules
    while True:
        recv_sock_list = []
        while len(recv_sock_list) == 0:
            for m in modules:
                if m['connected']:
                    recv_sock_list.append( m['socket'] )

        read_socks, write_socks, error_socks = select.select( recv_sock_list , [], [] )
        for s in read_socks:
            for m in modules:
                if m['socket'] == s:
                    r = m['socket'].recv(BUFSIZ)
                    if r != '':
                        reply = pickle.loads( r )
                        m['reply'] = reply
#                        debug_print( "sv_socks_thread", "reply from module " + m['name'] + " is '" + str(reply) + "'" )


for m in modules:
    m['socket'] = socket.socket( socket.AF_INET, socket.SOCK_STREAM )

    while m['connected'] != True:
        try:
            log_cprint( 'sv', "trying to connect module " + m['name'] )
            m['socket'].connect( (m['host'], m['port']) )
            m['socket'].settimeout( 5.0 ) # in secs
        except socket.error, msg:
            log_cprint( 'sv', 'error ' + str(msg[0]) + ': ' + str(msg[1]) )
            if m['host'] == 'localhost':
                if os.name == 'nt':
                    if m['pyversion'] == 3:
                        python = 'c:\\python33\\python.exe'
                    else:
                        python = 'c:\\python27\\python.exe'
                else:
                    if m['pyversion'] == 3:
                        python = '/usr/bin/python3'
                    else:
                        python = '/usr/bin/python'

                log_cprint( 'sv', "spawning " + m['name'] )
                m_pid = os.spawnl( os.P_NOWAIT, python, 'python', m['script'], m['host'], str(m['port']) )
                m['pid'] = m_pid
                log_cprint( 'sv', "pid = " + str(m_pid) )
                time.sleep( 3 )
            else:
                m['pid'] = 0
                log_cprint( 'sv', "cannot spawn because of not localhost, keep trying to connect" )
    #        sys.exit()
        else:
            m['connected'] = True
            log_cprint( 'sv', "sending HELO to " + m['name'] )
            request = (time.time(), 'HELO')
            m['socket'].sendall( pickle.dumps(request,2) )
            reply = pickle.loads( m['socket'].recv(BUFSIZ) )
            ost = reply[0][0] #overall spent time, module spent time
            mst = reply[0][1]
            ost = time.time() - ost
            if reply[1][0] == 'OK':
                log_cprint( 'sv', "HELO reply for " + m['name'] + " is '" + reply[1][1] + "'; overall spent time = " + str(ost) + ", module spent time = " + str(mst) )
                m['ready'] = True
            else:
                log_cprint( 'sv', "HELO error reply for " + m['name'] + " is '" + reply[1][1] + "'; overall spent time = " + str(ost) + ", module spent time = " + str(mst) )

            log_cprint( 'sv', "sending CALIBRATE to " + m['name'] )
            request = (time.time(), 'CALIBRATE')
            m['socket'].sendall( pickle.dumps(request,2) )
            reply = pickle.loads( m['socket'].recv(BUFSIZ) )
            ost = reply[0][0] #overall spent time, module spent time
            mst = reply[0][1]
            ost = time.time() - ost
            if reply[1][0] == 'OK':
#                log_cprint( 'sv', "CALIBRATE reply for " + m['name'] + " is '" + '{:0.3f} | {:0.3f} | {:0.3f}'.format(reply[1][1],reply[1][2],reply[1][3]) + "'; ost = " + str(ost) + ", mst = " + str(mst) )
                log_cprint( 'sv', "CALIBRATE reply for " + m['name'] + " is '" + str(reply[1]) + "'; ost = " + str(ost) + ", mst = " + str(mst) )
                m['ready'] = True
            else:
                log_cprint( 'sv', "CALIBRATE error reply for " + m['name'] + " is '" + reply[1][1] + "'; overall spent time = " + str(ost) + ", module spent time = " + str(mst) )

            m['reply'] = ''
    win.refresh()

thread.start_new_thread( socks_thread, () )

exiting = False
cycle_time = 0.05
sleep_time = 0.1
motor_step = 0.01
#f = open( "log.csv", "w" )
while (not exiting) or connected: #main cycle
    cycle_start = time.time()
    if not exiting:
        for m in modules:
            if m['connected']:
                if m['ready'] == True:
                    param = ''
                    if m['name'] == 'gyroer':
                        c = 'GETVEL'
                    elif m['name'] == 'acceler':
                        c = 'GETAXES'
                    elif m['name'] == 'soner':
                        c = 'GETDIST'
                    elif m['name'] == 'compasser':
                        c = 'GETHEADING'
                    elif m['name'] == 'mover':
                        c = 'SETALL'
                        param = motors
                    try:
                        log_cprint( 'sv', "sending command '" + c + "', " + str(param) + " to module " + m['name'] )
                        request = ( time.time(), c, param )
                        m['socket'].sendall( pickle.dumps(request,2) )
                        m['ready'] = False
                    except socket.error:
                        log_cprint( 'sv', "sending failed" )
                        sys.exit()
                    except socket.timeout:
                        log_cprint( 'sv', "timeout exception at sending '" + c + "' to module " + m['name'] )
                        sys.exit()
            
    time.sleep( sleep_time )
    connected = False
    for m in modules:
        if m['connected']:
            connected = True
            if m['reply'] != '':
                if m['name'] == 'gyroer':
                    if m['reply'][1][0] == 'OK':
                        if m['reply'][1][1] == 'EXITING':
                            log_cprint( 'sv', "closing socket for module " + m['name'] )
                            m['socket'].close
                            m['connected'] = False
                        else:
                            ost = m['reply'][0][0]
                            mst = m['reply'][0][1]
                            ost = time.time() - ost
#                               debug_cprint( m['name'], "(" + format(ost,"0.3f") + ";" + format(mst,"0.3f") + ") -> " + str(m['reply'][1][1]) + ' | ' + str(m['reply'][1][2]) + ' | ' + str(m['reply'][1][3]) )
                            d_alpha = m['reply'][1][1]
                            d_beta = m['reply'][1][2]
                            d_gamma = m['reply'][1][3]
                            alpha += d_alpha * cycle_time
                            beta += d_beta * cycle_time
                            gamma += d_gamma * cycle_time
                            debug_cprint( m['name'], '({:0.3f};{:0.3f}) -> {:0.3f} | {:0.3f} | {:0.3f} || {:0.3f} | {:0.3f} | {:0.3f}'.format(ost,mst,d_alpha,d_beta,d_gamma,alpha,beta,gamma) )
                    elif m['reply'][1][0] == 'ERR':
                        debug_cprint( m['name'], 'error recieved: ' + m['reply'][1][1] )
                    else:
                        debug_cprint( m['name'], 'unknown error recieved:' + str(m['reply']) )
                elif m['name'] == 'acceler':
                    if m['reply'][1][0] == 'OK':
                        if m['reply'][1][1] == 'EXITING':
                            log_cprint( m['name'], 'closing socket' )
                            m['socket'].close
                            m['connected'] = False
                        else:
                            ost = m['reply'][0][0]
                            mst = m['reply'][0][1]
                            ost = time.time() - ost
                            ax = m['reply'][1][1]
                            ay = m['reply'][1][2]
                            az = m['reply'][1][3] 
                            vx += ax * cycle_time * 9.8
                            vy += ay * cycle_time * 9.8
                            vz += az * cycle_time * 9.8
                            x += vx * cycle_time
                            y += vy * cycle_time
                            z += vz * cycle_time
                            debug_cprint( m['name'], '({:0.3f};{:0.3f}) -> {:0.3f} | {:0.3f} | {:0.3f} || {:0.3f} | {:0.3f} | {:0.3f}'.format(ost,mst,ax,ay,az,x,y,z) )
                            accel_alpha = math.atan2(az,ay) * 180 / math.pi
                            accel_beta = math.atan2(az,ax) * 180 / math.pi
                            debug_cprint( 'acceler_angles', '{:0.3f} | {:0.3f}'.format(accel_alpha,accel_beta) )
                    elif m['reply'][1][0] == 'ERR':
                        debug_cprint( m['name'], 'error recieved: ' + m['reply'][1][1] )
                    else:
                        debug_cprint( m['name'], 'unknown error recieved:' + str(m['reply']) )

                elif m['name'] == 'compasser':
                    if m['reply'][1][0] == 'OK':
                        if m['reply'][1][1] == 'EXITING':
                            log_cprint( m['name'], 'closing socket' )
                            m['socket'].close
                            m['connected'] = False
                        else:
                            ost = m['reply'][0][0]
                            mst = m['reply'][0][1]
                            ost = time.time() - ost
                            heading = m['reply'][1][1]
                            debug_cprint( m['name'], '({:0.3f};{:0.3f}) -> {:0.3f}'.format(ost,mst,heading) )
                    elif m['reply'][1][0] == 'ERR':
                        debug_cprint( m['name'], 'error recieved: ' + m['reply'][1][1] )
                    else:
                        debug_cprint( m['name'], 'unknown error recieved:' + str(m['reply']) )

                elif m['name'] == 'soner':
                    if m['reply'][1][0] == 'OK':
                        if m['reply'][1][1] == 'EXITING':
                            log_cprint( m['name'], 'closing socket' )
                            m['socket'].close
                            m['connected'] = False
                        else:
                            ost = m['reply'][0][0]
                            mst = m['reply'][0][1]
                            ost = time.time() - ost
                            height = m['reply'][1][1]
                            debug_cprint( m['name'], '({:0.3f};{:0.3f}) -> {:0.3f}'.format(ost,mst,height) )
                    elif m['reply'][1][0] == 'ERR':
                        debug_cprint( m['name'], 'error recieved: ' + m['reply'][1][1] )
                    else:
                        debug_cprint( m['name'], 'unknown error recieved:' + str(m['reply']) )

                m['reply'] = ''
                m['ready'] = True
    cycle_time = time.time() - cycle_start
    debug_cprint( 'sv', 'main cycle = ' + format(cycle_time,"0.3f") )
    key = stdscr.getch()
    if key != -1:
        log_cprint( 'sv', 'key detected = ' + str(key) )
    if key == 27: #ESC
        for m in modules:
            if m['pid'] != 0:
#                log_cprint( 'sv', 'killing module ' + m['name'] + ' (pid ' + str(m['pid']) + ')' )
#                os.kill( m['pid'], 1 )
                log_cprint( 'sv', 'sending EXIT to module ' + m['name'] )
                request = (time.time(), 'EXIT')
                m['socket'].sendall( pickle.dumps(request,2) )
        exiting = True
    elif key == ord('z'): # zeroing coordinates, velocities and motors
        vx,vy,vz,x,y,z,alpha,beta,gamma = 0,0,0,0,0,0,0,0,0
        for i in range(len(motors)):
            motors[i] = 0

#    elif key == ord('c'): # recalibrating
    elif key == ord('q'): # motors speed up
        for i in range(len(motors)):
            motors[i] += motor_step
    elif key == ord('a'): # motors slow down
        for i in range(len(motors)):
            motors[i] -= motor_step

    elif key == ord('w'): # motors speed up
        motors[0] += motor_step
    elif key == ord('s'): # motors slow down
        motors[0] -= motor_step

    elif key == ord('e'): # motors speed up
        motors[1] += motor_step
    elif key == ord('d'): # motors slow down
        motors[1] -= motor_step

    elif key == ord('r'): # motors speed up
        motors[2] += motor_step
    elif key == ord('f'): # motors slow down
        motors[2] -= motor_step

    elif key == ord('t'): # motors speed up
        motors[3] += motor_step
    elif key == ord('g'): # motors slow down
        motors[3] -= motor_step

    elif key == 258 or key == ord('.'): # down key / backward
        motors[0] += motor_step
        motors[1] -= motor_step
        motors[2] -= motor_step
        motors[3] += motor_step

    elif key == 259 or key == ord('l'): # up key / forward
        motors[0] -= motor_step
        motors[1] += motor_step
        motors[2] += motor_step
        motors[3] -= motor_step

    elif key == 260 or key == ord(','): # left key / strife left
        motors[0] += motor_step
        motors[1] += motor_step
        motors[2] -= motor_step
        motors[3] -= motor_step

    elif key == 261 or key == ord('/'): # right key / strife right
        motors[0] -= motor_step
        motors[1] -= motor_step
        motors[2] += motor_step
        motors[3] += motor_step

    elif key == ord('k'): # rot ccw
        motors[0] += motor_step
        motors[1] -= motor_step
        motors[2] += motor_step
        motors[3] -= motor_step

    elif key == ord(';'): # rot cw
        motors[0] -= motor_step
        motors[1] += motor_step
        motors[2] -= motor_step
        motors[3] += motor_step

    if heading > keep_heading + 20:
        if rotation != -1:
            motors[0] += rotscale*motor_step
            motors[1] -= rotscale*motor_step
            motors[2] += rotscale*motor_step
            motors[3] -= rotscale*motor_step
            rotation = -1
    elif heading < keep_heading - 20:
        if rotation != 1:
            motors[0] -= rotscale*motor_step
            motors[1] += rotscale*motor_step
            motors[2] -= rotscale*motor_step
            motors[3] += rotscale*motor_step
            rotation = 1
    else:
        if rotation == -1:
            motors[0] -= rotscale*motor_step
            motors[1] += rotscale*motor_step
            motors[2] -= rotscale*motor_step
            motors[3] += rotscale*motor_step
        elif rotation == 1:
            motors[0] += rotscale*motor_step
            motors[1] -= rotscale*motor_step
            motors[2] += rotscale*motor_step
            motors[3] -= rotscale*motor_step
        rotation = 0


    for i in range(len(motors)):
        if motors[i] < 0:
            motors[i] = 0
        elif motors[i] > 1:
            motors[i] = 1

#    f.write( str(sum(motors)/len(motors)) + ";" + str(height) + "," + str(heading) + "\n" )
    win.refresh()

curses.nocbreak()
stdscr.keypad(False)
curses.echo()
#f.close()
debug_print( 'sv', 'done' )
