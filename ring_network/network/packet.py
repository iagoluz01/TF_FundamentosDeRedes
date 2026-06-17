from enum import Enum
from dataclasses import dataclass


class PacketType(Enum):
	DISCOVER = 10
	HELLO = 20
	TOKEN = 1000
	DATA = 2000


@dataclass
class Packet:
	"""Classe base para pacotes"""
	packet_type: PacketType

	def serialize(self) -> str:
		raise NotImplementedError

	@staticmethod
	def deserialize(data: str) -> 'Packet':
		raise NotImplementedError


@dataclass
class DiscoverPacket(Packet):
	"""Pacote DISCOVER: 10:<apelido>:<IP>"""
	nickname: str
	ip: str

	def __init__(self, nickname: str, ip: str):
		super().__init__(PacketType.DISCOVER)
		self.nickname = nickname
		self.ip = ip

	def serialize(self) -> str:
		return f"10:{self.nickname}:{self.ip}"

	@staticmethod
	def deserialize(data: str) -> 'DiscoverPacket':
		parts = data.split(':')
		if len(parts) >= 3 and parts[0] == '10':
			return DiscoverPacket(parts[1], parts[2])
		raise ValueError("Invalid DISCOVER packet format")


@dataclass
class HelloPacket(Packet):
	"""Pacote HELLO: 20:<apelido>:<IP>"""
	nickname: str
	ip: str

	def __init__(self, nickname: str, ip: str):
		super().__init__(PacketType.HELLO)
		self.nickname = nickname
		self.ip = ip

	def serialize(self) -> str:
		return f"20:{self.nickname}:{self.ip}"

	@staticmethod
	def deserialize(data: str) -> 'HelloPacket':
		parts = data.split(':')
		if len(parts) >= 3 and parts[0] == '20':
			return HelloPacket(parts[1], parts[2])
		raise ValueError("Invalid HELLO packet format")


@dataclass
class TokenPacket(Packet):
	"""Pacote TOKEN: 1000"""

	def __init__(self):
		super().__init__(PacketType.TOKEN)

	def serialize(self) -> str:
		return "1000"

	@staticmethod
	def deserialize(data: str) -> 'TokenPacket':
		if data.strip() == "1000":
			return TokenPacket()
		raise ValueError("Invalid TOKEN packet format")


@dataclass
class DataPacket(Packet):
	"""Pacote DATA: 2000:<origem>:<destino>:<status>:<CRC>:<mensagem>"""
	origin: str
	destination: str
	status: str
	crc: int
	message: str

	def __init__(self, origin: str, destination: str, status: str, crc: int, message: str):
		super().__init__(PacketType.DATA)
		self.origin = origin
		self.destination = destination
		self.status = status
		self.crc = crc
		self.message = message

	def serialize(self) -> str:
		return f"2000:{self.origin}:{self.destination}:{self.status}:{self.crc}:{self.message}"

	@staticmethod
	def deserialize(data: str) -> 'DataPacket':
		parts = data.split(':', 5)
		if len(parts) >= 6 and parts[0] == '2000':
			return DataPacket(
				origin=parts[1],
				destination=parts[2],
				status=parts[3],
				crc=int(parts[4]),
				message=parts[5]
			)
		raise ValueError("Invalid DATA packet format")