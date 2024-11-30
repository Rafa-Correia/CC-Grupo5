import socket
import json
import threading
import subprocess
import time
import random
import psutil
import re
import queue
from NetTask import *
from DataBlocks import *


class Agent:
    def __init__ (self, agent_id = "", server_address = "0.0.0.0", server_port = 0):
        self.agent_id = agent_id

        self.s_socket_NetTask = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s_socket_NetTask.bind(('0.0.0.0', 65432))
        self.s_socket_AlertFlow = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s_socket_AlertFlow.bind(('0.0.0.0', 23456))

        self.seq_number = random.randint(0, 1000000) #any works, just for safety
        self.ack_number = 0

        self.s_socket_NetTask.settimeout(2.0)

        self.s_address = server_address
        self.s_port = server_port
        self.s_info = (server_address, server_port)
        self.tasks = []

        self.m_queue = queue.Queue()

        self.lock = threading.Lock()
    
    def initialize_connection(self):
        payload = self.agent_id.encode("utf-8")
        packet = NetTask(seq_num=self.seq_number, ack_num=self.ack_number, flags=SYN,payload=payload)
        while True:
            try:
                print("Sending SYN packet...")
                self.s_socket_NetTask.sendto(packet.to_bytes(), self.s_info)
                response = self.s_socket_NetTask.recv(1024)
                response_packet = NetTask.from_bytes(response)
                flags = SYN
                flags |= ACK
                if response_packet.flags & flags:
                    print("Got a SYN+ACK response!")
                    self.ack_number=response_packet.seq_num
                    break
                
            except Exception as e:
                #print("Something went wrong: " + str(e))
                continue
        
        return True

    #SEND A PACKET AND WAIT FOR ACKNOWLEDGE, TRY AT MAX 10 TIMES
    def send_packet(self, packet_stream, max_retries = 10):
        retries = 0
        while retries < max_retries:
            try:
                self.s_socket_NetTask.sendto(packet_stream, self.s_info)

                while True:
                    response = self.s_socket_NetTask.recv(1024)
                    p_len = len(response)

                    packet = NetTask.from_bytes(response)
                    if packet.flags & ACK:
                        self.seq_number = packet.ack_num
                        self.ack_number = packet.seq_num
                        return True
                    
                    if packet.flags & ERR:
                        retries += 1
                        break

                    self.process_packet(packet, p_len)

            except socket.timeout:
                retries += 1

            except socket.error:
                retries += 1

    #PROCESS A PACKET
    def process_packet(self, packet, p_len):
        if packet.flags & ACK:
            #drop packet / do nothing
            #dropped because ack is after timeout (all acknowledges are supposed to be received at most 2 seconds after packet is sent)
            return True
        
        elif packet.flags & TASK:
            #print("Processing TASK!")
            self.seq_number = packet.ack_num

            task_id = packet.task_id
            if task_id not in self.tasks:
                self.tasks.append(task_id)
                #print("Now measuring metrics...")
                blocks = DataBlockServer.separate_packed_data(packet.payload)
                for block in blocks:
                    t = threading.Thread(target=Agent.collect_send_metrics, args=(self, task_id, block), daemon=True)
                    t.start()
                    

            self.ack_number = self.ack_number + p_len
            response = NetTask(self.seq_number, self.ack_number, ACK)
            #print("Sending acknowledge...")
            self.s_socket_NetTask.sendto(response.to_bytes(), self.s_info)
            #print("Done!")
            return True
        
        elif packet.flags & FIN:
            #finalize connection
            return True

        else:
            return True

    #COLLECT METRICS
    def collect_metrics(id, duration, client_mode=True, source_ip ="0.0.0.0", destination_ip="0.0.0.0"):
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
        #print("Collecting...")
        id = data_block.id
        #print(f"id is {id}")
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
                if metrics > data_block.max_value:
                    #alert
                    print("ALERT")
                    block = DataBlockClient(id, metrics)
                else:
                    block = DataBlockClient(id, metrics)

            block_stream = block.to_bytes()
            packet = NetTask(agent.seq_number, agent.ack_number, REPORT, task_id, block_stream)

            with agent.lock:
                agent.m_queue.put(packet)

            time.sleep(sleep_time)

    def run(self):
        self.initialize_connection()
        while True:
            try:
                while not self.m_queue.empty():
                    p = self.m_queue.get()
                    print(str(p.flags))
                    self.send_packet(p.to_bytes())
                packet_stream = self.s_socket_NetTask.recv(1024)
                p_len = len(packet_stream)
                packet = NetTask.from_bytes(packet_stream)
                self.process_packet(packet, p_len)
                packet = None
            except Exception as e:
                #print("Exception: " + str(e))
                continue

def get_ip_address():
    while True:
        ip_address = input("What is the server's address: ")
        # Basic validation for IP address format
        parts = ip_address.split(".")
        if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
            return ip_address
        else:
            print("Invalid IP address format. Please try again.")

def get_agent_id():
    id = input("Last but not least, what is this agent's id: ")
    return id

if __name__ == "__main__":
    address = get_ip_address()
    port = 65432
    id = get_agent_id()

    agent = Agent(id, address, port)

    agent.run()

    '''
    if server_socket:
        threading.Thread(target=send_metrics_periodically, args=(server_socket,), daemon=True).start()
        while True:
            time.sleep(1)
    '''
