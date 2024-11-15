import socket
import json
import threading
import subprocess
import time
import random
import psutil
import re
from NetTask import *
from DataBlocks import *


class Agent:
    def __init__ (self, agent_id = "", server_address = "0.0.0.0", server_port = 0):
        self.agent_id = agent_id
        self.s_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.seq_number = random.randint(0, 1000000) #any works, just for safety
        self.ack_number = 0

        self.s_socket.settimeout(2.0)

        self.s_address = server_address
        self.s_port = server_port
        self.tasks = {}
    

    def initialize_connection(self):
        payload = self.agent_id.encode("utf-8")
        packet = NetTask(self.seq_number, self.ack_number, SYN, 0, payload)
        while True:
            try:
                self.s_socket.sendall(packet.to_bytes())
                response = self.s_socket.recv(121)
                response_packet = NetTask.from_bytes(response)
                if response_packet.flags & (SYN & ACK):
                    self.ack_number=response_packet.seq_num
                    return True
            except:
                continue


    #SEND A PACKET AND WAIT FOR ACKNOWLEDGE, TRY AT MAX 10 TIMES
    def send_packet(self, packet_stream, max_retries = 10):
        retries = 0
        while retries < max_retries:
            try:
                self.s_socket.sendall(packet_stream)
                while True:
                    response = self.s_socket.recv(121)

                    packet = NetTask.from_bytes(response)
                    if packet.flags & ACK:
                        #increase sequence and acknowledge numbers?
                        return True
                    
                    if packet.flags & ERR:
                        retries += 1
                        break

                    self.process_packet(packet)

            except socket.timeout:
                retries += 1

            except socket.error:
                retries += 1

    #PROCESS A PACKET
    def process_packet(self, packet):
        if packet.flags & ACK:
            #drop packet / do nothing
            #dropped because ack is after timeout (all acknowledges are supposed to be received at most 2 seconds after packet is sent)
            return True
        
        elif packet.flags & TASK:
            self.seq_number = packet.ack_num

            task_id = packet.task_id
            blocks = DataBlockServer.separate_packed_data(packet.payload)
            for block in blocks:
                threading.Thread(target=Agent.collect_send_metrics, args=(self, task_id, block,), daemon=True).start()
            return True
        
        elif packet.flags & FIN:
            #finalize connection
            return True

        else:
            return True

    #COLLECT METRICS
    def collect_metrics(id, duration, client_mode, source_ip, destination_ip):
        if id == CPU:
            cpu_usage_float = psutil.cpu_percent(duration)
            cpu_usage = int(cpu_usage_float) #round down percentage
            return cpu_usage
        
        elif id == RAM:
            ram = psutil.virtual_memory()
            ram_percent_float = ram.percent
            ram_percent = int(ram_percent_float)
            return ram_percent
        
        elif id == INTERFACE:
            interface_names = psutil.net_if_addrs().keys()
            concatenated_names = ';'.join(interface_names) #join all interface names separated by ;
            return concatenated_names.encode('utf-8') #encode string to send
        
        elif id == BANDWIDTH:
            return Agent.get_from_iperf(id, duration, client_mode, source_ip, destination_ip, False)
            
        elif id == JITTER:
            return Agent.get_from_iperf(id, duration, client_mode, source_ip, destination_ip)
        
        elif id == LOSS:
            return Agent.get_from_iperf(id, duration, client_mode, source_ip, destination_ip)
            
    

    #GET RESULT FROM IPERF, BE IT BANDWIDTH JITTER OR LOSS (specified by ID)
    def get_from_iperf(id:int, duration, client_mode, source_ip, destination_ip, udp = True):
        command = ["iperf"]
        if client_mode:
            command += ["-c", destination_ip]
        
        else:
            command.append("-s")
        command += ["-t", str(duration)]
        if source_ip != "0.0.0.0":
            command += ["-B", source_ip]

        if udp:
            command.append("-u")
            command += ["-b", "10M"]
        
        try:
            result = subprocess.run(command, capture_output=True, text=True, check= True)
            output = result.stdout
        except:
            print("Could run iperf.")
            return None
        

        if id == BANDWIDTH:
            match = re.search(r"([\d.]+)\s(Gbits/sec|Mbits/sec)", output)
            if match:
                bandwidth = float(match.group(1))  # Bandwidth value
                unit = match.group(2)             # Unit (Mbits/sec or Gbits/sec)

                # Convert Gbits/sec to Mbits/sec if needed
                if unit == "Gbits/sec":
                    bandwidth *= 1000

                return bandwidth
            else:
                print("Could not parse Bandwidth from iperf output")
                return None
            
        elif id == JITTER:
            match = re.search(r"([\d.]+)\sms", output)
            if match:
                jitter = float(match.group(1))  # Extract the jitter value
                return jitter
            else:
                print("Could not parse Jitter from iperf output")
                return None
            
        elif id == LOSS:
            match = re.search(r"\(([\d.]+)%\)", output)
            if match:
                loss_percentage = float(match.group(1))  # Extract the loss percentage
                return loss_percentage
            else:
                print("Could not parse Loss Percentage from iperf output")
                return None
            
        else: 
            return None


    #GET METRICS AND SEND THEM TO SERVER
    def collect_send_metrics(agent, task_id, data_block):
        id = data_block.id
        frequency = data_block.frequency
        duration = data_block.duration
        sleep_time = frequency - duration #duration of measurement is allways expected to be smaller than frequency of measurement
        while True:
            metrics = Agent.collect_metrics(id, duration)
            if metrics == None:
                continue #nothing happens if cant measure
            

            if id == INTERFACE:
                block = DataBlockClient(id, data=metrics)
            else:
                block = DataBlockClient(id, metrics)

            block_stream = block.to_bytes()
            packet = NetTask(agent.seq_number, agent.ack_number, REPORT, task_id, block_stream)

            agent.send_packet(packet.to_bytes())

            time.sleep(sleep_time)

    

    def run(self):
        allgood = self.initialize_connection()
        if not allgood:
            return None
        while True:
            try:
                packet_stream = self.s_socket.recv(121)
                packet = NetTask.from_bytes(packet_stream)
                self.process_packet(packet)
            except:
                return None

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
