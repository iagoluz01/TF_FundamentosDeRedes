import threading
import time
from typing import Optional
from models.machine import Machine
from message_queue.message_queue import MessageQueue
from utils.logger import Logger


class RingManager:
    """Gerencia o funcionamento do anel (próxima máquina, fila de mensagens)"""
    
    def __init__(self, config, topology_manager, udp_service):
        self.config = config
        self.topology_manager = topology_manager
        self.udp_service = udp_service
        self.logger = Logger()
        self.message_queue = MessageQueue(max_size=10)
        self.lock = threading.Lock()
        self.current_position = 0
    
    def get_next_machine(self) -> Optional[Machine]:
        """Retorna a próxima máquina no anel"""
        with self.lock:
            machines = self.topology_manager.get_all_machines()
            if not machines:
                return None
            
            # Encontra a posição atual
            try:
                current_index = next(i for i, m in enumerate(machines) if m.nickname == self.config.nickname)
            except StopIteration:
                return machines[0] if machines else None
            
            # Retorna a próxima
            next_index = (current_index + 1) % len(machines)
            return machines[next_index]
    
    def get_next_machine_after(self, nickname: str) -> Optional[Machine]:
        """Retorna a próxima máquina após um apelido específico"""
        with self.lock:
            machines = self.topology_manager.get_all_machines()
            if not machines:
                return None
            
            try:
                current_index = next(i for i, m in enumerate(machines) if m.nickname == nickname)
                next_index = (current_index + 1) % len(machines)
                return machines[next_index]
            except (StopIteration, ValueError):
                return machines[0] if machines else None
    
    def add_message(self, origin: str, destination: str, text: str) -> bool:
        """Adiciona uma mensagem à fila"""
        from models.message import Message
        message = Message(origin, destination, text)
        success = self.message_queue.add(message)
        if success:
            self.logger.info(f"Mensagem adicionada à fila: {destination}", self.config.nickname)
        else:
            self.logger.warning(f"Fila cheia! Mensagem não foi adicionada", self.config.nickname)
        return success
    
    def mark_message_sent(self, destination: str):
        """Marca mensagem como enviada com sucesso"""
        message = self.message_queue.remove()
        if message:
            self.logger.info(f"Mensagem para {destination} removida da fila", self.config.nickname)
    
    def mark_message_failed(self, destination: str):
        """Marca mensagem como falha (NAK) - mantém na fila"""
        self.logger.warning(f"Mensagem para {destination} falhou - será retentada", self.config.nickname)
    
    def mark_machine_offline(self, destination: str):
        """Marca máquina como offline e remove mensagem"""
        message = self.message_queue.remove()
        if message:
            self.logger.warning(f"Máquina {destination} offline - mensagem descartada", self.config.nickname)
    
    def has_pending_messages(self) -> bool:
        """Verifica se há mensagens pendentes"""
        return not self.message_queue.is_empty()
    
    def get_queue_size(self) -> int:
        """Retorna o tamanho atual da fila"""
        return self.message_queue.size()
