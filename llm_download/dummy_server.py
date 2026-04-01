import time
import random

print("Starting server...")
for i in range(5):
    print(f"Initializing module {i}...")
    time.sleep(1)

print("Error: ConnectionRefusedError: [Errno 111] Connection refused")
print("    at /usr/lib/python3.10/socket.py:832 in create_connection")
print("    at /app/server.py:42 in connect_db")
print("CRITICAL: Database connection failed. Aborting.")
while True:
    time.sleep(10)
