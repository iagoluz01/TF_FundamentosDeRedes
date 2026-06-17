from network.crc_service import CRCService


class Message:
    def __init__(self, origin, destination, text):
        self.origin = origin
        self.destination = destination
        self.text = text
        self.crc = CRCService.calculate_crc(text)
        self.retransmitted = False