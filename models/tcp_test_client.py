import socket
import numpy as np

HOST = "localhost"
PORT = 12345

CHANNELS = 32
SAMPLES_PER_PACKET = 18

PACKET_SIZE = CHANNELS * SAMPLES_PER_PACKET * 8

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

print("Connecting...")

client.connect((HOST, PORT))

print("Connected!")

buffer = b""

while True:
    data = client.recv(4096)

    if not data:
        print("Connection closed")
        break

    buffer += data

    while len(buffer) >= PACKET_SIZE:

        packet = buffer[:PACKET_SIZE]
        buffer = buffer[PACKET_SIZE:]

        signal = np.frombuffer(
            packet,
            dtype=np.float64
        ).reshape(CHANNELS, SAMPLES_PER_PACKET)

        print("Packet received")
        print("Shape:", signal.shape)
        print("Dtype:", signal.dtype)
        print("First value:", signal[0, 0])
        print("-" * 40)