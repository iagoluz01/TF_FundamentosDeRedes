import random
from network.crc_service import CRCService


class FaultInjector:
    """Módulo para injetar falhas aleatoriamente nas mensagens"""

    def __init__(self, error_probability: float):
        """
        Args:
            error_probability: Probabilidade de inserir erro (0-100)
        """
        self.error_probability = error_probability

    def inject_error(self, message: str) -> str:
        """
        Injeta erro aleatoriamente na mensagem baseado na probabilidade
        
        Args:
            message: Mensagem original
            
        Returns:
            Mensagem com possível erro injetado
        """
        if random.random() * 100 < self.error_probability:
            # Injeta erro modificando um caractere aleatório
            if len(message) > 0:
                message_list = list(message)
                random_index = random.randint(0, len(message_list) - 1)
                # Inverte o bit de um caractere
                message_list[random_index] = chr(ord(message_list[random_index]) ^ 0x01)
                return ''.join(message_list)
        return message

    def has_error(self, data: str, crc: int) -> bool:
        """
        Verifica se há erro na mensagem comparando CRC
        
        Args:
            data: Dados a verificar
            crc: CRC esperado
            
        Returns:
            True se houver erro, False caso contrário
        """
        calculated_crc = CRCService.calculate_crc(data)
        return calculated_crc != crc
