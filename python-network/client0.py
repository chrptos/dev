import socket

HOST = "localhost"
PORT = 50000
BUFSIZE = 4049

# IPv4とTCPを利用
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

client.connect((HOST, PORT))

data = client.recv(BUFSIZE)

# pythonではutf-8が利用されるので、server側もutf-8を利用している前提で実装する。
print(data.decode("UTF-8"))

client.close()