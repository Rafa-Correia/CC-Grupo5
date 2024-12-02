from nms_server import Server
from Task import *
import threading
import os

def interpretar_tarefas(server):
    """
    Função para carregar tarefas de um arquivo JSON especificado pelo usuário.
    """
    print("\n=== Interpretar Tarefas ===")
    task_file_path = input("Digite o caminho do arquivo JSON de tarefas: ")
    
    # Verificar se o caminho do arquivo existe
    if not os.path.isfile(task_file_path):
        print("Erro: Arquivo JSON não encontrado.")
        return
    
    interpreter = TaskInterpreter(task_file_path)
    interpreter.load_tasks()
    with server.lock:
        server.task_interpreter_list.append(interpreter)


def apresentar_metricas(server: Server):
    """
    Função para exibir as métricas recebidas dos agentes.
    """
    while True:
        print("\n=== Apresentar Métricas ===")
        print("1. Apresentar agentes registados")
        print("2. Apresentar metricas coletadas por Agente")
        print("3. Apresentar alertas dados por Agente")
        print("4. Voltar ao menu anterior")

        selection = input("Escolha uma opção: ")
        if selection == "1":
            server.print_registered_agents()
        elif selection == "2":
            agent_id = input("ID do Agente: ")
            server.print_agent_data(agent_id)
        elif selection == "3":
            agent_id = input("ID do Agente: ")
            server.print_agent_alerts(agent_id)
        elif selection == "4":
            return

        else:
            print("INVALID")


    server.print_all_data()

def iniciar_servidor(server):
    """
    Inicia o servidor em um thread separado para permitir o uso contínuo do menu.
    """
    print("\n=== Iniciar Servidor ===")
    print("Servidor está sendo iniciado...")
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    print("Servidor iniciado!")

def main():
    # Criar instância do servidor
    server = Server()
    iniciar_servidor(server)

    while True:
        print("\n===== Menu Principal =====")
        print("1. Interpretar Tarefas (Especificar Arquivo JSON)")
        print("2. Metricas")
        print("0. Sair")
        
        escolha = input("Escolha uma opção: ")
        
        if escolha == "1":
            interpretar_tarefas(server)
        elif escolha == "2":
            apresentar_metricas(server)
        elif escolha == "0":
            print("Encerrando o programa. Até logo!")
            server.stop_server()
            break
        else:
            print("Opção inválida. Tente novamente.")

if __name__ == "__main__": 
    main()