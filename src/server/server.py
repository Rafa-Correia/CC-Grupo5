import socket

class Server:
    
    def start_udp_server_with_ack(host='10.0.0.10', port=38):
        udp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_server_socket.bind((host, port))

        print(f"Server listening at {host}:{port}")

        while True:
            data, addr = udp_server_socket.recvfrom(1024)
            message = data.decode()
            print(f"Mensagem recebida de {addr}: {message}")

            # Extrai o número de sequência
            if "Seq:" in message:
                seq_num = message.split(":")[1].split(" - ")[0]
                print(f"Número de sequência recebido: {seq_num}")

                # Envia um ACK de volta
                ack_message = f"ACK:{seq_num}"
                udp_server_socket.sendto(ack_message.encode(), addr)

if __name__ == "__main__":
    srv = Server()
    srv.start_udp_server_with_ack()