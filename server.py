import sys
import socket
import platform
import random
from client import BROADCAST_ADDR
from segmen import Segmen
from time import sleep

# BROADCAST_ADDR = "255.255.255.255" if platform.system() == 'Linux' else str(
#     socket.getaddrinfo(host=socket.gethostname(),
#     port=None, family=socket.AF_INET)[0][4][0])
BROADCAST_ADDR = ""
SEGMEN_SIZE = 32780
MAX_DATA_SIZE = 32768

class Server:
    def __init__(self, port, path):
        self.port = port
        self.clients = []
        self.path = path
        self.file = self.get_file(path)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    def listen(self):
        self.socket.bind((BROADCAST_ADDR, self.port))
        print("Listening to broadcast address for clients.")
        inp = 'y'
        while inp == 'y':
            data, addr = self.socket.recvfrom(SEGMEN_SIZE)
            print(f"[!] Client ({addr[0]}:{addr[1]}) found")
            self.clients.append(addr)
            inp = str(input("[?] Listen more? (y/n): "))

        print(f"\n{len(self.clients)} clients found:")
        for i in range(len(self.clients)):
            addr = self.clients[i]
            print(f"{i+1}. {addr[0]}:{addr[1]}")
        print()

        segments, bytes_segments = self.file_to_segmen() # Segmented file
        print(f"[SERVER] Segmented input file {self.path} with size={len(self.file)}")

        # commence three way handshake for all addr
            # commence file transfer
        for address in self.clients: 
            self.threewayhandshake(address)
            self.send(address, bytes_segments)
            self.close(address)
            sleep(5)
    
    def threewayhandshake(self, addr):
        seq_n = random.randint(0, 9999) # Random seq Number
        while True:
            print(f"[SERVER] Sending SYN to {addr[0]}:{addr[1]}, waiting for SYN-ACK")
            self.socket.sendto(Segmen(
                seq=seq_n,
                ack=0,
                flag='SYN').to_bytesformat(), addr)
            sleep(1)
            print(f"[SERVER] (Sending SYN with SEQ Number = {seq_n})")
            
            data, addr = self.socket.recvfrom(SEGMEN_SIZE)
            seg_syn4ack = Segmen.construct_segmen(data)
            if not seg_syn4ack.check_checksum():
                print(f"[SERVER] Checksum failed, resending SYN")
                continue
            if seg_syn4ack.flag != 'SYN4ACK':
                print(f"[SERVER] Received flag {seg_syn4ack.flag}, resending SYN, waiting for SYN-ACK")
                continue
            if seg_syn4ack.ack != seq_n + 1:
                print(f"[SERVER] Invalid ACK received (received ACK={seg_syn4ack.ack}), resending SYN, waiting for SYN-ACK")
                continue
            print(f"[SERVER] Received SYN-ACK with Valid ACK, sending Final ACK")
            self.socket.sendto(Segmen(
                seq=0,
                ack=seg_syn4ack.seq+1,
                flag="ACK").to_bytesformat(), addr)
            sleep(1)
            print(f"[SERVER] Three way handshake completed")
            break


    def get_file(self, path):
    # Mengembalikan bytes file
        try:
            input_file = open(path, "rb")
            return input_file.read()
        except:
            print(f"[SERVER] File {path} not found! Try another path")
            sys.exit()

    def file_to_segmen(self):
    # Mengembalikan array berisi segmen-segmen dari file (dalam format bytes)
        segments = [] # List of Segmen classes to send
        bytes_segments = [] # List of Segmen in bytes format
        data = self.file
        for i in range(0, len(data), MAX_DATA_SIZE):
            if i + MAX_DATA_SIZE > len(data):
                data_s = data[i:]
            else:
                data_s = data[i:i+MAX_DATA_SIZE]
            seq_n = (i // MAX_DATA_SIZE) + 1
            segmen = Segmen(
                    seq = seq_n, # Seq Number
                    ack = 0, # Ack Number
                    flag = "DATA",
                    data = data_s
                )
            segments.append(segmen)
            bytes_segments.append(segmen.to_bytesformat())
        
        return (segments, bytes_segments)

    def send(self, addr, segmen_bytes):
        print(f"[SERVER] Commencing file transfer...")
        window_size = 4
        sendx = True
        seq_base = 0 # seq = 1
        seq_max = window_size
        while True:
            if (sendx):
                for i in range(window_size):
                    self.socket.sendto(segmen_bytes[i+seq_base], addr)
                    print(f"[SEGMEN SEQ={i+seq_base+1}] Sent")
                    # sleep(0.5)
                sendx = False
            try:
                data, addrs = self.socket.recvfrom(SEGMEN_SIZE)
            except:
                print(f"[SERVER] Socket timed out, sending to next client/stopping file transfer")
                break
            r_segmen = Segmen.construct_segmen(data)
            if r_segmen.check_checksum():
                if r_segmen.ack < seq_base:
                    print(f"[SEGMEN SEQ={r_segmen.ack}] NOT ACKED. Duplicate ACK Found")
                    print(f"[SERVER] Commencing Go-Back-N ARQ")
                    sendx = True
                    seq_base = r_segmen.ack
                    seq_max = seq_base + window_size
                    continue
                else:
                    if r_segmen.ack == len(segmen_bytes):
                        print(f"[SEGMEN SEQ={len(segmen_bytes)}] Final ACK received, sending FIN")
                        print(f"Closing connection with {addr[0]}:{addr[1]}...")
                        # Call close connection
                        break
                    else:
                        print(f"[SEGMEN SEQ={r_segmen.ack}] ACKED")
                        if seq_max < len(segmen_bytes):
                            self.socket.sendto(segmen_bytes[seq_max], addr)
                            print(f"[SEGMEN SEQ={seq_max+1}] Sent")
                            seq_base += 1
                            seq_max += 1
                        # sleep(0.5)
            else:
                print(f"[SEGMEN] Checksum failed, commencing Go-Back-N ARQ")
                sendx = True
    
    def close(self, addr):
        self.socket.sendto(Segmen(0, 0, "FIN").to_bytesformat(), addr)

        rand_seq = random.randint(0, 9999) # Random seq number
        sent_ack = len(self.file) // MAX_DATA_SIZE
        self.socket.sendto(Segmen(rand_seq, sent_ack, "FIN4ACK").to_bytesformat(), addr)

        ack, addrs = self.socket.recvfrom(SEGMEN_SIZE)
        r_seg = Segmen.construct_segmen(ack)
        if r_seg.flag == "ACK" and r_seg.seq == sent_ack \
            and r_seg.ack == rand_seq + 1:
            print(f"[SERVER] Received ACK SEQ={r_seg.seq} ACK={r_seg.ack}")

        finack, addrs = self.socket.recvfrom(SEGMEN_SIZE)
        r2_seg = Segmen.construct_segmen(finack)
        if r2_seg.flag == "FIN4ACK" and r2_seg.seq == sent_ack \
            and r2_seg.ack == rand_seq + 1:
            print(f"[SERVER] Received FIN-ACK SEQ={r2_seg.seq} ACK={r2_seg.ack}")

        self.socket.sendto(Segmen(
            seq=r2_seg.ack,
            ack=r2_seg.seq+1,
            flag="ACK"
        ).to_bytesformat(), addr)
        

if __name__ == "__main__":
    PORT = int(sys.argv[1]) # Isi PORT (4433)
    PATH = sys.argv[2] # Isi path ke file
    server = Server(PORT, PATH)
    server.listen()