import socket
import json
import threading
import time
import random
from NetTask import *


class Agent:
    def __init__ (self, agent_id = "", server_address = "0.0.0.0", server_port = 0):
        self.agent_id = agent_id
        self.s_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.seq_number = random.randint(0, 1000000) #any works, just for safety
        self.ack_number = 0

        self.s_socket.settimeout(2.0)

        self.s_address = server_address
        self.s_port = server_port
    

    def init_connection(self):
        try:
            self.s_socket.connect((self.s_address, self.s_port))
        except Exception as e:
            self.s_socket.close()
            print(f"Failed to connect to {self.s_address}:{self.s_port}.")
            return False
        
        agent_id_length = len(self.agent_id)
        payload = struct.pack('!h', agent_id_length)
        payload += self.agent_id.encode("utf-8")
        packet = NetTask(self.seq_number, self.ack_number, SYN, payload)
        packet_stream = packet.to_bytes
        try:
            self.s_socket.send(packet_stream)
        except Exception as e:
            self.s_socket.close()
            print(f"Failed to send SYN packet to {self.s_address}:{self.s_port}")
            return False
        
        while(True):
            try:
                buffer = self.s_socket.recv(100) #the maximum is 83, set to 100 for convenience
                received_packet = NetTask.from_bytes(buffer)
                if received_packet.flags & ACK:
                    #check seq number, see if packet valid, etc.
                    return True
                else:
                    self.init_connection()
            except:
                self.init_connection()

    def process_packet(packet_stream):
        packet = NetTask.from_bytes(packet_stream)

    def collect_metrics():
        metrics = {
            "cpu_usage": 45,
            "ram_usage": 70
        }
        print(f"[NMS_AGENT] - [collect_metrics]: COLLECTED METRICS: {metrics}")
        return metrics
    
    def run(self):
        allgood = self.init_connection()
        if not allgood:
            return None
        
        while(True):
            return None

        



def send_metrics_():
    while True:
        metrics = collect_metrics()
        packet = NetTask(seq_num=1, ack_num=0, flags=DATA)
        packet.prepare_metrics_payload(metrics)
        server_socket.sendall(packet.to_bytes())
        print(f"[NMS_AGENT] - [send_metrics_periodically]: SENT METRICS TO SERVER")
        time.sleep(interval)

def get_ip_address():
    while True:
        ip_address = input("What is the server address: ")
        # Basic validation for IP address format
        parts = ip_address.split(".")
        if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
            return ip_address
        else:
            print("Invalid IP address format. Please try again.")

def get_port():
    while True:
        port = input("What's the server port: ")
        if port.isdigit() and 1 <= int(port) <= 65535:
            return int(port)
        else:
            print("Invalid port number. Please enter a number between 1 and 65535.")

def get_agent_id():
    id = input("Last but not least, what is this agent's id: ")
    return id

if __name__ == "__main__":
    address = get_ip_address()
    port = get_port()
    id = get_agent_id()

    agent = Agent(id, address, port)

    agent.run()

    '''
    if server_socket:
        threading.Thread(target=send_metrics_periodically, args=(server_socket,), daemon=True).start()
        while True:
            time.sleep(1)
    '''
