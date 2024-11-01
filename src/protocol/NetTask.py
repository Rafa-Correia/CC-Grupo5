import socket
import struct
import hashlib

SYN = 0b000001
ACK = 0b000010
DATA = 0b000100
RES = 0b001000
ERR = 0b010000
FIN = 0b100000

class NetTask:
    def __init__ (self, seq_num = 0, ack_num = 0, flags = 0, payload = b''):
        self.seq_num = seq_num
        self.ack_num = ack_num
        self.flags = flags
        self.payload = payload
        self.checksum = self.calculate_checksum()
        
    def calculate_checksum (self):
        data = struct.pack('!IIB', self.seq_num, self.ack_num, self.flags) + self.payload
        return hashlib.md5(data).hexdigest()
    
    
    def to_bytes(self):
        len = len(self.payload)
        header = struct.pack('!IIB16sH', self.seq_num, self.ack_num, self.flags, self.checksum, len)
        return header + self.payload
    
    def from_bytes(data):
        seq_num, ack_num, flags, checksum, payload_len = struct.unpack('!IIB16sH', data[:27])
        payload = data[12:12 + payload_len]
        packet = NetTask(seq_num, ack_num, flags, payload)
        return packet
        