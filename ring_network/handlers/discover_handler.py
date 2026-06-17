import threading
from network.packet import DiscoverPacket, HelloPacket
from utils.logger import Logger


class DiscoverHandler:
    """Handler para processar mensagens DISCOVER"""
    
    def __init__(self, udp_service, config, topology_manager):
        self.udp_service = udp_service
        self.config = config
        self.topology_manager = topology_manager
        self.logger = Logger()
    
    def handle(self, packet_data: str, sender_ip: str):
        """Processa um pacote DISCOVER recebido"""
        try:
            packet = DiscoverPacket.deserialize(packet_data)
            self.logger.info(f"DISCOVER recebido de {packet.nickname} ({sender_ip})", self.config.nickname)

            # Use sender_ip from UDP (actual source IP, not self-reported)
            self.topology_manager.add_machine(packet.nickname, sender_ip)

            # Respond with HELLO advertising own nickname
            hello_packet = HelloPacket(self.config.nickname, sender_ip)
            self.udp_service.broadcast(hello_packet.serialize())
            self.logger.info(f"HELLO enviado para {packet.nickname}", self.config.nickname)
            
        except Exception as e:
            self.logger.error(f"Erro ao processar DISCOVER: {e}", self.config.nickname)
