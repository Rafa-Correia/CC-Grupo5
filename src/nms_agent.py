import socket
import json
import threading
import time
from NetTask import NetTask, SYN, ACK, DATA

def register_with_server(server_host='10.0.0.11', server_port=65432):
    try:
        tcp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_client_socket.connect((server_host, server_port))
        tcp_client_socket.send("REGISTER".encode('utf-8'))
        print(f"[NMS_AGENT] - [register_with_server]: SENT REGISTRATION REQUEST TO {server_host}:{server_port}")

        response = tcp_client_socket.recv(4096).decode('utf-8')
        print(f"[NMS_AGENT] - [register_with_server]: RECEIVED TASK FROM SERVER: {response}")
        return tcp_client_socket
    except Exception as e:
        print(f"[NMS_AGENT] - [register_with_server]: ERROR WHILE REGISTERING WITH SERVER: {e}")
        tcp_client_socket.close()
        return None

def collect_metrics():
    metrics = {
        "cpu_usage": 45,
        "ram_usage": 70
    }
    print(f"[NMS_AGENT] - [collect_metrics]: COLLECTED METRICS: {metrics}")
    return metrics

def send_metrics_periodically(server_socket, interval=10):
    while True:
        metrics = collect_metrics()
        packet = NetTask(seq_num=1, ack_num=0, flags=DATA)
        packet.prepare_metrics_payload(metrics)
        server_socket.sendall(packet.to_bytes())
        print(f"[NMS_AGENT] - [send_metrics_periodically]: SENT METRICS TO SERVER")
        time.sleep(interval)

def get_ip_address():
    while True:
        ip_address = input("Please enter a valid IP address: ")
        # Basic validation for IP address format
        parts = ip_address.split(".")
        if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
            return ip_address
        else:
            print("Invalid IP address format. Please try again.")

def get_port():
    while True:
        port = input("Please enter a port number (1-65535): ")
        if port.isdigit() and 1 <= int(port) <= 65535:
            return int(port)
        else:
            print("Invalid port number. Please enter a number between 1 and 65535.")           

if __name__ == "__main__":
    address = get_ip_address()
    port = get_port()
    server_socket = register_with_server()
    if server_socket:
        threading.Thread(target=send_metrics_periodically, args=(server_socket,), daemon=True).start()
        while True:
            time.sleep(1)
