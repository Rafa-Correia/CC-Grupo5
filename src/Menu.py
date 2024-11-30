from nms_server import Server
import threading
import os

def interpretar_tarefas(server, task_file_path):
    """
    Função para carregar tarefas de um arquivo JSON especificado pelo usuário.
    """
    print("\n=== Interpretar Tarefas ===")
    task_file_path = input("Digite o caminho do arquivo JSON de tarefas: ")
    
    # Verificar se o caminho do arquivo existe
    if not os.path.isfile(task_file_path):
        print("Erro: Arquivo JSON não encontrado.")
        return
    server.task_interpreter.task_file_path = task_file_path
    server.assign_tasks()

def apresentar_metricas(server):
    """
    Função para exibir as métricas recebidas dos agentes.
    """
    print("\n=== Apresentar Métricas ===")
    print("Métricas recebidas dos agentes:")
    server.print_all_data()

def iniciar_servidor(server):
    """
    Inicia o servidor em um thread separado para permitir o uso contínuo do menu.
    """
    print("\n=== Iniciar Servidor ===")
    print("Servidor está sendo iniciado...")
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    print("Servidor iniciado! Use Ctrl+C para parar.")

def main():
    PORT = 65432  # Porta padrão para o servidor
    task_file_path = "tasks2.json"  # Caminho padrão inicial para o arquivo JSON

    # Criar instância do servidor
    server = Server(PORT, task_file_path)

    while True:
        print("\n===== Menu Principal =====")
        print("1. Interpretar Tarefas (Especificar Arquivo JSON)")
        print("2. Apresentar Métricas")
        print("3. Iniciar Servidor")
        print("0. Sair")
        
        escolha = input("Escolha uma opção: ")
        
        if escolha == "1":
            interpretar_tarefas(server, task_file_path)
        elif escolha == "2":
            apresentar_metricas(server)
        elif escolha == "3":
            iniciar_servidor(server)
        elif escolha == "0":
            print("Encerrando o programa. Até logo!")
            break
        else:
            print("Opção inválida. Tente novamente.")

if __name__ == "__main__": 
    main()