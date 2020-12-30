import argparse
import binascii
import socket
import threading
from threading import Timer
import sys
import termios
import atexit
from select import select

stop_threads=False
OFFER_PREFIX=b'feedbeef02'

def start_client(team_name):
    global stop_threads
    while True:
        server_address, tcp_port = searchForServer()
        sock = connectToServer(server_address,tcp_port)
        startGame(sock,team_name)
        stop_threads=False
def connectToServer(server_address, tcp_port):
    #print('trying to connect')
    print(f'Received offer from {server_address}, attempting to connect...')
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientSocket.connect((server_address, tcp_port))
    #print(f'connected to {server_address}')
    return clientSocket
def recieveData(sock):
    try:
        msg = sock.recv(2048)
        print(decode(msg))
    except:
        print('problem with the socket')
    finally:
        return
def listener_func (sock):
    kb=KBHit()
    global stop_threads
    while True:
        if kb.kbhit():
            c = kb.getch()
            try:
                sock.send(encode(c))
            except:
                print('server socket close')
                break
        if stop_threads:
            break
def stop():
    global stop_threads
    stop_threads=True
def startGame(sock,team_name):
    global stop_threads
    sock.send(encode(f'{team_name}\n'))
    recieveData(sock)
    listener_thread=threading.Thread(target=listener_func,args=(sock,),name='KB listener')
    listener_thread.start()
    Timer(10,stop).start()
    listener_thread.join()
    #print('finish keyboard')
    recieveData(sock)
    sock.close()
    print('Server disconnected, listening for offer requests...')
    return
def searchForServer(udp_port=13117):
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)  # UDP
    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    # Enable broadcasting mode
    client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    client.bind(("", udp_port))
    print ('Client started, listening for offer requests...')
    while True:
        data, (addr,port) = client.recvfrom(1024)
        if isOfferMessage(data):
            tcp_port = int(binascii.hexlify(data)[10:],16)
            #print(f'port:{tcp_port}')
            return addr,tcp_port
def isOfferMessage(data):
    return binascii.hexlify(data)[0:10].__eq__(OFFER_PREFIX)
#region Encode/Decode
def encode(string)->bytearray:
    return string.encode('utf-8')

def decode(data)->str:
    msg = None
    try:
        msg = data.decode('utf-8')
    except Exception:
        try:
            msg = data.decode('ascii')
        except Exception:
            try:
                msg = data.decode('utf-16')
            except Exception as e:
                print(e)
    finally:
        return msg
#endregion
#region Utils
class KBHit:

    def __init__(self):
        '''Creates a KBHit object that you can call to do various keyboard things.
        '''

        # Save the terminal settings
        self.fd = sys.stdin.fileno()
        self.new_term = termios.tcgetattr(self.fd)
        self.old_term = termios.tcgetattr(self.fd)

        # New terminal setting unbuffered
        self.new_term[3] = (self.new_term[3] & ~termios.ICANON & ~termios.ECHO)
        termios.tcsetattr(self.fd, termios.TCSAFLUSH, self.new_term)

        # Support normal-terminal reset at exit
        atexit.register(self.set_normal_term)


    def set_normal_term(self):
        ''' Resets to normal terminal.  On Windows this is a no-op.
        '''
        termios.tcsetattr(self.fd, termios.TCSAFLUSH, self.old_term)


    def getch(self):
        ''' Returns a keyboard character after kbhit() has been called.
            Should not be called in the same program as getarrow().
        '''

        s = ''
        return sys.stdin.read(1)


    def getarrow(self):
        ''' Returns an arrow-key code after kbhit() has been called. Codes are
        0 : up
        1 : right
        2 : down
        3 : left
        Should not be called in the same program as getch().
        '''
        c = sys.stdin.read(3)[2]
        vals = [65, 67, 66, 68]
        return vals.index(ord(c.decode('utf-8')))


    def kbhit(self):
        ''' Returns True if keyboard character was hit, False otherwise.
        '''
        dr,dw,de = select([sys.stdin], [], [], 0)
        return dr != []
#endregion

def args_parsing():
    #Parsing arguments
    parser = argparse.ArgumentParser(description='Tread Per client version for battle royal')
    parser.add_argument('-name',type=str,action="store",default='o_o Packet Sniffers O_O ¯\_( ͡❛ ͜ʖ ͡❛)_/¯ ',required=False,help='server ip')
    args = parser.parse_args()
    return args
if __name__=='__main__':
    #args = sys.argv[1:]
    args = args_parsing()
    if args.name is None:
        print('missing team name')
        sys.exit(1)
    start_client(args.name)