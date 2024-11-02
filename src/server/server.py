import socket
import json

class TaskInterpreter:
    def __init__(self, file_path):
        """
        Inicializa o interpretador de tarefas com o caminho para o arquivo JSON.
        """
        self.file_path = file_path
        self.tasks = []

    def load_tasks(self):
        """
        Carrega as tarefas do arquivo JSON. Se o arquivo não for encontrado ou estiver corrompido,
        uma mensagem de erro será exibida.
        """
        try:
            with open(self.file_path, 'r') as file:
                data = json.load(file)
                self.tasks = data.get('tasks', [])
                print("Tarefas carregadas com sucesso.")
        except FileNotFoundError:
            print("Arquivo não encontrado:", self.file_path)
        except json.JSONDecodeError:
            print("Erro ao decodificar o arquivo JSON.")
    
    def process_tasks(self):
        """
        Processa as tarefas carregadas, exibindo informações detalhadas sobre cada tarefa,
        incluindo dispositivos, métricas e condições de alerta.
        """
        if not self.tasks:
            print("Nenhuma tarefa para processar.")
            return

        for task in self.tasks:
            # Extrai informações da tarefa principal
            task_id = task.get("task_id")
            frequency = task.get("frequency")
            devices = task.get("devices", [])

            print("Processando tarefa: Task ID =", task_id, "Frequência =", frequency, "segundos")

            for device in devices:
                # Extrai informações específicas do dispositivo
                device_id = device.get("device_id")
                device_metrics = device.get("device_metrics", {})
                link_metrics = device.get("link_metrics", {})
                alertflow_conditions = device.get("alertflow_conditions", {})

                print("  Dispositivo:", device_id)
                
                # Processa métricas do dispositivo, como uso de CPU e RAM
                for metric, enabled in device_metrics.items():
                    if enabled:
                        print("    Monitorando métrica de dispositivo:", metric)

                # Processa métricas de link, como largura de banda e jitter
                for metric, config in link_metrics.items():
                    print("    Métrica de link:", metric, "Configuração:", config)

                # Processa as condições de alerta
                for condition, limit in alertflow_conditions.items():
                    print("    Condição de alerta:", condition, ">=", limit)

class Server:
    def __init__(self, host='10.0.0.10', port=38, task_file='/home/core/Desktop/Uni/CC/CC-Grupo5/src/tasks.json'):
        """
        Inicializa o servidor com o endereço e a porta especificados, e configura o interpretador de tarefas.
        """
        self.host = host
        self.port = port
        self.task_interpreter = TaskInterpreter(task_file)

    def start_udp_server_with_ack(self):
        """
        Inicia o servidor UDP, carrega e processa as tarefas do JSON e responde com ACK para
        mensagens recebidas dos clientes.
        """
        # Carrega e processa as tarefas antes de iniciar o servidor
        self.task_interpreter.load_tasks()
        self.task_interpreter.process_tasks()

        # Configura o socket UDP
        udp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_server_socket.bind((self.host, self.port))

        print("Servidor ouvindo em", self.host, ":", self.port)

        while True:
            # Recebe dados do cliente
            data, addr = udp_server_socket.recvfrom(1024)
            message = data.decode()
            print("Mensagem recebida de", addr, ":", message)

            # Extrai o número de sequência para enviar o ACK correspondente
            if "Seq:" in message:
                seq_num = message.split(":")[1].split(" - ")[0]
                print("Número de sequência recebido:", seq_num)

                # Envia um ACK de volta para o cliente
                ack_message = "ACK:" + seq_num
                udp_server_socket.sendto(ack_message.encode(), addr)

if __name__ == "__main__":
    # Inicializa e inicia o servidor
    srv = Server()
    srv.start_udp_server_with_ack()





"""
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
"""