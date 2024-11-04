import socket
import json
import threading
import time
import subprocess


def request_metrics_from_server(server_host='127.0.0.1', server_port=65432):
    while True:
        try:
            tcp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_client_socket.connect((server_host, server_port))
            message = "device_metrics"
            tcp_client_socket.send(message.encode())
            data = tcp_client_socket.recv(4096).decode()
            print("METRICS RECEIVED!\n", data)
        except Exception as e:
            print(f"[ERROR] An error occurred while communicating with the server: {e}")
        finally:
            tcp_client_socket.close()
        time.sleep(10)

def receive_udp_message_and_execute(client_host='0.0.0.0', client_port=0):
    udp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_client_socket.bind((client_host, client_port))
    client_address = udp_client_socket.getsockname()
    print(f"[CLIENT] Listening on {client_address[0]} : {client_address[1]}")
    while True:
        data, server_addr = udp_client_socket.recvfrom(4096)
        message = data.decode()
        print("MESSAGE RECEIVED FROM:", server_addr, ":", message)
        try:
            task = json.loads(message)
            execute_task(task)
        except json.JSONDecodeError:
            print("[ERROR] Invalid JSON received.")

def execute_task(task):
    device_id = task.get("device_id")
    print(f"EXECUTING TASK FOR DEVICE ID: {device_id}")
    device_metrics = task.get("device_metrics", {})
    if device_metrics:
        print("DEVICE METRICS:")
        for metric, enabled in device_metrics.items():
            print("-", metric, ":", "ACTIVATED" if enabled else "DEACTIVATED")
    if device_metrics.get('cpu_usage'):
        print("MONITORING CPU USAGE...")
        subprocess.run(["top", "-b", "-n", "1"])
    if device_metrics.get('ram_usage'):
        print("MONITORING RAM USAGE...")
        subprocess.run(["free", "-h"])

if __name__ == "__main__":
    metrics_thread = threading.Thread(target=request_metrics_from_server)
    metrics_thread.start()
    receive_udp_message_and_execute()