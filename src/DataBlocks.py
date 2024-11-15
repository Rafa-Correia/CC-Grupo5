import struct
import socket

#DataBlock Identifiers
CPU = 0
RAM = 1
INTERFACE = 2
BANDWIDTH = 3
JITTER = 4
LOSS = 5
LATENCY = 6

#data blocks that are sent by the server
class DataBlockServer:   
    #                  1B,        4B,           1B               4B           4B            1B                 4B                     4B
    def __init__(self, id = CPU, frequency = 1, max_value = 0, duration = 1, client_mode = True, source_ip = "0.0.0.0", destination_ip = "0.0.0.0"):
        #max_value is only really used when id is 0, 1, 2, 4 and 5. In case of id = 2 or 4, then max_value is 4 bytes, else is 1 byte.
        #duration is used to measure bandwidth, jitter, loss and latency.
        self.id = id
        self.frequency = frequency
        self.max_value = max_value
        self.duration = duration
        self.client_mode = client_mode
        self.source_ip = source_ip
        self.destination_ip = destination_ip

    def to_bytes(self):
        s_ip = socket.inet_aton(self.source_ip)
        d_ip = socket.inet_aton(self.destination_ip)
        c_mode = 0
        if self.client_mode:
            c_mode = 1

        if id == CPU:
            return struct.pack('!BiBi', self.id & 0xFF, self.frequency, self.max_value & 0xFF, self.duration)
        
        elif id == RAM:
            return struct.pack('!BiB', self.id & 0xFF, self.frequency, self.max_value & 0xFF)
        
        elif id == INTERFACE:
            return struct.pack('!Bii', self.id & 0xFF, self.frequency, self.max_value)
        
        elif id == BANDWIDTH:
            return struct.pack('!BiiB4s4s', self.id & 0xFF, self.frequency, self.duration, c_mode & 0xFF, s_ip, d_ip)
        
        elif id == JITTER:
            return struct.pack('!BiiiB4s4s', self.id & 0xFF, self.frequency, self.max_value, self.duration, c_mode & 0xFF, s_ip, d_ip)
        
        elif id == LOSS:
            return struct.pack('!BiBiB4s4s', self.id & 0xFF, self.frequency, self.max_value & 0xFF, self.duration, c_mode & 0xFF, s_ip, d_ip)
        
        elif id == LATENCY:
            return struct.pack('!Bii4s4s', self.id & 0xFF, self.frequency, self.duration, s_ip, d_ip)
        
        return None
        
    def from_bytes(id, packed_data):
        if id == CPU:
            freq, max_value, duration = struct.unpack('!iBi', packed_data)
            return DataBlockServer(id, freq, max_value, duration)
        
        elif id == RAM:
            freq, max_value = struct.unpack('!iB', packed_data)
            return DataBlockServer(id, freq, max_value)
        
        elif id == INTERFACE:
            freq, max_value = struct.unpack('!ii', packed_data)
            return DataBlockServer(id, freq, 0, max_value)
        
        elif id == BANDWIDTH:
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
            BANDWIDTH: 17,
            JITTER: 21,
            LOSS: 18,
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
        self.data_len = len(data)

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
        