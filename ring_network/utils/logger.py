import threading
from datetime import datetime
from enum import Enum


class LogLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    DEBUG = "DEBUG"


class Logger:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(Logger, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._lock = threading.Lock()

    def log(self, message: str, level: LogLevel = LogLevel.INFO, machine: str = None):
        """Log uma mensagem com timestamp e máquina de origem"""
        with self._lock:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            if machine:
                print(f"[{timestamp}] [{level.value}] [{machine}] {message}")
            else:
                print(f"[{timestamp}] [{level.value}] {message}")

    def info(self, message: str, machine: str = None):
        self.log(message, LogLevel.INFO, machine)

    def warning(self, message: str, machine: str = None):
        self.log(message, LogLevel.WARNING, machine)

    def error(self, message: str, machine: str = None):
        self.log(message, LogLevel.ERROR, machine)

    def debug(self, message: str, machine: str = None):
        self.log(message, LogLevel.DEBUG, machine)
