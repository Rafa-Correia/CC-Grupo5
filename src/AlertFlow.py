import socket
import json
import threading
import os
import struct

CPU         = 0b00000001
RAM         = 0b00000010
INTERFACE   = 0b00000100
JITTER      = 0b00001000
LOSS        = 0b00010000
ALERT       = 0b00100000
ERR         = 0b01000000

class AlertFlow:
    def __init__(self, flags = CPU, m_value = 0, payload = b''):
        self.flags = flags
        self.m_value = m_value
        self.payload = payload
        
    def to_bytes(self):
        if self.flags & ERR:
            return struct.pack('!B', self.flags & 0xFF)
        
        if not self.flags & ALERT and not self.flags & ERR:
            return None #SHOULD ALLWAYS HAVE ERR OR ALERT
        
        if self.flags & CPU or self.flags & RAM or self.flags & LOSS:
            return struct.pack('!BB', self.flags & 0xFF, self.m_value & 0xFF)
        
        elif self.flags & JITTER:
            return struct.pack('!Bi', self.flags & 0xFF, self.m_value)
        
        elif self.flags & INTERFACE:
            s_len = len(self.payload)
            packed_data = struct.pack('!BiH', self.flags & 0xFF, self.m_value, s_len)
            return packed_data + self.payload
        
        return None
        
    def from_bytes(packet_stream):
        flags = struct.unpack('!B', packet_stream[:1])[0]
        if flags & ERR:
            return AlertFlow(flags=flags)
        
        if not flags & ERR and not flags & ALERT:
            return None
        
        if flags & CPU or flags & RAM or flags & LOSS:
            m_value = struct.unpack('!B', packet_stream[1:2])[0]
            return AlertFlow(flags=flags, m_value=m_value)
        
        elif flags & JITTER:
            m_value = struct.unpack('!i', packet_stream[1:5])[0]
            return AlertFlow(flags=flags, m_value=m_value)
        
        elif flags & INTERFACE:
            m_value, s_len = struct.unpack('!iH', packet_stream[1:7])
            payload = packet_stream[7:7+s_len]
            return AlertFlow(flags=flags, m_value=m_value, payload=payload)
        
        return None
            
        