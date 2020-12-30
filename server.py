import argparse
import binascii
import selectors
import threading
import time
import socket
import sys
from typing import List
#region Global Variables
Group_A_threads=[]          #will hold tuple of (threadObject,clientName)
Group_A_receive_chars=[]    #['a','b,'a',...]
Group_B_threads=[]          #will hold tuple of (threadObject,clientName)
Group_B_receive_chars=[]

Groups=[Group_A_threads,Group_B_threads]
Scores=[Group_A_receive_chars,Group_B_receive_chars]

Group_to_register=Group_A_threads
sockets=[]
StartFlag = False
#endregion

def init_Server(server_ip,tcp_port):
    global StartFlag
    payload = binascii.unhexlify(f'FEEDBEEF02{hex(tcp_port)[2:]}')
    UDP_socket = createUDPSocket()
    TCP_socket = createTCPSocket(server_ip, tcp_port)
    print(f'Server started, listening on IP address {server_ip}')
    while True:
        UDP_broadcast_thread = threading.Thread(target=UDP_broadcast, args=(UDP_socket, server_ip, payload),
                                                name='UDP thread')
        UDP_broadcast_thread.start()
        TCP_greeter(TCP_socket, server_ip, tcp_port)
        if len(sockets)<1:
            print('No connection has been made to the server, continue broadcasting...')
            continue
        sendBroadCastMessage(PrepareWelcomeMessage(),sockets)
        #print("Welcome message sent")
        StartFlag=True
        #print('Game started.')
        time.sleep(10)
        StartFlag = False
        #print('Stop pressing!!!')

        all_clients=Groups[0]+Groups[1]
        all_threads:List[threading.Thread]=[x[0] for x in all_clients]
        for thread in all_threads:
            if thread.isAlive():
                thread.join()

        WinnerMessage = GenerateWinningMessage(len(Scores[0]), len(Scores[1]))
        print(WinnerMessage)
        sendBroadCastMessage(WinnerMessage,sockets)
        #print("Winners message sent")

        ResetGame(sockets)
        print('Game Over, sending out offer requests...')

#region Sockets functions
def TCP_greeter(TCP_greeter_socket,server_ip,tcp_port):
    TCP_greeter_socket.listen()
    TCP_greeter_socket.setblocking(False)
    selector = selectors.DefaultSelector()
    selector.register(TCP_greeter_socket, selectors.EVENT_READ, data=None)

    #print('listening on', (server_ip, tcp_port))

    elapses = time.time() + 10
    i=0
    while time.time()<=elapses:
        events = selector.select(timeout=10)
        for key, mask in events:
            if key.data is None:
                conn, addr = accept_Handler(key.fileobj)
                registerClient(conn, addr, Groups[i % 2], Scores[i % 2])
                i = i+1
def UDP_broadcast(UDP_socket,server_ip,payload,destination_port=13117):
    ar=server_ip.split('.')
    ar[3]='255'
    broadcast_address='.'.join(ar)
    end_Broadcasting = time.time() + 10
    while time.time()<=end_Broadcasting:
        UDP_socket.sendto(payload,(broadcast_address,destination_port))
        time.sleep(1)
    #print('finish broadcast')
def createUDPSocket():
    UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    UDP_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    UDP_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    return UDP_socket
def createTCPSocket(server_ip,tcp_port):
    TCP_greeter_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    TCP_greeter_socket.bind(("", tcp_port))
    return TCP_greeter_socket
#endregion

#region Client Handling - Threading
def accept_Handler(sock):
    conn, addr = sock.accept()
    #print('accepted connection from', addr)
    conn.setblocking(False)
    return conn, addr
def registerClient(conn,addr,group_thread_list,group_char_list)->threading.Thread:
    sockets.append(conn)
    client_thread = threading.Thread(target=Handle_Client, args=(conn, addr,group_thread_list,group_char_list), name=f'Client {addr}',daemon=True)
    client_thread.start()
def Handle_Client(conn, addr,group_list,group_score):
    global StartFlag
    conn.setblocking(True)
    conn.settimeout(10)
    client_name = decode(conn.recv(1024))
    #print(client_name)
    group_list.append((threading.current_thread(),client_name))
    while not StartFlag:
        pass
    while StartFlag:
        try:
            data = conn.recv(1024)
            print(decode(data))
            group_score.append(data)
        except socket.timeout:
            continue
    conn.setblocking(False)
    return
#endregion

#region Messeages and broadcasts
def PrepareWelcomeMessage():
        groupA_names = [x[1] for x in Group_A_threads]
        groupB_names = [x[1] for x in Group_B_threads]
        msg = "Welcome to Keyboard Spamming Battle Royale.\nGroup 1:\n==\n"
        for name in groupA_names:
            msg = msg + name + '\n'
        msg = msg + "\nGroup 2:\n==\n"
        for name in groupB_names:
            msg = msg + name + '\n'
        msg = msg + "\nStart pressing keys on your keyboard as fast as you can!!"
        return msg
def GenerateWinningMessage(ScoreA,ScoreB):
    global Group_A_threads
    global Group_B_threads
    winner=None
    names=None
    #names = [x[1] for x in (Group_A_threads+Group_B_threads)]
    print(f'winning messages names:{names}')
    if ScoreA>ScoreB:
        winner='Group 1'
        names = [x[1] for x in Group_A_threads]

    else:
        winner='Group 2'
        names = [x[1] for x in Group_B_threads]

    message = f'Game over!\nGroup 1 typed in {ScoreA} characters. Group 2 typed in {ScoreB} characters.\n{winner} ' \
              f'wins!\nCongratulations to the winners:\n==\n'
    for name in names:
        message = message + name + '\n'
    return message
def sendBroadCastMessage(msg,sockets):
    for sock in sockets:
        #print(repr(sock))
        sock.sendall(encode(msg))
#endregion

#region utils
def ResetGame(clientSockets):
    global Group_A_threads
    global Group_A_receive_chars
    global Group_B_threads
    global Group_B_receive_chars
    global sockets
    for sock in clientSockets:
        sock.close()

    Group_A_threads = []
    Group_A_receive_chars = []
    Group_B_threads = []
    Group_B_receive_chars = []
    sockets=[]
def encode(str):
    return str.encode('utf-8')
def decode(data):
    msg=None
    try:
        msg= data.decode('utf-8')
    except Exception:
        try:
            msg=data.decode('ascii')
        except Exception:
            try:
                msg = data.decode('utf-16')
            except Exception as e:
                print(e)
    finally:
        return data.decode('utf-8')

#endregion
def args_parsing():
    #Parsing arguments
    parser = argparse.ArgumentParser(description='Tread Per client version for battle royal')
    parser.add_argument('-ip',type=str,action="store",default='10.100.102.35',required=False,help='server ip')
    parser.add_argument('-p',type=int,action="store",default=7777,required=False,help='tcp port to listen')
    args = parser.parse_args()
    return args

if __name__== '__main__':
    args=args_parsing()
    if args.ip is None or args.p is None:
        print('one missing arguments')
        sys.exit(1)
    init_Server(args.ip,args.p)
