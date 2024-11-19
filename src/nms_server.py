import socket
import json
import threading
import random
import select
import os
from NetTask import *

class TaskInterpreter:
    def __init__(self, file_path):
        self.file_path = file_path
        self.devices = []

    def load_tasks(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                tasks = data.get('tasks', [])
                print("[NMS_SERVER] - [load_tasks]: PARSING TASKS...\n")
                for task in tasks:
                    task_id = task.get("task_id", "UNKNOWN")
                    devices = task.get("devices", [])
                    print(f"[NMS_SERVER] - [load_tasks]: TASK ID: {task_id}")
                    for device in devices:
                        device_id = device.get("device_id", "UNKNOWN")
                        device_metrics = device.get("device_metrics", {})
                        alertflow_conditions = device.get("alertflow_conditions", {})

                        print(f"  [NMS_SERVER] - DEVICE ID: {device_id}")
                        print("    METRICS:")
                        for metric, status in device_metrics.items():
                            status_text = "ENABLED" if status else "DISABLED"
                            print(f"      - {metric.upper()}: {status_text}")

                        print("    ALERT CONDITIONS:")
                        for condition, value in alertflow_conditions.items():
                            print(f"      - {condition.upper()}: {value}")
                        print("\n")

                    self.devices.extend(devices)
                print("[NMS_SERVER] - [load_tasks]: TASKS LOADED SUCCESSFULLY.")
        except FileNotFoundError:
            print(f"[NMS_SERVER] - [load_tasks]: FILE NOT FOUND: {self.file_path}")
        except json.JSONDecodeError:
            print("[NMS_SERVER] - [load_tasks]: FAILED TO DECODE THE JSON FILE. CHECK THE FORMAT.")

    def assign_task_to_agent(self, agent_address):
        if not self.devices:
            print(f"[NMS_SERVER] - [assign_task_to_agent]: NO TASKS AVAILABLE TO ASSIGN TO {agent_address}")
            return "NO TASKS AVAILABLE"

        task = self.devices.pop(0)
        task_info = f"TASK ASSIGNED: {task.get('device_id')}"
        print(f"[NMS_SERVER] - [assign_task_to_agent]: {task_info} TO AGENT {agent_address}")
        return json.dumps(task)

class Server:
    def __init__(self, host, port, task_file_path):
        self.host = host
        self.port = port
        self.task_interpreter = TaskInterpreter(task_file_path)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.settimeout(2)
        self.lock = threading.Lock()
        self.agent_registry = {}
        self.agent_data = {}
        

    def start(self):
        try:
            self.server_socket.bind((self.host, self.port))
            #self.server_socket.listen(5)
            print(f"[NMS_SERVER] - [start]: SERVER STARTED AND LISTENING ON {self.host}:{self.port}")
            self.task_interpreter.load_tasks()
        except OSError as e:
            print(f"[NMS_SERVER] - [start]: FAILED TO START SERVER: {e}")
            return

        while True:
            try:
                packet_stream, address = self.server_socket.recvfrom(1024)
                packet = NetTask.from_bytes(packet_stream)
                if packet.flags & SYN:
                    print(f"[NMS_SERVER] - [start]: NEW CONNECTION FROM {address}")
                    agent_id = packet.payload.decode("utf-8")
                    self.agent_registry[address] = (agent_id, random.randint(0, 100000), packet.seq_num)
                    print(f"Registered at {address}:{self.agent_registry[address]}")
                    flags = SYN
                    flags |= ACK
                    ack_packet = NetTask(seq_num=self.agent_registry[address][1], ack_num=self.agent_registry[address][2], flags=flags)
                    ack_stream = ack_packet.to_bytes()
                    print("Sending " + str(ack_stream))
                    self.server_socket.sendto(ack_stream, address)
                else:
                    self.receive_data_from_agent(packet)
            except Exception as e:
                print("Something went wrong: " + str(e))


    def receive_data_from_agent(self, agent_socket):
        try:
            data = agent_socket.recv(4096)
            if data:
                packet = NetTask.from_bytes(data)
                if packet.flags & REPORT:
                    print(f"[NMS_SERVER] - [receive_data_from_agent]: RECEIVED METRICS FROM AGENT: {packet.payload.decode('utf-8')}")
                    self.agent_data[agent_socket] = packet.payload.decode('utf-8')
            else:
                print("[NMS_SERVER] - [receive_data_from_agent]: AGENT DISCONNECTED")
                self.inputs.remove(agent_socket)
                agent_socket.close()
        except Exception as e:
            print(f"[NMS_SERVER] - [receive_data_from_agent]: ERROR RECEIVING DATA: {e}")
            self.inputs.remove(agent_socket)
            agent_socket.close()

if __name__ == "__main__":
    task_file_path = "tasks.json"
    HOST = "10.0.0.10"
    PORT = 65432

    server = Server(HOST, PORT, task_file_path)
    print("[NMS_SERVER] - [main]: INITIALIZING SERVER...")
    server.start()
