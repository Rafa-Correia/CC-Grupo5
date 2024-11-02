import socket
import time
import json

def send_udp_message_with_seq(server_host='10.0.0.10', server_port=38):
    udp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    sequence_number = 1
    message = "Seq:{sequence_number} - Métricas coletadas!"
    
    # Envia a mensagem com número de sequência
    udp_client_socket.sendto(message.encode(), (server_host, server_port))
    
    # Aguardando ACK
    try:
        udp_client_socket.settimeout(2.0)  # Timeout de 2 segundos
        data, server = udp_client_socket.recvfrom(1024)
        if data.decode() == "ACK:{sequence_number}":
            print("ACK recebido para sequência {sequence_number}")
    except socket.timeout:
        print("Tempo limite para ACK da sequência {sequence_number} expirou.")
        # Aqui poderia ser implementado o código de retransmissão
    
    udp_client_socket.close()

def receive_udp_message_and_execute(client_host='10.0.0.11', client_port=38):
    """
    Recebe mensagens do servidor e executa as tarefas conforme especificado.
    """
    udp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_client_socket.bind((client_host, client_port))
    print("Cliente ouvindo em", client_host, ":", client_port)

    while True:
        # Recebe a mensagem do servidor
        data, server_addr = udp_client_socket.recvfrom(1024)
        message = data.decode()
        print("Mensagem recebida de", server_addr, ":", message)

        # Tenta interpretar a mensagem como JSON para extrair a tarefa
        try:
            task = json.loads(message)
            execute_task(task)
        except json.JSONDecodeError:
            print("Erro: Mensagem recebida não é um JSON válido.")
        
def execute_task(task):
    """
    Executa a tarefa recebida com base nas informações fornecidas.
    """
    device_id = task.get("device_id")
    print("Executando tarefa para o dispositivo", device_id)

    device_metrics = task.get("device_metrics", {})
    if device_metrics:
        print("  Métricas de dispositivo:")
        for metric, enabled in device_metrics.items():
            print("    -", metric, ":", "Ativado" if enabled else "Desativado")

    # Verifica as métricas de dispositivo e executa os comandos correspondentes
    if task.get("device_metrics", {}).get('cpu_usage'):
        print("Monitorando uso de CPU...")
        # Exemplo de comando de monitoramento de CPU (descomente para executar de verdade)
        # subprocess.run(["top", "-b", "-n", "1"])
    
    if task.get("device_metrics", {}).get('ram_usage'):
        print("Monitorando uso de RAM...")
        # Exemplo de comando de monitoramento de RAM (descomente para executar de verdade)
        # subprocess.run(["free", "-h"])
    
    # Adicione mais lógica para outras métricas e tarefas conforme necessário

if __name__ == "__main__":
    send_udp_message_with_seq()
    receive_udp_message_and_execute()