import threading
import time
from network.packet import TokenPacket
from utils.logger import Logger


class TokenManager:
    """Gerencia o ciclo de vida do token (geração, timeout, detecção de duplicatas)"""
    
    def __init__(self, config, ring_manager, udp_service, topology_manager):
        self.config = config
        self.ring_manager = ring_manager
        self.udp_service = udp_service
        self.topology_manager = topology_manager
        self.logger = Logger()
        self.is_token_generator = False
        self.last_token_time = None
        self.token_lock = threading.Lock()
        self.running = False
        self.monitor_thread = None
    
    def set_as_token_generator(self, is_generator: bool):
        """Define se esta máquina é geradora de token"""
        self.is_token_generator = is_generator
        if is_generator:
            self.logger.info("Esta máquina é geradora de token", self.config.nickname)
    
    def start_token_monitor(self):
        """Inicia o monitor de token"""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Monitor de token iniciado", self.config.nickname)
    
    def _monitor_loop(self):
        """Loop de monitoramento do token"""
        while self.running and self.is_token_generator:
            try:
                time.sleep(self.config.token_timeout / 2)

                should_generate = False
                lost = False

                with self.token_lock:
                    if self.last_token_time is not None:
                        elapsed = time.time() - self.last_token_time
                        if elapsed > self.config.token_timeout:
                            lost = True
                            should_generate = True
                    else:
                        # Primeira vez — gera o token inicial
                        if not hasattr(self, '_first_token_sent'):
                            self._first_token_sent = True
                            should_generate = True

                if lost:
                    self.logger.warning(
                        f"Token perdido! Timeout de {self.config.token_timeout}s excedido",
                        self.config.nickname,
                    )
                if should_generate:
                    self.generate_token()

            except Exception as e:
                if self.running:
                    self.logger.error(f"Erro no monitor de token: {e}", self.config.nickname)
    
    def generate_token(self):
        """Gera um novo token"""
        try:
            with self.token_lock:
                self.last_token_time = time.time()
            
            token = TokenPacket()
            next_machine = self.ring_manager.get_next_machine()
            
            if next_machine:
                self.udp_service.send(token.serialize(), next_machine.ip)
                self.logger.info(f"Token gerado e enviado para {next_machine.nickname}", self.config.nickname)
        except Exception as e:
            self.logger.error(f"Erro ao gerar token: {e}", self.config.nickname)
    
    def token_received(self):
        """Registra recebimento de um token"""
        with self.token_lock:
            self.last_token_time = time.time()
    
    def remove_token(self):
        """Remove o token da rede (descarta quando chega)"""
        self.logger.info("Token removido da rede", self.config.nickname)
    
    def stop(self):
        """Para o monitor de token"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
