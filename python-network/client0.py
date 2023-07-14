import socket

HOST = "localhost"
PORT = 50000
BUFSIZE = 4049

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))
data = client.recv(BUFSIZE)
print(data.decode("UTF-8"))
client.close()