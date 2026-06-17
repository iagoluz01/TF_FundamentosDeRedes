import os
from dataclasses import dataclass
from typing import Optional
from utils.logger import Logger


@dataclass
class Config:
    """Configuração da máquina carregada do arquivo .conf"""
    nickname: str
    token_time: float
    error_probability: float
    token_timeout: float
    min_token_time: float

    @staticmethod
    def load_from_file(config_file: str = "config/maquina.conf") -> 'Config':
        """Carrega configuração do arquivo"""
        logger = Logger()
        
        if not os.path.exists(config_file):
            logger.error(f"Arquivo de configuração não encontrado: {config_file}")
            raise FileNotFoundError(f"Config file not found: {config_file}")

        try:
            with open(config_file, 'r') as f:
                lines = f.readlines()
                
            lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
            
            if len(lines) < 5:
                raise ValueError("Config file must have at least 5 lines")
            
            nickname = lines[0].strip()
            token_time = float(lines[1].strip())
            error_probability = float(lines[2].strip())
            token_timeout = float(lines[3].strip())
            min_token_time = float(lines[4].strip())
            
            config = Config(
                nickname=nickname,
                token_time=token_time,
                error_probability=error_probability,
                token_timeout=token_timeout,
                min_token_time=min_token_time
            )
            
            logger.info(f"Configuração carregada: {nickname}", nickname)
            return config
            
        except Exception as e:
            logger.error(f"Erro ao carregar configuração: {e}")
            raise