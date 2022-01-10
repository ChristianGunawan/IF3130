import os

if __name__ == "__main__":
    os.system('python3 server.py 4434 ./files/spek.pdf')
    os.system('python3 client.py 4434 ./output/')
    os.system('python3 client.py 4434 ./output/')