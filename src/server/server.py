import socket
import json
import threading
import os

class TaskInterpreter:
    
    def __init__(self, file_path):
        self.file_path = file_path
        self.devices = []
    
    def load_tasks(self):
        try:
            with open(self.file_path, 'r') as file:
                data = json.load(file)
                tasks = data.get('tasks', [])
                for task in tasks:
                    self.devices.extend(task.get("devices", []))
                print("[INFO] Devices successfully loaded.")
        except FileNotFoundError:
            print("[ERROR] File not found:", self.file_path)
        except json.JSONDecodeError:
            print("[ERROR] Failed to decode the JSON file.")
    
    def get_device_metrics(self, device_index):
        if not self.devices or device_index >= len(self.devices):
            return "[INFO] No device to process for this client."
        device = self.devices[device_index]
        device_id = device.get("device_id")
        device_metrics = device.get("device_metrics", {})
        alertflow_conditions = device.get("alertflow_conditions", {})
        device_info = f"Device: {device_id}\n"
        device_info += "  Metrics:\n"
        device_info += f"    - CPU Usage: {device_metrics.get('cpu_usage')}\n"
        device_info += f"    - RAM Usage: {device_metrics.get('ram_usage')}\n"
        device_info += f"    - Interface Stats: {device_metrics.get('interface_stats')}\n"
        device_info += "  Alert Conditions:\n"
        for condition, value in alertflow_conditions.items():
            device_info += f"    - {condition}: {value}\n"
        return device_info

class Server:

    def __init__(self, host, port, task_file_path):
        self.host = host
        self.port = port
        self.task_interpreter = TaskInterpreter(task_file_path)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lock = threading.Lock()
        self.client_map = {}

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"[SERVER] Server started and listening on {self.host}:{self.port}")
        self.task_interpreter.load_tasks()
        while True:
            client_socket, client_address = self.server_socket.accept()
            print(f"[CONNECTION] New connection from {client_address}")
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket, client_address))
            client_thread.start()

    def handle_client(self, client_socket, client_address):
        try:
            with self.lock:
                if client_address not in self.client_map:
                    # Assign a new device index if this client is new
                    self.client_map[client_address] = len(self.client_map)
            device_index = self.client_map[client_address]
            while True:
                device_info = self.task_interpreter.get_device_metrics(device_index)
                client_socket.send(device_info.encode())
                threading.Event().wait(10)
        except Exception as e:
            print(f"[ERROR] An error occurred with the connection: {e}")
        finally:
            client_socket.close()
            print(f"[CONNECTION] Client {client_address} disconnected.")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    task_file_path = os.path.join(current_dir, "..", "tasks.json")
    HOST = "127.0.0.1"
    PORT = 65432
    server = Server(HOST, PORT, task_file_path)
    server.start()