import sys
import time
import threading
from config.config import Config
from network.udp_service import UDPService
from network.packet import DiscoverPacket, DataPacket
from ring.topology_manager import TopologyManager
from ring.ring_manager import RingManager
from ring.token_manager import TokenManager
from handlers.discover_handler import DiscoverHandler
from handlers.hello_handler import HelloHandler
from handlers.data_handler import DataHandler
from handlers.token_handler import TokenHandler
from utils.logger import Logger


class RingNetwork:
    def __init__(self):
        self.logger = Logger()
        self.config = None
        self.udp_service = None
        self.topology_manager = None
        self.ring_manager = None
        self.token_manager = None
        self.running = False
    
    def initialize(self):
        """Inicializa a aplicação"""
        try:
            # Carrega configuração
            self.config = Config.load_from_file()
            self.logger.info(f"Sistema iniciando: {self.config.nickname}", self.config.nickname)
            
            # Cria gerenciadores
            self.udp_service = UDPService(listen_port=6000)
            self.topology_manager = TopologyManager(self.config)
            self.ring_manager = RingManager(self.config, self.topology_manager, self.udp_service)
            self.token_manager = TokenManager(self.config, self.ring_manager, self.udp_service, self.topology_manager)
            
            # Cria handlers
            discover_handler = DiscoverHandler(self.udp_service, self.config, self.topology_manager)
            hello_handler = HelloHandler(self.udp_service, self.config, self.topology_manager)
            data_handler = DataHandler(self.udp_service, self.config, self.ring_manager)
            token_handler = TokenHandler(self.udp_service, self.config, self.ring_manager, self.token_manager)
            
            # Registra callbacks
            def packet_received(message, sender_ip):
                if message.startswith("10:"):
                    discover_handler.handle(message, sender_ip)
                elif message.startswith("20:"):
                    hello_handler.handle(message, sender_ip)
                elif message.startswith("2000:"):
                    data_handler.handle(message, sender_ip)
                elif message.startswith("1000"):
                    token_handler.handle(message, sender_ip)
            
            self.udp_service.register_callback(packet_received)
            
            # Inicia UDP service
            self.udp_service.start()
            self.logger.info("UDP service iniciado", self.config.nickname)
            
            # Envia DISCOVER
            discover_packet = DiscoverPacket(self.config.nickname, "127.0.0.1")
            self.udp_service.broadcast(discover_packet.serialize())
            self.logger.info("DISCOVER enviado em broadcast", self.config.nickname)
            
            # Aguarda descoberta de outras máquinas
            self.logger.info("Aguardando descoberta de máquinas...", self.config.nickname)
            time.sleep(3)
            
            # Adiciona a si mesma
            self.topology_manager.add_machine(self.config.nickname, "127.0.0.1")
            self.topology_manager.print_topology()
            
            # Define gerador de token se for a primeira máquina (ordem alfabética)
            sorted_nicknames = self.topology_manager.get_sorted_nicknames()
            if sorted_nicknames and sorted_nicknames[0] == self.config.nickname:
                self.token_manager.set_as_token_generator(True)
                self.logger.info("Esta máquina é geradora de token (primeira em ordem alfabética)", self.config.nickname)
            
            # Inicia monitor de token
            self.token_manager.start_token_monitor()
            
            self.running = True
            self.logger.info("Sistema pronto", self.config.nickname)
            
        except Exception as e:
            self.logger.error(f"Erro na inicialização: {e}")
            sys.exit(1)
    
    def run_interactive(self):
        """Interface interativa"""
        print("\n" + "="*60)
        print(f"REDE EM ANEL - Máquina: {self.config.nickname}")
        print("="*60)
        print("\nComandos disponíveis:")
        print("  m <destino> <mensagem>  - Enviar mensagem")
        print("  t                        - Gerar novo token")
        print("  r                        - Remover token")
        print("  s                        - Ver status")
        print("  q                        - Sair")
        print("="*60 + "\n")
        
        while self.running:
            try:
                cmd = input(f"[{self.config.nickname}]> ").strip()
                
                if cmd.startswith("m "):
                    parts = cmd[2:].split(" ", 1)
                    if len(parts) == 2:
                        destination, message = parts
                        self.ring_manager.add_message(self.config.nickname, destination, message)
                    else:
                        print("Uso: m <destino> <mensagem>")
                
                elif cmd == "t":
                    self.token_manager.set_as_token_generator(True)
                    self.token_manager.generate_token()
                
                elif cmd == "r":
                    self.token_manager.remove_token()
                
                elif cmd == "s":
                    self.print_status()
                
                elif cmd == "q":
                    self.running = False
                    print("Desligando...")
                
            except KeyboardInterrupt:
                self.running = False
                print("\nDesligando...")
    
    def print_status(self):
        """Imprime status da rede"""
        print("\n" + "-"*60)
        print("STATUS DA REDE")
        print("-"*60)
        
        machines = self.topology_manager.get_all_machines()
        print(f"Máquinas na rede ({len(machines)}):")
        for m in machines:
            print(f"  - {m.nickname}: {m.ip}")
        
        print(f"\nFila de mensagens: {self.ring_manager.get_queue_size()}/10")
        
        next_machine = self.ring_manager.get_next_machine()
        if next_machine:
            print(f"Próxima máquina no anel: {next_machine.nickname}")
        
        print("-"*60 + "\n")
    
    def shutdown(self):
        """Encerra a aplicação"""
        self.running = False
        self.token_manager.stop()
        self.udp_service.stop()
        self.logger.info("Sistema encerrado", self.config.nickname)


def main():
    try:
        network = RingNetwork()
        network.initialize()
        network.run_interactive()
    except Exception as e:
        Logger().error(f"Erro fatal: {e}")
    finally:
        if 'network' in locals():
            network.shutdown()


if __name__ == "__main__":
    main()