import threading
import time
from network.packet import TokenPacket, DataPacket
from fault.fault_injector import FaultInjector
from utils.logger import Logger


class TokenHandler:
    """Handler para processar tokens"""

    def __init__(self, udp_service, config, ring_manager, token_manager=None):
        self.udp_service = udp_service
        self.config = config
        self.ring_manager = ring_manager
        self.token_manager = token_manager
        self.fault_injector = FaultInjector(config.error_probability)
        self.logger = Logger()
        self.last_token_time = None
        self.token_lock = threading.Lock()
        # Garante que apenas um token seja processado por vez
        self._processing = threading.Lock()

    def handle(self, packet_data: str, sender_ip: str):
        """Processa um token recebido"""
        # Descarta se já há um token em processamento nesta máquina
        if not self._processing.acquire(blocking=False):
            self.logger.debug("Token descartado: já há um em processamento", self.config.nickname)
            return
        try:
            self._process_token(packet_data, sender_ip)
        finally:
            self._processing.release()

    def _process_token(self, packet_data: str, sender_ip: str):
        try:
            TokenPacket.deserialize(packet_data)

            with self.token_lock:
                current_time = time.time()

                # Descarta token duplicado apenas quando há múltiplas máquinas
                # (em anel com 1 máquina, o token volta imediatamente e não é duplicata)
                network_size = self.ring_manager.topology_manager.get_network_size()
                if network_size > 1 and self.last_token_time and (current_time - self.last_token_time) < self.config.min_token_time:
                    self.logger.warning("Múltiplos tokens detectados! Descartando.", self.config.nickname)
                    return

                self.last_token_time = current_time

            self.logger.info("Token recebido", self.config.nickname)

            # Notifica o token_manager para resetar o timeout
            if self.token_manager:
                self.token_manager.token_received()

            # Envia mensagem pendente, se houver
            if not self.ring_manager.message_queue.is_empty():
                message = self.ring_manager.message_queue.next()
                if message:
                    # Injeta falha na transmissão (simula erros de canal)
                    transmitted_text = self.fault_injector.inject_error(message.text)
                    data_packet = DataPacket(
                        origin=self.config.nickname,
                        destination=message.destination,
                        status="maquinainexistente",
                        crc=message.crc,          # CRC do texto original
                        message=transmitted_text,  # texto possivelmente corrompido
                    )
                    next_machine = self.ring_manager.get_next_machine()
                    if next_machine:
                        self.udp_service.send(data_packet.serialize(), next_machine.ip)
                        self.logger.info(f"Enviando mensagem para {message.destination}", self.config.nickname)
                    return  # Segura o token até o dado retornar (data_handler passará o token)

            # Nenhuma mensagem — aguarda o hold time antes de passar o token
            # (token_time / N segundos por máquina para controlar velocidade de circulação)
            network_size = self.ring_manager.topology_manager.get_network_size()
            hold_time = self.config.token_time / max(1, network_size)
            time.sleep(hold_time)

            # Passa o token adiante
            next_machine = self.ring_manager.get_next_machine()
            if next_machine:
                self.udp_service.send(TokenPacket().serialize(), next_machine.ip)
                self.logger.debug(f"Token passado para {next_machine.nickname}", self.config.nickname)

        except Exception as e:
            self.logger.error(f"Erro ao processar token: {e}", self.config.nickname)
