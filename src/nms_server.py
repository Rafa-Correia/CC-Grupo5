import select
import socket
import threading
import random
from NetTask import *
from AlertFlow import *
from DataBlocks import *
from Task import *

class Server:
    def __init__(self):
        self.task_interpreter_list = []

        self.server_socket_NetTask = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket_NetTask.bind(('0.0.0.0', 65432))
        self.server_socket_NetTask.settimeout(2)

        self.server_socket_AlertFlow = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket_AlertFlow.bind(('0.0.0.0', 23456))
        self.server_socket_AlertFlow.setblocking(False)

        self.lock = threading.Lock()
        self.agent_registry = {}
        self.address_to_agent_id = {}
        self.agent_data = {}

        self.alert_sockets = [self.server_socket_AlertFlow]
        self.alert_to_agent_id = {}

        self.agent_alerts = {}
        
    def start(self):
        #start thread for alertFlow read
        threading.Thread(target=self.alert_flow_loop, daemon=True).start()
        while True:
            try:
                self.assign_tasks()
                #self.print_all_data() 

                packet_stream, address = self.server_socket_NetTask.recvfrom(1024)
                packet = NetTask.from_bytes(packet_stream)
                if packet.flags & SYN:
                    #print(f"[NMS_SERVER] - [start]: NEW CONNECTION FROM {address}")
                    agent_id = packet.payload.decode("utf-8")
                    self.agent_registry[agent_id] = (address, random.randint(0, 100000), packet.seq_num)
                    self.address_to_agent_id[address] = agent_id
                    self.agent_data[agent_id] = b''
                    #print(f"Registered at {agent_id}:{self.agent_registry[agent_id]}")
                    flags = SYN
                    flags |= ACK
                    ack_packet = NetTask(seq_num=self.agent_registry[agent_id][1], ack_num=self.agent_registry[agent_id][2], flags=flags)
                    ack_stream = ack_packet.to_bytes()
                    #print("Sending " + str(ack_stream))
                    self.server_socket_NetTask.sendto(ack_stream, address)
                else:
                    self.process_NetTask_packet(packet, address)
            except Exception as e:
                #print("Exception: " + str(e)) Parar de mandar time outs
                continue

    def alert_flow_loop(self):
        self.server_socket_AlertFlow.listen(5)
        while True:
            readable, _, _ = select.select(self.alert_sockets, [], self.alert_sockets)
            for sock in readable:
                if sock is self.server_socket_AlertFlow:
                    #this is a new connection
                    #register socket
                    client_socket, address = sock.accept()
                    client_socket.setblocking(False)
                    self.alert_sockets.append(client_socket)
                    ip, _ = address
                    agent_id = self.address_to_agent_id[(ip, 65432)]
                    self.alert_to_agent_id[client_socket] = agent_id

                else:
                    data = sock.recv(1024)
                    if data:
                        alert_packet = AlertFlow.from_bytes(data)
                        agent_id = self.alert_to_agent_id[sock]
                        alert_list = self.agent_alerts.get(agent_id, None)
                        if alert_list is None:
                            alert_list = []
                            alert_list.append(alert_packet)
                            self.agent_alerts[agent_id] = alert_list
                        else:
                            alert_list.append(alert_packet)
                        #process alert packet
                    else:
                        self.alert_sockets.remove(sock)
                        del self.alert_to_agent_id[sock]
                        sock.close()

    def process_NetTask_packet(self, packet, address):
        try:
            #print("Got data from agent...")
            if packet.flags & REPORT:
                #print("It's a report!")
                agent_id = self.address_to_agent_id[address]
                if packet.seq_num < self.agent_registry[agent_id][2]:
                    #print("Seq is smaller.")
                    self.agent_data[agent_id] = self.agent_data[agent_id][:packet.seq_num]

                new_registry = (address, self.agent_registry[agent_id][1], self.agent_registry[agent_id][2]+len(packet.payload))
                self.agent_registry[agent_id] = new_registry

                acknowledge_packet = NetTask(self.agent_registry[agent_id][1], self.agent_registry[agent_id][2], ACK, packet.task_id)
                ack_stream = acknowledge_packet.to_bytes()
                #print(f"Sending ack to {address}...")
                self.server_socket_NetTask.sendto(ack_stream, address)
                #print("Done!")

                #print(f"Added {packet.payload} to agent {agent_id}'s data.")
                self.agent_data[agent_id] += packet.payload
        except Exception as e:
            print(f"Oh... {e}")

    def send_packet(self, packet_stream, address, max_retries = 10):
        retries = 0
        while retries < max_retries:
            try:
                self.server_socket_NetTask.sendto(packet_stream, address)
                while True:
                    #print("waiting for response...")
                    response, address_r = self.server_socket_NetTask.recvfrom(1024)

                    packet = NetTask.from_bytes(response)
                    
                    if address_r != address:
                        self.process_NetTask_packet(packet, address_r)
                    
                    elif packet.flags & ACK:
                        #print("Got ack")
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
        #print("Assigning tasks...")
        agents = self.agent_registry.keys()
        for a in agents:
            for interpreter in self.task_interpreter_list:
                tasks = interpreter.devices_with_tasks.get(a, None)
                if tasks == None:
                    continue
                else:
                    #print(f"Sending task to {a}!")
                    address, seq, ack = self.agent_registry[a]
                    while tasks:
                        t = tasks.pop()
                        payload = t.to_bytes()
                        packet = NetTask(seq, ack, TASK, t.task_id, payload)
                        self.send_packet(packet.to_bytes(), address)

    def print_all_data(self):
        #print("Printing all data:\n")
        id_to_string = {
            CPU: "CPU",
            RAM: "RAM",
            INTERFACE: "INTERFACE",
            BANDWIDTH: "BANDWIDTH",
            JITTER: "JITTER",
            LOSS: "LOSS",
            LATENCY: "LATENCY"
        }
        count = 1
        key_set = self.agent_data.keys()
        for k in key_set:
            print(f"From agent {k}:")
            p = self.agent_data.get(k, b'')
            #print(f"\tRaw data is {p}!")
            blocks = DataBlockClient.separate_packed_data(p)
            if blocks:
                for b in blocks:
                    print(f"----------{count}----------")
                    count = count + 1
                    print(f"\tMetric: {id_to_string[b.id]}\n\tm_value: {b.m_value}")
                    if b.data != b'':
                        print()
                    print(f"---------------------------")
            else:
                print("\tNone.")

    def print_registered_agents(self):
        print("\nAgentes registados:")
        agents = self.agent_registry.keys()
        if not agents:
            print("\tNenhum agente registado")
            return
        i = 1
        for a in agents:
            print(f"\t{i}.: {a}")
            i += 1

    def print_agent_data(self, agent_id):
        id_to_string = {
            CPU: "CPU",
            RAM: "RAM",
            INTERFACE: "INTERFACE",
            BANDWIDTH: "BANDWIDTH",
            JITTER: "JITTER",
            LOSS: "LOSS",
            LATENCY: "LATENCY"
        }

        count = 1
        print(f"From agent {agent_id}:")
        p = self.agent_data.get(agent_id, None)
        #print(f"\tRaw data is {p}!")
        if p is None:
            print("\tNo data!")
        blocks = DataBlockClient.separate_packed_data(p)
        if blocks:
            for b in blocks:
                print(f"----------{count}----------")
                count = count + 1
                unit = ""
                if b.id == BANDWIDTH:
                    unit = "Mbits/sec"
                elif b.id == JITTER:
                    unit = "ms"
                elif b.id == CPU or b.id == RAM or b.id == LOSS:
                    unit = "%"
                print(f"\tMetric: {id_to_string[b.id]}\n\tMeasured value: {b.m_value} {unit}")
                if b.data != b'':
                    print()
                print(f"---------------------------")
        else:
            print("\tNone.")

    def print_agent_alerts(self, agent_id):
        id_to_string = {
            CPU: "CPU",
            RAM: "RAM",
            INTERFACE: "INTERFACE",
            BANDWIDTH: "BANDWIDTH",
            JITTER: "JITTER",
            LOSS: "LOSS",
            LATENCY: "LATENCY"
        }

        print(f"From agent {agent_id}:")
        alert_list = self.agent_alerts[agent_id]
        count = 1
        if not alert_list:
            print("\tNo alerts!")
        for a in alert_list:
            print(f"----------{count}----------")
            print(f"\tMetric: {id_to_string[a.id]}\n\tMeasured Value: {a.m_value}")
            if a.payload != b'':
                print(f"\tData: {a.payload}")
            print(f"------------------------------")

    def stop_server(self):
        agent_list = self.agent_registry.keys()
        for a in agent_list:
            print(f"Finalizing conection with {a}...")
            self.send_fin(a)
            continue

        for sock in self.alert_sockets:
            sock.close()
            
        return
    
    def send_fin(self, agent_id):
        agent_address, seq, ack = self.agent_registry[agent_id]
        final_packet = NetTask(seq, ack, FIN)
        while True:
            try:
                print(f"Sending FIN packet to {agent_address}")
                self.server_socket_NetTask.sendto(final_packet.to_bytes(), agent_address)
                while True:
                    rec_stream, rec_address = self.server_socket_NetTask.recvfrom(1024)
                    if rec_address != agent_address:
                        continue

                    rec_packet = NetTask.from_bytes(rec_stream)
                    if rec_packet.flags & FIN and rec_packet.flags & ACK:
                        print("Got a FINACK from the agent!")
                        return
                    else:
                        continue
            except OSError:
                print("Socket has been closed already!")
                break

            except:
                continue

if __name__ == "__main__":

    server = Server()
    print("[NMS_SERVER] - [main]: INITIALIZING SERVER...")
    server.start()
