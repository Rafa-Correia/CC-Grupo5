import socket
import struct
import hashlib
import time
import json

#NetTask flags
SYN  = 0b00000001
ACK  = 0b00000010
DATA = 0b00000100
RES  = 0b00001000
ERR  = 0b00010000
FIN  = 0b00100000

#Agent DataBlock identifiers
CPU = 0
RAM = 1
INTERFACE = 2
BANDWIDTH = 3
JITTER = 4
LOSS = 5
LATENCY = 6

#Server DataBlock identifiers
CPU = 0
RAM = 1
INTERFACE = 2
IPERF_M = 3 #blocks for measuring bandwidth, loss and jitter
LATENCY = 4

#measure mode flags
CLIENT_MODE       = 0b00000001
SERVER_MODE       = 0b00000010
USING_TCP         = 0b00000100
M_BANDWIDTH       = 0b00001000
M_LOSS            = 0b00010000
M_JITTER          = 0b00100000


#data blocks that are sent by the server
class DataBlockServer:   
    #                  1B,        4B,           1B               4B           4B            1B                 4B                     4B
    def __init__(self, id = CPU, frequency = 1, max_percent = 0, max_int = 0, duration = 1, measure_flags = 0, source_ip = "0.0.0.0", destination_ip = "0.0.0.0"):
        #max_value is only really used when id is 0, 1, 2, 4 and 5. In case of id = 2 or 4, then max_value is 4 bytes, else is 1 byte.
        #duration is used to measure bandwidth, jitter, loss and latency.
        self.id = id
        self.frequency = frequency
        self.max_percent = max_percent
        self.max_int = max_int
        self.duration = duration
        self.measure_flags = measure_flags
        self.source_ip = source_ip
        self.destination_ip = destination_ip

    def to_bytes(self):
        if id == CPU or id == RAM:
            return struct.pack('!BiB', self.id & 0xFF, self.frequency, self.max_percent & 0xFF)
        
        elif id == INTERFACE:
            return struct.pack('!Bii', self.id & 0xFF, self.frequency, self.max_int)
        
        elif id == IPERF_M:
            s_ip = socket.inet_aton(self.source_ip)
            d_ip = socket.inet_aton(self.destination_ip)
            return struct.pack('!BiBiiB4s4s', self.id & 0xFF, self.frequency, self.max_percent & 0xFF, self.max_int, self.measure_flags & 0xFF, self.duration, s_ip, d_ip)
        
        elif id == LATENCY:
            s_ip = socket.inet_aton(self.source_ip)
            d_ip = socket.inet_aton(self.destination_ip)
            return struct.pack('!Bii4s4s', self.id & 0xFF, self.frequency, self.duration, s_ip, d_ip)
        
        return None
        
    def from_bytes(id, packed_data):
        if id == CPU or id == RAM:
            freq, max_value = struct.unpack('!iB', packed_data)
            return DataBlockServer(id, freq, max_value)
        
        elif id == INTERFACE:
            freq, max_value = struct.unpack('!ii', packed_data)
            return DataBlockServer(id, freq, 0, max_value)
        
        elif id == IPERF_M:
            freq, max_perc, max_int, duration, measure_flags, s_ip, d_ip = struct.unpack('!iBiiB4s4s', packed_data)
            source_ip = socket.inet_ntoa(s_ip)
            destination_ip = socket.inet_ntoa(d_ip)
            return DataBlockServer(id, freq, max_perc, max_int, duration, measure_flags, source_ip, destination_ip)

        elif id == LATENCY:
            freq, duration, s_ip, d_ip = struct.unpack('!ii4s4s', packed_data)
            source_ip = socket.inet_ntoa(s_ip)
            destination_ip = socket.inet_ntoa(d_ip)
            return DataBlockServer(id, freq, 0, 0, duration, 0, source_ip, destination_ip)


        return None
    
    def separate_packed_data(packed_blocks):
        # Define the mapping from ID to data length
        id_to_length = {
            CPU: 5,
            RAM: 5,
            INTERFACE: 8,
            IPERF_M: 22,
            LATENCY: 16
        }

        # Initialize an index to read through the packed byte stream
        index = 0
        data_blocks = []

        # Unpack each block and use from_bytes to create DataBlock objects with ID
        while index < len(packed_blocks):
            # Read the ID (1 byte)
            block_id = struct.unpack_from("!B", packed_blocks, index)[0]
            index += 1  # Move index past the ID field

            # Get the data length for this ID
            data_length = id_to_length[block_id]

            # Extract the data bytes for this block
            data = packed_blocks[index:index + data_length]
            index += data_length  # Move index past the data

            # Create a DataBlock object with the ID and data, and store it
            data_block = DataBlockServer.from_bytes(block_id, data)
            data_blocks.append(data_block)
        return data_blocks


#data blocks that are sent by the client
class DataBlockClient:
    #                  1B        1B/4B        xB
    def __init__(self, id = CPU, m_value = 0, data = b''):
        self.id = id
        self.m_value = m_value
        self.data = data
        self.data_len = data.__len__()

    def to_bytes(self):
        if id == CPU or id == RAM or id == LOSS:
            return struct.pack('!BB', self.id & 0xFF, self.m_value & 0xFF)

        elif id == INTERFACE:
            packed_len = struct.pack('!BH', self.id & 0xFF, self.data_len & 0xFFFF)
            return packed_len + self.data
        
        else:
            return struct.pack('!Bi', self.id & 0xFF, self.m_value)

    def from_bytes(packed_data = b''):
        if id == CPU or id == RAM or id == LOSS:
            m_value = struct.unpack('!B', packed_data)
            return DataBlockClient(id, m_value)
        
        elif id == INTERFACE:
            data_len = struct.unpack('!H', packed_data)
            encoded_data = packed_data[3:3+data_len]
            return DataBlockClient(id, 0, encoded_data)
        
        else:
            m_value = struct.unpack('!i', packed_data)
            return DataBlockClient(id, m_value)
        

    def separate_packed_data(packed_blocks):
        # Define the mapping from ID to data length
        id_to_length = {
            CPU: 1,
            RAM: 1,
            #INTERFACE: ?
            BANDWIDTH: 4,
            JITTER: 4,
            LOSS: 1,
            LATENCY: 4
        }

        # Initialize an index to read through the packed byte stream
        index = 0
        data_blocks = []

        # Unpack each block and use from_bytes to create DataBlock objects with ID
        while index < len(packed_blocks):
            # Read the ID (1 byte)
            block_id = struct.unpack_from("!B", packed_blocks, index)[0]
            index += 1  # Move index past the ID field

            if(block_id == INTERFACE):
                str_len = struct.unpack('!H', packed_blocks[index:index+2])[0]
                data_length = 2 + str_len

            # Get the data length for this ID
            else:
                data_length = id_to_length[block_id]

            # Extract the data bytes for this block
            data = packed_blocks[index:index + data_length]
            index += data_length  # Move index past the data

            # Create a DataBlock object with the ID and data, and store it
            data_block = DataBlockServer.from_bytes(block_id, data)
            data_blocks.append(data_block)
        return data_blocks
        


        


class NetTask:
    def __init__(self, seq_num=0, ack_num=0, flags=0, payload=b''):
        self.seq_num = seq_num
        self.ack_num = ack_num
        self.flags = flags
        self.payload = payload
        self.checksum = self.calculate_checksum()
        print(f"[NETTASK] - [__init__]: INITIALIZED WITH SEQ_NUM={self.seq_num}, ACK_NUM={self.ack_num}, FLAGS={self.flags}, PAYLOAD LENGTH={len(self.payload)}")

    def calculate_checksum(self):
        data = struct.pack('!IIB', self.seq_num, self.ack_num, self.flags) + self.payload
        checksum = hashlib.md5(data).hexdigest()
        print(f"[NETTASK] - [calculate_checksum]: CHECKSUM CALCULATED AS {checksum}")
        return checksum

    def to_bytes(self):
        payload_length = len(self.payload)
        header = struct.pack('!IIB16sH', self.seq_num, self.ack_num, self.flags, self.checksum.encode('utf-8'), payload_length)
        print(f"[NETTASK] - [to_bytes]: CONVERTED TO BYTES WITH HEADER LENGTH={len(header)}, PAYLOAD LENGTH={payload_length}")
        return header + self.payload

    @staticmethod
    def from_bytes(data):
        seq_num, ack_num, flags, checksum, payload_len = struct.unpack('!IIB16sH', data[:27])
        payload = data[27:27 + payload_len]
        packet = NetTask(seq_num, ack_num, flags, payload)
        packet.checksum = checksum.decode('utf-8')
        print(f"[NETTASK] - [from_bytes]: PACKET CREATED FROM BYTES WITH SEQ_NUM={seq_num}, ACK_NUM={ack_num}, FLAGS={flags}, PAYLOAD LENGTH={payload_len}")
        return packet

    def send_with_retransmission(self, socket, address, timeout=2):
        socket.sendto(self.to_bytes(), address)
        print(f"[NETTASK] - [send_with_retransmission]: PACKET SENT TO {address}")
        socket.settimeout(timeout)
        try:
            response, _ = socket.recvfrom(4096)
            ack_packet = NetTask.from_bytes(response)
            if ack_packet.flags & ACK:
                print(f"[NETTASK] - [send_with_retransmission]: ACK RECEIVED FOR SEQ_NUM={self.seq_num}")
                return True
        except socket.timeout:
            print(f"[NETTASK] - [send_with_retransmission]: TIMEOUT, RETRANSMITTING SEQ_NUM={self.seq_num}")
            return False

    def update_sequence_and_ack(self):
        self.seq_num += 1
        self.ack_num = self.seq_num
        print(f"[NETTASK] - [update_sequence_and_ack]: SEQ_NUM UPDATED TO {self.seq_num}, ACK_NUM UPDATED TO {self.ack_num}")

    def handle_transmission(self, socket, address, max_retries=3):
        for attempt in range(max_retries):
            success = self.send_with_retransmission(socket, address)
            if success:
                return True
            print(f"[NETTASK] - [handle_transmission]: RETRY {attempt + 1} FOR SEQ_NUM={self.seq_num}")
        print(f"[NETTASK] - [handle_transmission]: FAILED AFTER {max_retries} RETRIES FOR SEQ_NUM={self.seq_num}")
        return False

    def prepare_metrics_payload(self, metrics):
        self.payload = json.dumps(metrics).encode('utf-8')
        self.checksum = self.calculate_checksum()
        print(f"[NETTASK] - [prepare_metrics_payload]: METRICS PAYLOAD PREPARED WITH CHECKSUM {self.checksum}")

if __name__ == "__main__":
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    test_address = ('127.0.0.1', 12345)

    packet = NetTask(seq_num=1, ack_num=0, flags=DATA)
    packet.prepare_metrics_payload({"cpu_usage": 50, "ram_usage": 60})
    packet.handle_transmission(udp_socket, test_address)