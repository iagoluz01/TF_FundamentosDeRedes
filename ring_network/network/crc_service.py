import zlib


class CRCService:
    """Serviço para cálculo e verificação de CRC32"""

    @staticmethod
    def calculate_crc(data: str) -> int:
        """Calcula CRC32 de uma string"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return zlib.crc32(data) & 0xffffffff

    @staticmethod
    def verify_crc(data: str, crc: int) -> bool:
        """Verifica se o CRC de uma string está correto"""
        calculated_crc = CRCService.calculate_crc(data)
        return calculated_crc == crc
