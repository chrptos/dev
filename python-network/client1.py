import socket
import sys

HOST = "localhost"
PORT = 50000
BUFSIZE = 4049

# IPv4とTCPを利用
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

host = input("server:")
try:
    client.connect((host, PORT))
except:
    print("connection failed.")

msg = input("message:")
client.sendall(msg.encode("utf-8"))

data = client.recv(BUFSIZE)
print("receive message:")
print(data.decode("UTF-8"))

client.close()