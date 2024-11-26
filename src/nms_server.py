import socket
import json
import threading
import random
import select
import os
from NetTask import *
from DataBlocks import *
from Task import *

#import pdb; pdb.set_trace()


class Server:
    def __init__(self, port, task_file_path):
        self.port = port
        self.task_interpreter = TaskInterpreter(task_file_path)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.settimeout(2)
        self.lock = threading.Lock()
        self.agent_registry = {}
        self.address_to_agent_id = {}
        self.agent_data = {}
        

    def start(self):
        try:
            self.server_socket.bind(('0.0.0.0', self.port))
            #self.server_socket.listen(5)
            print(f"[NMS_SERVER] - [start]: SERVER STARTED ON PORT {self.port}")
            self.task_interpreter.load_tasks()
        except OSError as e:
            print(f"[NMS_SERVER] - [start]: FAILED TO START SERVER: {e}")
            return

        while True:
            try:
                
                self.assign_tasks()

                packet_stream, address = self.server_socket.recvfrom(1024)
                packet = NetTask.from_bytes(packet_stream)
                if packet.flags & SYN:
                    print(f"[NMS_SERVER] - [start]: NEW CONNECTION FROM {address}")
                    agent_id = packet.payload.decode("utf-8")
                    self.agent_registry[agent_id] = (address, random.randint(0, 100000), packet.seq_num)
                    self.address_to_agent_id[address] = agent_id
                    self.agent_data[agent_id] = []
                    print(f"Registered at {agent_id}:{self.agent_registry[agent_id]}")
                    flags = SYN
                    flags |= ACK
                    ack_packet = NetTask(seq_num=self.agent_registry[agent_id][1], ack_num=self.agent_registry[agent_id][2], flags=flags)
                    ack_stream = ack_packet.to_bytes()
                    print("Sending " + str(ack_stream))
                    self.server_socket.sendto(ack_stream, address)
                else:
                    self.receive_data_from_agent(packet, address)
            except Exception as e:
                print("Something went wrong: " + str(e))


    def receive_data_from_agent(self, packet, address):
        print("inside receive data")
        if packet.flags & REPORT:
            print("is report")
            agent_id = self.address_to_agent_id[address]
            self.agent_data[agent_id].append(packet)

    def send_packet(self, packet_stream, address, max_retries = 10):
        retries = 0
        while retries < max_retries:
            try:
                self.server_socket.sendto(packet_stream, address)
                while True:
                    print("waiting for response...")
                    response, address_r = self.server_socket.recvfrom(1024)

                    packet = NetTask.from_bytes(response)
                    
                    if address_r != address:
                        self.receive_data_from_agent(packet, address_r)
                    
                    elif packet.flags & ACK:
                        print("Got ack")
                        #increase sequence and acknowledge numbers?
                        return True
                    
                    elif packet.flags & ERR:
                        retries += 1
                        break

            except socket.timeout:
                retries += 1

            except socket.error:
                retries += 1

    
    def assign_tasks(self):
        agents = self.agent_registry.keys()
        for a in agents:
            tasks = self.task_interpreter.devices_with_tasks.get(a, None)
            if tasks == None:
                continue
            else:
                address, seq, ack = self.agent_registry[a]
                while tasks:
                    t = tasks.pop()
                    payload = t.to_bytes()
                    packet = NetTask(seq, ack, TASK, t.task_id, payload)
                    self.send_packet(packet.to_bytes(), address)


if __name__ == "__main__":
    task_file_path = "tasks2.json"
    PORT = 65432

    server = Server(PORT, task_file_path)
    print("[NMS_SERVER] - [main]: INITIALIZING SERVER...")
    server.start()
