from network.packet import DataPacket, TokenPacket
from network.crc_service import CRCService
from utils.logger import Logger


class DataHandler:
    """Handler para processar mensagens de dados"""

    def __init__(self, udp_service, config, ring_manager):
        self.udp_service = udp_service
        self.config = config
        self.ring_manager = ring_manager
        self.logger = Logger()

    def handle(self, packet_data: str, sender_ip: str):
        """Processa um pacote de dados recebido"""
        try:
            packet = DataPacket.deserialize(packet_data)

            # Se for destinado a esta máquina: verifica CRC e define ACK/NAK
            if packet.destination == self.config.nickname:
                if CRCService.verify_crc(packet.message, packet.crc):
                    packet.status = "ACK"
                    self.logger.info(f"Mensagem de {packet.origin}: {packet.message}", self.config.nickname)
                else:
                    packet.status = "NAK"
                    self.logger.warning(f"Erro CRC na mensagem de {packet.origin}", self.config.nickname)

            # Se esta máquina é a origem, o pacote completou a volta no anel
            if packet.origin == self.config.nickname:
                if packet.status == "ACK":
                    self.logger.info(f"ACK de {packet.destination}", self.config.nickname)
                    self.ring_manager.mark_message_sent(packet.destination)
                elif packet.status == "NAK":
                    self.logger.warning(f"NAK de {packet.destination}", self.config.nickname)
                    self.ring_manager.mark_message_failed(packet.destination)
                elif packet.status == "maquinainexistente":
                    self.logger.warning(f"Máquina {packet.destination} não existe ou está desligada", self.config.nickname)
                    self.ring_manager.mark_machine_offline(packet.destination)

                # Passa o token para a próxima máquina após o dado retornar
                next_machine = self.ring_manager.get_next_machine()
                if next_machine:
                    self.udp_service.send(TokenPacket().serialize(), next_machine.ip)
                    self.logger.debug(f"Token passado para {next_machine.nickname} após retorno de dados", self.config.nickname)
            else:
                # Encaminha o pacote para a próxima máquina no anel
                next_machine = self.ring_manager.get_next_machine()
                if next_machine:
                    self.udp_service.send(packet.serialize(), next_machine.ip)

        except Exception as e:
            self.logger.error(f"Erro ao processar DATA: {e}", self.config.nickname)
