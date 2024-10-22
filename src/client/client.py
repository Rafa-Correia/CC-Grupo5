import socket
import time

def send_udp_message_with_seq(server_host='10.0.0.10', server_port=38):
    udp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    sequence_number = 1
    message = f"Seq:{sequence_number} - Métricas coletadas!"
    
    # Envia a mensagem com número de sequência
    udp_client_socket.sendto(message.encode(), (server_host, server_port))
    
    # Aguardando ACK
    try:
        udp_client_socket.settimeout(2.0)  # Timeout de 2 segundos
        data, server = udp_client_socket.recvfrom(1024)
        if data.decode() == f"ACK:{sequence_number}":
            print(f"ACK recebido para sequência {sequence_number}")
    except socket.timeout:
        print(f"Tempo limite para ACK da sequência {sequence_number} expirou.")
        # Aqui poderia ser implementado o código de retransmissão
    
    udp_client_socket.close()

if __name__ == "__main__":
    send_udp_message_with_seq()