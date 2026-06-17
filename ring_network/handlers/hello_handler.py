import threading
from network.packet import HelloPacket
from utils.logger import Logger


class HelloHandler:
    """Handler para processar mensagens HELLO"""
    
    def __init__(self, udp_service, config, topology_manager):
        self.udp_service = udp_service
        self.config = config
        self.topology_manager = topology_manager
        self.logger = Logger()
    
    def handle(self, packet_data: str, sender_ip: str):
        """Processa um pacote HELLO recebido"""
        try:
            packet = HelloPacket.deserialize(packet_data)
            self.logger.info(f"HELLO recebido de {packet.nickname} ({sender_ip})", self.config.nickname)

            # Use sender_ip from UDP (reliable actual source IP)
            self.topology_manager.add_machine(packet.nickname, sender_ip)
            
        except Exception as e:
            self.logger.error(f"Erro ao processar HELLO: {e}", self.config.nickname)
