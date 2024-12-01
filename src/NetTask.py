import socket
import struct
import hashlib
import time
import json

#NetTask flags
SYN     = 0b00000001
ACK     = 0b00000010
TASK    = 0b00000100
REPORT  = 0b00001000
REQ     = 0b00010000
ERR     = 0b00100000
FIN     = 0b01000000

class NetTask:
    def __init__(self, seq_num=0, ack_num=0, flags=0, task_id = 0, payload=b''):
        self.seq_num = seq_num
        self.ack_num = ack_num
        self.flags = flags
        self.task_id = task_id
        self.payload = payload
        self.checksum = self.calculate_checksum()
        #print(f"[NETTASK] - [__init__]: INITIALIZED WITH SEQ_NUM={self.seq_num}, ACK_NUM={self.ack_num}, FLAGS={self.flags}, PAYLOAD LENGTH={len(self.payload)}, PAYLOAD={self.payload}")

    def calculate_checksum(self):
        data = struct.pack('!IIB', self.seq_num, self.ack_num, self.flags) + self.payload
        checksum = hashlib.md5(data).hexdigest()
        #print(f"[NETTASK] - [calculate_checksum]: CHECKSUM CALCULATED AS {checksum}")
        return checksum

    def to_bytes(self):

        payload_length = len(self.payload)
        header = struct.pack('!IIB16siH', self.seq_num, self.ack_num, self.flags, self.checksum.encode('utf-8'), self.task_id, payload_length)
        #print(f"[NETTASK] - [to_bytes]: CONVERTED TO BYTES WITH HEADER LENGTH={len(header)}, PAYLOAD LENGTH={payload_length}")
        return header + self.payload

    @staticmethod
    def from_bytes(data):
        seq_num, ack_num, flags, checksum, task_id, payload_len= struct.unpack('!IIB16siH', data[:31])
        payload = data[31:31 + payload_len]
        packet = NetTask(seq_num, ack_num, flags, task_id, payload)
        packet.checksum = checksum.decode('utf-8')
        #print(f"[NETTASK] - [from_bytes]: PACKET CREATED FROM BYTES WITH SEQ_NUM={seq_num}, ACK_NUM={ack_num}, FLAGS={flags}, PAYLOAD LENGTH={payload_len}")
        return packet

    def send_with_retransmission(self, socket, address, timeout=2):
        socket.sendto(self.to_bytes(), address)
        #print(f"[NETTASK] - [send_with_retransmission]: PACKET SENT TO {address}")
        socket.settimeout(timeout)
        try:
            response, _ = socket.recvfrom(4096)
            ack_packet = NetTask.from_bytes(response)
            if ack_packet.flags & ACK:
                #print(f"[NETTASK] - [send_with_retransmission]: ACK RECEIVED FOR SEQ_NUM={self.seq_num}")
                return True
        except socket.timeout:
            #print(f"[NETTASK] - [send_with_retransmission]: TIMEOUT, RETRANSMITTING SEQ_NUM={self.seq_num}")
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
            #print(f"[NETTASK] - [handle_transmission]: RETRY {attempt + 1} FOR SEQ_NUM={self.seq_num}")
        #print(f"[NETTASK] - [handle_transmission]: FAILED AFTER {max_retries} RETRIES FOR SEQ_NUM={self.seq_num}")
        return False

    def prepare_metrics_payload(self, metrics):
        self.payload = json.dumps(metrics).encode('utf-8')
        self.checksum = self.calculate_checksum()
        #print(f"[NETTASK] - [prepare_metrics_payload]: METRICS PAYLOAD PREPARED WITH CHECKSUM {self.checksum}")

if __name__ == "__main__":
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    test_address = ('127.0.0.1', 12345)

    packet = NetTask(seq_num=1, ack_num=0, flags=REPORT)
    packet.prepare_metrics_payload({"cpu_usage": 50, "ram_usage": 60})
    packet.handle_transmission(udp_socket, test_address)