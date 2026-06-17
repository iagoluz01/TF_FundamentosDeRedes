from queue import Queue
from threading import Lock


class MessageQueue:
    """Fila de mensagens com capacidade máxima de 10"""
    
    def __init__(self, max_size: int = 10):
        self.queue = Queue(maxsize=max_size)
        self.lock = Lock()

    def add(self, message) -> bool:
        """Adiciona mensagem à fila"""
        try:
            self.queue.put_nowait(message)
            return True
        except:
            return False

    def next(self):
        """Retorna a próxima mensagem sem remover"""
        try:
            with self.lock:
                if not self.queue.empty():
                    return self.queue.queue[0]
            return None
        except:
            return None

    def remove(self):
        """Remove e retorna a próxima mensagem"""
        try:
            return self.queue.get_nowait()
        except:
            return None

    def is_empty(self) -> bool:
        """Verifica se fila está vazia"""
        return self.queue.empty()

    def size(self) -> int:
        """Retorna tamanho da fila"""
        return self.queue.qsize()