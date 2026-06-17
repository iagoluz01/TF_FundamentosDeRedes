class Machine:
    """Representa uma máquina na rede"""
    
    def __init__(self, nickname: str, ip: str):
        self.nickname = nickname
        self.ip = ip

    def __str__(self):
        return f"Machine({self.nickname}: {self.ip})"

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if isinstance(other, Machine):
            return self.nickname == other.nickname
        return False

    def __hash__(self):
        return hash(self.nickname)