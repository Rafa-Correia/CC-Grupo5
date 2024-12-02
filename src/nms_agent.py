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
from AlertFlow import *
from DataBlocks import *

class MetricCollector(threading.Thread):
    def __init__(self, agent, task_id, data_block):
        #print("b4 super init")
        super().__init__()
        #print("after super init")
        self.agent = agent
        self.task_id = task_id
        self.data_block = data_block

        self.stop_event = threading.Event()

        #print("Metric collector created!")

    def run(self):
        #print("Collecting...")
        id = self.data_block.id
        #print(f"id is {id}")
        frequency = self.data_block.frequency
        duration = self.data_block.duration
        sleep_time = frequency - duration #duration of measurement is allways expected to be smaller than frequency of measurement
        sv_id = -1
        if self.data_block.id == BANDWIDTH or self.data_block.id == JITTER or self.data_block.id == LOSS:
            sv_id = agent.open_server_id 
            sv_inf = agent.open_server_info.get(sv_id, None)
            if sv_inf == None:
                agent.open_server_info[sv_id] = None

            agent.open_server_id+=1
            
            
        while not self.stop_event.is_set():
            #print(f"Collecting {id}...")
            metrics = MetricCollector.collect_metrics(id, duration, True, self.data_block.source_ip, self.data_block.destination_ip, agent, sv_id)
            if metrics == None:
                continue #nothing happens if cant measure

            if id == CPU or id == RAM or id == JITTER or id == LOSS:
                if metrics > self.data_block.max_value:
                    #alert
                    print("ALERT")
                    #send through alertflow
                    time.sleep(sleep_time)
                    continue
                else:
                    block = DataBlockClient(id, metrics)

            elif id == INTERFACE:
                block = DataBlockClient(id, data=metrics)

            elif id == BANDWIDTH:
                block = DataBlockClient(id, metrics)


            block_stream = block.to_bytes()
            packet = NetTask(agent.seq_number, agent.ack_number, REPORT, self.task_id, block_stream)

            with agent.lock:
                agent.m_queue.put((packet, agent.s_info_NetTask, None, False))

            time.sleep(sleep_time)

    def stop(self):
        self.stop_event.set()

    #================================================================================
    #                                METRIC COLLECTION
    #================================================================================
    def collect_metrics(id, duration, client_mode=True, source_ip ="0.0.0.0", destination_ip="0.0.0.0", agent = None, sv_id = -1):
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
            interface_pps_list = []
            interface_names = psutil.net_if_addrs().keys()
            for i in interface_names:
                #measure all pps
                continue
            concatenated_names = ';'.join(interface_names) #join all interface names separated by ;
            return concatenated_names.encode('utf-8') #encode string to send
        
        elif id == BANDWIDTH:
            return MetricCollector.get_from_iperf(id, duration, client_mode, source_ip, destination_ip, False, agent, sv_id)
            
        elif id == JITTER:
            return MetricCollector.get_from_iperf(id, duration, client_mode, source_ip, destination_ip, True, agent, sv_id)
        
        elif id == LOSS:
            return MetricCollector.get_from_iperf(id, duration, client_mode, source_ip, destination_ip, True, agent, sv_id)
        
        elif id == LATENCY:
            #measure latency using ping?
            return 1
            
    

    #================================================================================
    #                                   RUN IPERF
    #================================================================================
    def get_from_iperf(id:int, duration, client_mode, source_ip, destination_ip, udp = True, agent = None, sv_id = -1):
        with agent.lock:
            sv_inf = agent.open_server_info[sv_id]
        if sv_inf == None:
            d_block = DataBlockClient(OPEN, 0, socket.inet_aton(destination_ip), udp)
            request_open = NetTask(flags=REQ, payload=d_block.to_bytes())
            add = (destination_ip, 65432)
            q = queue.Queue()
            agent.m_queue.put((request_open, add, q, False))
            response = q.get()
                    
            sv_inf = (destination_ip, str(response.task_id))
            with agent.lock:
                agent.open_server_info[sv_id] = sv_inf
        
        
        
        command = ["iperf"]
        if client_mode:
            command += ["-c", sv_inf[0], "-p", sv_inf[1]]
        
        else:
            command.append("-s")
        command += ["-t", str(duration)]
        if source_ip != "0.0.0.0":
            command += ["-B", source_ip]

        if udp:
            command.append("-u")
            command += ["-b", "10M"]
        
        try:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check= True)
            if result.returncode!=0:
                error = result.stderr
                #print(f"Error is: {error}")
                return None
            else:
                output = result.stdout
                #print(output)
        except Exception as e:
            #print(f"Couldn't run iperf: {str(e)}")
            return None
        

        if id == BANDWIDTH:
            match = re.search(r"([\d.]+)\s(Gbits/sec|Mbits/sec)", output)
            if match:
                bandwidth = float(match.group(1))  # Bandwidth value
                unit = match.group(2)             # Unit (Mbits/sec or Gbits/sec)

                # Convert Gbits/sec to Mbits/sec if needed
                if unit == "Gbits/sec":
                    bandwidth *= 1000

                return int(bandwidth)
            else:
                #print("Could not parse Bandwidth from iperf output")
                return 0
            
        elif id == JITTER:
            match = re.search(r"([\d.]+)\sms", output)
            if match:
                jitter = float(match.group(1))  # Extract the jitter value
                return int(jitter)
            else:
                #print("Could not parse Jitter from iperf output")
                return 0
            
        elif id == LOSS:
            match = re.search(r"\(([\d.]+)%\)", output)
            if match:
                loss_percentage = float(match.group(1))  # Extract the loss percentage
                return int(loss_percentage)
            else:
                #print("Could not parse Loss Percentage from iperf output")
                return 0
            
        else: 
            return None

class IperfThread(threading.Thread):
    def __init__(self, port, ip, udp_mode):
        super.__init__()
        self.port = port
        self.ip = ip
        self.udp_mode = udp_mode

        self.iperf_process = None

        self.stop_event = threading.Event()

    def run(self, port, ip, udp_mode):
        try:
            command=["iperf", "-s", "-p", str(port), "-B", ip]
            #print(f"Running following command: {command}")
            if udp_mode:
                command.append("-u")

            self.iperf_process = subprocess.Popen(command)

            while not self.stop_event.is_set():
                time.sleep(1)
        finally:
            self.iperf_process.terminate()
            self.iperf_process.wait()



    def open_iperf_server(port, ip, udp_mode):
        command=["iperf", "-s", "-p", str(port), "-B", ip]
        #print(f"Running following command: {command}")
        if udp_mode:
            command.append("-u")
            
        subprocess.run(command)

class Agent:
    def __init__ (self, agent_id = "", server_address = "0.0.0.0"):
        self.agent_id = agent_id

        self.s_socket_NetTask = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s_socket_NetTask.bind(('0.0.0.0', 65432))

        self.s_socket_AlertFlow = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s_socket_AlertFlow.bind(('0.0.0.0', 23456))

        self.seq_number = random.randint(0, 1000000) #any works, just for safety
        self.ack_number = 0

        self.s_socket_NetTask.settimeout(2.0)
        self.s_socket_AlertFlow.settimeout(2.0)

        self.s_info_NetTask = (server_address, 65432)
        self.s_info_AlertFlow = (server_address, 23456)
        self.tasks = []

        self.m_queue = queue.Queue()

        self.lock = threading.Lock()
    
        
        self.iperf_port_counter = 5001
        self.open_server_id = 0
        self.open_server_info = {}

        self.threads = []

        self.running = True
    

    #================================================================================
    #                        INITIALIZE CONNECTION WITH SERVER
    #================================================================================

    def initialize_connection(self):
        payload = self.agent_id.encode("utf-8")
        packet = NetTask(seq_num=self.seq_number, ack_num=self.ack_number, flags=SYN,payload=payload)
        while True:
            try:
                #print("Sending SYN packet...")
                self.s_socket_NetTask.sendto(packet.to_bytes(), self.s_info_NetTask)
                response = self.s_socket_NetTask.recv(1024)
                response_packet = NetTask.from_bytes(response)
                flags = SYN
                flags |= ACK
                if response_packet.flags & flags:
                    #print("Got a SYN+ACK response!")
                    self.ack_number=response_packet.seq_num
                    break
                
            except Exception as e:
                #print("Something went wrong: " + str(e))
                continue
        
        return True



    #================================================================================
    #                               SEND NETTASK PACKET
    #================================================================================
    def send_packet_NetTask(self, packet_stream, max_retries = 100, address = None):
        add = address if address != None else self.s_info_NetTask
        retries = 0
        while retries < max_retries:
            #print(f"Sending packet to {add}...")
            try:
                self.s_socket_NetTask.sendto(packet_stream, add)

                while True:
                    response, add = self.s_socket_NetTask.recvfrom(1024)
                        
                    #print("Whoopee! Inside send_packet processing packet!")
                    
                    p_len = len(response)
                    #print("Got response!")
                    packet = NetTask.from_bytes(response)
                    #print(f"Flags are: {packet.flags}")
                    if packet.flags & ACK:
                        #print("Is ack!")
                        if packet.seq_num != 0 and packet.ack_num != 0:
                            self.seq_number = packet.ack_num
                            self.ack_number = packet.seq_num
                        return packet
                    if packet.flags & ERR:
                        retries += 1
                        break
                    self.process_packet(packet, p_len, add)

            except socket.timeout:
                retries += 1

            except socket.error:
                retries += 1
                
            return None



    #================================================================================
    #                             SEND ALERTFLOW PACKET
    #================================================================================
    def send_packet_AlertFlow():
        return



    #================================================================================
    #                              PROCESS NETTASK PACKET
    #================================================================================
    def process_packet(self, packet, p_len, address):
        #print("Processing packet")
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
                    print("Trying to create a metric collector!")
                    t = MetricCollector(self, task_id, block)
                    t.start()
                    self.threads.append(t)
                    

            self.ack_number = self.ack_number + p_len
            response = NetTask(self.seq_number, self.ack_number, ACK)
            #print("Sending acknowledge...")
            self.s_socket_NetTask.sendto(response.to_bytes(), self.s_info_NetTask)
            #print("Done!")
            return True
        
        elif packet.flags & REQ:
            #print("Got a request!")
            open_requests = DataBlockClient.separate_packed_data(packet.payload)
            b = open_requests[0]
            ip = socket.inet_ntoa(b.data)
            t = IperfThread(self.iperf_port_counter, ip, b.udp_mode)
            t.start()
            self.threads.append(t)
            #print("Thread started!")
            
            ack_packet = NetTask(0, 0, ACK, self.iperf_port_counter)
            #print(f"Sending ack to {address} with flags: {ack_packet.flags}!")
            self.s_socket_NetTask.sendto(ack_packet.to_bytes(), address)
            
            self.iperf_port_counter += 1
            #print(f"Port incremented to {self.iperf_port_counter}!")          
            return True
        
        elif packet.flags & FIN:
            self.stop()
            return True

        else:
            return True


    #================================================================================
    #                             MAIN LOOP OF AGENT
    #================================================================================
    def run(self):
        self.initialize_connection()
        while self.running:
            try:
                while not self.m_queue.empty():
                    with self.lock:
                        p, addr, q, alert = self.m_queue.get()
                    #print(f"Processing from queue: {p}, {addr}, {q}")
                    if alert:
                        continue

                    response = self.send_packet_NetTask(p.to_bytes(), address=addr)
                    if q is not None:
                        q.put(response)
                packet_stream, address = self.s_socket_NetTask.recvfrom(1024)

                #print("Got a packet.")
                p_len = len(packet_stream)
                packet = NetTask.from_bytes(packet_stream)
                self.process_packet(packet, p_len, address)

                
            except Exception as e:
                #print("Exception: " + str(e))
                continue

    def stop(self):
        self.running = False
        for t in self.threads:
            t.stop()

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
    id = get_agent_id()

    agent = Agent(id, address)

    agent.run()

    '''
    if server_socket:
        threading.Thread(target=send_metrics_periodically, args=(server_socket,), daemon=True).start()
        while True:
            time.sleep(1)
    '''
