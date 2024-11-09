import socket
import json
import threading
import select
import os
from NetTask import NetTask, SYN, ACK, DATA

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
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.lock = threading.Lock()
        self.agent_registry = {}
        self.inputs = [self.server_socket]
        self.agent_data = {}

    def start(self):
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f"[NMS_SERVER] - [start]: SERVER STARTED AND LISTENING ON {self.host}:{self.port}")
            self.task_interpreter.load_tasks()
        except OSError as e:
            print(f"[NMS_SERVER] - [start]: FAILED TO START SERVER: {e}")
            return

        while True:
            readable, _, _ = select.select(self.inputs, [], [], 1)
            for s in readable:
                if s is self.server_socket:
                    client_socket, client_address = self.server_socket.accept()
                    print(f"[NMS_SERVER] - [start]: NEW CONNECTION FROM {client_address}")
                    self.inputs.append(client_socket)
                    self.register_agent(client_socket, client_address)
                else:
                    self.receive_data_from_agent(s)

    def register_agent(self, client_socket, client_address):
        try:
            registration_message = client_socket.recv(1024).decode('utf-8')
            if registration_message == "REGISTER":
                with self.lock:
                    self.agent_registry[client_address] = client_socket
                print(f"[NMS_SERVER] - [register_agent]: AGENT {client_address} REGISTERED SUCCESSFULLY")
                task = self.task_interpreter.assign_task_to_agent(client_address)
                client_socket.send(task.encode('utf-8'))
                print(f"[NMS_SERVER] - [register_agent]: TASK SENT TO AGENT {client_address}")
        except Exception as e:
            print(f"[NMS_SERVER] - [register_agent]: ERROR WITH AGENT {client_address}: {e}")

    def receive_data_from_agent(self, agent_socket):
        try:
            data = agent_socket.recv(4096)
            if data:
                packet = NetTask.from_bytes(data)
                if packet.flags & DATA:
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
    HOST = "127.0.0.1"
    PORT = 65432

    server = Server(HOST, PORT, task_file_path)
    print("[NMS_SERVER] - [main]: INITIALIZING SERVER...")
    server.start()
