import threading
from typing import List, Dict, Optional
from models.machine import Machine
from utils.logger import Logger


class TopologyManager:
    """Gerencia a topologia da rede (máquinas ativas)"""
    
    def __init__(self, config):
        self.config = config
        self.logger = Logger()
        self.machines: Dict[str, Machine] = {}
        self.lock = threading.Lock()
    
    def add_machine(self, nickname: str, ip: str) -> bool:
        """Adiciona uma máquina à topologia"""
        with self.lock:
            if nickname not in self.machines:
                machine = Machine(nickname, ip)
                self.machines[nickname] = machine
                self.logger.info(f"Máquina adicionada à topologia: {nickname} ({ip})", self.config.nickname)
                return True
            else:
                # Atualiza IP se mudou
                if self.machines[nickname].ip != ip:
                    self.machines[nickname].ip = ip
                    self.logger.info(f"IP atualizado para {nickname}: {ip}", self.config.nickname)
                return False
    
    def remove_machine(self, nickname: str) -> bool:
        """Remove uma máquina da topologia"""
        with self.lock:
            if nickname in self.machines:
                del self.machines[nickname]
                self.logger.info(f"Máquina removida da topologia: {nickname}", self.config.nickname)
                return True
            return False
    
    def get_machine(self, nickname: str) -> Optional[Machine]:
        """Obtém uma máquina pelo nickname"""
        with self.lock:
            return self.machines.get(nickname)
    
    def get_all_machines(self) -> List[Machine]:
        """Retorna todas as máquinas em ordem alfabética"""
        with self.lock:
            sorted_nicknames = sorted(self.machines.keys())
            return [self.machines[nick] for nick in sorted_nicknames]
    
    def get_sorted_nicknames(self) -> List[str]:
        """Retorna apelidos em ordem alfabética"""
        with self.lock:
            return sorted(self.machines.keys())
    
    def machine_exists(self, nickname: str) -> bool:
        """Verifica se uma máquina existe"""
        with self.lock:
            return nickname in self.machines
    
    def get_network_size(self) -> int:
        """Retorna quantidade de máquinas na rede"""
        with self.lock:
            return len(self.machines)
    
    def print_topology(self):
        """Imprime a topologia atual"""
        machines = self.get_all_machines()
        if machines:
            ips = " -> ".join([f"{m.nickname}" for m in machines])
            self.logger.info(f"Topologia: {ips}", self.config.nickname)
