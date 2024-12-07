import struct
from DataBlocks import *


import struct
import time
from DataBlocks import *

class AlertFlow:
    def __init__(self, id=CPU, m_value=0, payload=b''):
        self.id = id
        self.m_value = m_value
        self.payload = payload
        self.payload_len = len(payload)
        self.timestamp = int(time.time())

    def to_bytes(self):
        if self.id in (CPU, RAM, LOSS):
            return struct.pack('!BBI', self.id & 0xFF, self.m_value & 0xFF, self.timestamp)
        
        elif self.id == JITTER:
            return struct.pack('!Bii', self.id & 0xFF, self.m_value, self.timestamp)
        
        elif self.id == INTERFACE:
            packed_data = struct.pack('!BiHi', self.id & 0xFF, self.m_value, self.payload_len & 0xFFFF, self.timestamp)
            return packed_data + self.payload

        return None

    @staticmethod
    def from_bytes(packet_stream):
        id = struct.unpack('!B', packet_stream[:1])[0]

        if id in (CPU, RAM, LOSS):
            m_value, timestamp = struct.unpack('!BI', packet_stream[1:1+5])
            return AlertFlow(id, m_value, b'')

        elif id == JITTER:
            m_value, timestamp = struct.unpack('!ii', packet_stream[1:1+8])
            return AlertFlow(id, m_value, b'')

        elif id == INTERFACE:
            m_value, payload_len, timestamp = struct.unpack('!iHi', packet_stream[1:1+10])
            payload = packet_stream[1+10:1+10+payload_len]
            return AlertFlow(id, m_value, payload)

            
        