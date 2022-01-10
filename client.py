import sys
import socket
import random
from segmen import Segmen
from time import sleep

BROADCAST_ADDR = "<broadcast>"
SEGMEN_SIZE = 32780

class Client:
    def __init__(self, port, path):
        self.port = port
        self.path = path
        self.file = None
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def req_server(self):
        print("Client starting...")
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        print(f"Broadcasting to broadcast domain | PORT: {self.port}")
        self.socket.sendto(b"Requesting file", (BROADCAST_ADDR, self.port))
        
        # Three Way Handshake
        self.threewayhandshake()
        # Receiving file
        self.receive()
        # Closing connection
        self.close()
        self.socket.close()
    
    def threewayhandshake(self):
        prev_syn = False
        rand_seq = random.randint(0, 9999)
        while True:
            data, addr = self.socket.recvfrom(SEGMEN_SIZE)
            r_segmen = Segmen.construct_segmen(data)
            validate = r_segmen.check_checksum()
            f_segmen = Segmen(seq=r_segmen.seq+5, 
                ack=r_segmen.seq+5, flag="SYN4ACK").to_bytesformat()
            if (validate):
                if r_segmen.flag == "SYN":
                    print(f"[CLIENT] Received SYN, sending SYN-ACK")
                    self.socket.sendto(Segmen(
                        seq=rand_seq,
                        ack=r_segmen.seq+1,
                        flag="SYN4ACK"
                    ).to_bytesformat(), addr)
                    sleep(1)
                    prev_syn = True
                    data2, addr = self.socket.recvfrom(SEGMEN_SIZE)
                    r2_segmen = Segmen.construct_segmen(data2)
                    if r2_segmen.flag == "ACK" and r2_segmen.ack == (rand_seq+1):
                        print(f"[CLIENT] Valid ACK, three way handshake done")
                        break
                    else:
                        print("[CLIENT] Waiting for valid ACK")
                        continue
                elif r_segmen.flag == "ACK" and prev_syn:
                    if r_segmen.ack == (rand_seq + 1):
                        print(f"[CLIENT] Valid ACK, three way handshake done")
                        break
                    else:
                        prev_syn = False
                        self.socket.close()
                        print(f"[CLIENT] Closing socket, invalid ACK")
                        sys.exit()
                        # Close connection, second ACK received False
                else:
                    print(f"[CLIENT] Invalid flag, waiting for SYN or ACK")
                    self.socket.sendto(f_segmen, addr) # Send False SYN-ACK Segmen
                    prev_syn = False
            else:
                print(f"[CLIENT] Invalid checksum, sending false SYN-ACK")
                self.socket.sendto(f_segmen, addr) # Send False SYN-ACK Segmen
                prev_syn = False

    def receive(self):
        print(f"[CLIENT] Commencing file receive...")
        self.socket.settimeout(30)
        write_f = b""
        req_n = 0
        while True:
            data, addr = self.socket.recvfrom(SEGMEN_SIZE)
            r_segmen = Segmen.construct_segmen(data)
            if r_segmen.flag == "FIN":
                self.file = write_f

                print(f"[CLIENT] Received FIN, writing file")
                out_file = open(self.path, "wb")
                out_file.write(self.file)
                out_file.close()
                break
            if not r_segmen.check_checksum():
                print(f"[CLIENT] Checksum invalid, sending ACK")
                self.socket.sendto(Segmen(0, req_n, "ACK").to_bytesformat(), addr)
                continue
            if r_segmen.seq == req_n + 1:
                print(f"[Segmen SEQ={r_segmen.seq}] Received, sending ACK")
                req_n += 1
                write_f += r_segmen.data
                self.socket.sendto(Segmen(0, req_n, "ACK").to_bytesformat(), addr)
            else:
                print(f"[Segmen SEQ={r_segmen.seq}] Received, refused")
                self.socket.sendto(Segmen(0, req_n, "ACK").to_bytesformat(), addr)

    def close(self):
        self.socket.settimeout(2)
        data, addr = self.socket.recvfrom(SEGMEN_SIZE)
        r_segmen = Segmen.construct_segmen(data)
        if r_segmen.flag == "FIN4ACK":
            print(f"[CLIENT] Received FIN-ACK")
            print(f"[SEGMEN] SEQ={r_segmen.seq} ACK={r_segmen.ack}")

        sent_seq = r_segmen.ack
        sent_ack = r_segmen.seq + 1
        print(f"[CLIENT] Sending ACK")
        self.socket.sendto(Segmen(
            seq=sent_seq,
            ack=sent_ack,
            flag="ACK"
            ).to_bytesformat(), addr)
        # sleep(0.5)

        print(f"[CLIENT] Sending FIN-ACK")
        self.socket.sendto(Segmen(
            seq=sent_seq,
            ack=sent_ack,
            flag="FIN4ACK"
            ).to_bytesformat(), addr)

        data2, addr2 = self.socket.recvfrom(SEGMEN_SIZE)
        r2_segmen = Segmen.construct_segmen(data2)
        if r2_segmen.flag == "ACK" and r2_segmen.seq == sent_ack \
            and r2_segmen.ack == sent_seq + 1:
            print(f"[CLIENT] Received Final ACK")
            print(f"[CLIENT] Closing connection with server")
            self.socket.close()
        return

if __name__ == "__main__":
    PORT = int(sys.argv[1]) # Isi PORT (4433)
    PATH = sys.argv[2] # Isi path save file
    client = Client(PORT, PATH)
    client.req_server()