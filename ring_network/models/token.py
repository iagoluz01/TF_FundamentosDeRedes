class Token:
    """Representa um token que circula na rede em anel"""

    def __init__(self):
        pass

    def serialize(self) -> str:
        """Serializa o token para envio"""
        return "1000"

    @staticmethod
    def deserialize(data: str) -> 'Token':
        """Desserializa um token recebido"""
        if data.strip() == "1000":
            return Token()
        raise ValueError("Invalid token format")
