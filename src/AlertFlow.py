import struct
from DataBlocks import *


class AlertFlow:
    def __init__(self, id = CPU, m_value = 0, payload = b''):
        self.id = id
        self.m_value = m_value
        self.payload = payload
        self.payload_len = len(payload)
        
        #print(f"AlertFlow with id {id}, m_value {m_value} and data {payload}")
        
    def to_bytes(self):
        if self.id & CPU or self.id & RAM or self.id & LOSS:
            return struct.pack('!BB', self.id & 0xFF, self.m_value & 0xFF)
        
        elif self.id & JITTER:
            return struct.pack('!Bi', self.id & 0xFF, self.m_value)
        
        elif self.id & INTERFACE:
            packed_data = struct.pack('!BiH', self.id & 0xFF, self.m_value, self.payload_len & 0xFFFF)
            return packed_data + self.payload
        
        return None
        
    def from_bytes(packet_stream):
        #print(f"Trying to unpack {packet_stream} of length {str(len(packet_stream))}")
        id = struct.unpack('!B', packet_stream[:1])[0]
        if id == CPU or id == RAM or id == LOSS:
            m_value = struct.unpack('!B', packet_stream[1:2])[0]
            return AlertFlow(id , m_value)
        
        elif id == JITTER:
            m_value = struct.unpack('!i', packet_stream[1:5])[0]
            return AlertFlow(id, m_value)
        
        elif id == INTERFACE:
            m_value, s_len = struct.unpack('!iH', packet_stream[1:7])
            payload = packet_stream[7:7+s_len]
            return AlertFlow(id, m_value, payload)
        
        return None
            
        