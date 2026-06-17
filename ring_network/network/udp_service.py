import socket
import threading
from utils.logger import Logger


class UDPService:
    def __init__(self, listen_port=6000):
        self.listen_port = listen_port
        self.logger = Logger()
        self.callbacks = []
        self.running = False
        self.socket = None

    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.socket.bind(("0.0.0.0", self.listen_port))
        self.running = True
        thread = threading.Thread(target=self._receive_loop, daemon=True)
        thread.start()

    def _receive_loop(self):
        while self.running:
            try:
                self.socket.settimeout(1.0)
                data, addr = self.socket.recvfrom(1024)
                msg = data.decode('utf-8')
                for cb in self.callbacks:
                    threading.Thread(target=cb, args=(msg, addr[0]), daemon=True).start()
            except socket.timeout:
                pass
            except Exception as e:
                if self.running:
                    self.logger.error(f"UDP error: {e}")

    def send(self, message, ip, port=6000):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.sendto(message.encode(), (ip, port))
            s.close()
            return True
        except Exception as e:
            self.logger.error(f"Send error: {e}")
            return False

    def broadcast(self, message, port=6000):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(message.encode(), ("255.255.255.255", port))
            s.close()
            return True
        except Exception as e:
            self.logger.error(f"Broadcast error: {e}")
            return False

    def register_callback(self, callback):
        self.callbacks.append(callback)

    def stop(self):
        self.running = False
        if self.socket:
            self.socket.close()