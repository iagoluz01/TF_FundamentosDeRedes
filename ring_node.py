#!/usr/bin/env python3
"""UDP token-ring simulator.

Each process represents one machine in the logical ring. All machines listen on
UDP port 6000 and exchange the packet formats required by the assignment:
DISCOVER, HELLO, TOKEN and DATA.
"""

from __future__ import annotations

import argparse
import ipaddress
import random
import socket
import sys
import threading
import time
import zlib
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional, Tuple


DEFAULT_PORT = 6000

DISCOVER = "10"
HELLO = "20"
TOKEN = "1000"
DATA = "2000"

STATUS_UNKNOWN = "maquinainexistente"
STATUS_ACK = "ACK"
STATUS_NAK = "NAK"
BROADCAST_NICK = "BROADCAST"


def parse_float(value: str) -> float:
    return float(value.strip().replace(",", "."))


def crc32_text(text: str) -> int:
    return zlib.crc32(text.encode("utf-8")) & 0xFFFFFFFF


def local_ip() -> str:
    """Best-effort local IPv4 used in DISCOVER/HELLO packets."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))
            return probe.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"



def sanitize_ip(ip: str) -> str:
    ip = ip.strip()

    if ":" in ip:
        candidate = ip.split(":", 1)[0]
        try:
            ipaddress.ip_address(candidate)
            return candidate
        except ValueError:
            pass

    return ip


def corrupt_message(message: str) -> str:
    """Change one character after CRC calculation to simulate transmission error."""
    if not message:
        return "#"
    pos = random.randrange(len(message))
    replacement = "?" if message[pos] != "?" else "!"
    return message[:pos] + replacement + message[pos + 1 :]


@dataclass
class Config:
    nickname: str
    hop_delay: float
    error_rate: float
    token_timeout: float
    min_token_interval: float

    @classmethod
    def from_file(cls, path: str) -> "Config":
        """Read the five-line configuration file described in the assignment."""
        with open(path, "r", encoding="utf-8-sig") as cfg:
            lines = [
                line.strip()
                for line in cfg
                if line.strip() and not line.strip().startswith("#")
            ]

        if len(lines) < 5:
            raise ValueError(
                "Config must have 5 non-empty lines: nickname, hop delay, "
                "error probability, token timeout, minimum token interval."
            )

        nickname = lines[0].upper()
        if nickname == BROADCAST_NICK or ":" in nickname or not nickname:
            raise ValueError("Invalid nickname.")

        raw_probability = parse_float(lines[2])
        error_rate = raw_probability if raw_probability <= 1 else raw_probability / 100
        error_rate = max(0.0, min(1.0, error_rate))

        return cls(
            nickname=nickname,
            hop_delay=max(0.0, parse_float(lines[1])),
            error_rate=error_rate,
            token_timeout=max(0.1, parse_float(lines[3])),
            min_token_interval=max(0.0, parse_float(lines[4])),
        )


@dataclass
class Peer:
    nickname: str
    ip: str
    last_seen: float


@dataclass
class MessageItem:
    destination: str
    message: str
    retries: int = 0


@dataclass
class DataPacket:
    origin: str
    destination: str
    status: str
    crc: int
    message: str

    @classmethod
    def parse(cls, raw: str) -> "DataPacket":
        parts = raw.split(":", 5)
        if len(parts) != 6 or parts[0] != DATA:
            raise ValueError("Malformed data packet.")
        return cls(
            origin=parts[1].upper(),
            destination=parts[2].upper(),
            status=parts[3],
            crc=int(parts[4]),
            message=parts[5],
        )

    def wire(self) -> str:
        return (
            f"{DATA}:{self.origin}:{self.destination}:"
            f"{self.status}:{self.crc}:{self.message}"
        )


class RingNode:
    def __init__(
        self,
        config: Config,
        bind_ip: str,
        advertise_ip: str,
        broadcast_ip: str,
        port: int,
        discovery_wait: float,
    ) -> None:
        self.config = config
        self.bind_ip = bind_ip
        self.advertise_ip = advertise_ip
        self.broadcast_ip = broadcast_ip
        self.port = port
        self.discovery_wait = discovery_wait

        self.stop_event = threading.Event()
        self.print_lock = threading.Lock()
        self.peer_lock = threading.RLock()
        self.queue_lock = threading.RLock()
        self.send_lock = threading.Lock()
        self.token_lock = threading.Lock()
        self.in_flight_lock = threading.Lock()

        self.peers: Dict[str, Peer] = {}
        self.queue: Deque[MessageItem] = deque()
        self.drop_next_token = False
        self.in_flight: Optional[MessageItem] = None
        self.last_controller_token_time: Optional[float] = None
        self.last_token_target: Optional[str] = None

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except OSError:
                pass
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind((bind_ip, port))
        self.sock.settimeout(0.5)

        # The local machine is always part of its own view of the ring.
        self.add_peer(config.nickname, advertise_ip, quiet=True)

    def log(self, message: str) -> None:
        with self.print_lock:
            now = time.strftime("%H:%M:%S")
            print(f"[{now}] {message}", flush=True)

    def add_peer(self, nickname: str, ip: str, quiet: bool = False) -> None:
        nickname = nickname.upper()
        ip = sanitize_ip(ip)
        if not nickname or nickname == BROADCAST_NICK:
            return

        changed = False
        with self.peer_lock:
            old = self.peers.get(nickname)
            if old is None or old.ip != ip:
                changed = True
            self.peers[nickname] = Peer(nickname, ip, time.monotonic())

        if changed and not quiet:
            self.log(f"Maquina ativa: {nickname} ({ip}). Anel: {self.ring_text()}")

    def mark_peer_seen_by_ip(self, ip: str) -> None:
        with self.peer_lock:
            for peer in self.peers.values():
                if peer.ip == ip:
                    peer.last_seen = time.monotonic()
                    return

    def remove_peer(self, nickname: str) -> None:
        nickname = nickname.upper()
        if nickname == self.config.nickname:
            self.log("A maquina local nao pode ser removida do proprio anel.")
            return

        with self.peer_lock:
            removed = self.peers.pop(nickname, None)

        if removed is None:
            self.log(f"Maquina {nickname} nao encontrada.")
        else:
            self.log(f"Maquina {nickname} removida. Anel: {self.ring_text()}")

    def ordered_nicks(self) -> list[str]:
        with self.peer_lock:
            return sorted(self.peers)

    def ring_text(self) -> str:
        nicks = self.ordered_nicks()
        if not nicks:
            return "(vazio)"
        return " -> ".join(nicks + [nicks[0]])

    def is_controller(self) -> bool:
        nicks = self.ordered_nicks()
        return bool(nicks) and nicks[0] == self.config.nickname

    def successor(self) -> Peer:
        """Return the next machine in alphabetical circular order."""
        with self.peer_lock:
            if self.config.nickname not in self.peers:
                self.peers[self.config.nickname] = Peer(
                    self.config.nickname, self.advertise_ip, time.monotonic()
                )
            nicks = sorted(self.peers)
            index = nicks.index(self.config.nickname)
            successor_nick = nicks[(index + 1) % len(nicks)]
            return self.peers[successor_nick]

    def send_raw(self, payload: str, ip: str) -> None:
        ip = sanitize_ip(ip)

        try:
            socket.gethostbyname(ip)
        except socket.gaierror:
            self.log(f"Endereco invalido ignorado: {ip}")
            return

        encoded = payload.encode("utf-8")
        with self.send_lock:
            self.sock.sendto(encoded, (ip, self.port))

    def broadcast_raw(self, payload: str) -> None:
        encoded = payload.encode("utf-8")
        with self.send_lock:
            self.sock.sendto(encoded, (self.broadcast_ip, self.port))

    def send_discover(self) -> None:
        payload = f"{DISCOVER}:{self.config.nickname}:{self.advertise_ip}"
        self.broadcast_raw(payload)
        self.log(f"DISCOVER enviado: {payload}")

    def send_hello(self) -> None:
        payload = f"{HELLO}:{self.config.nickname}:{self.advertise_ip}"
        self.broadcast_raw(payload)
        self.log(f"HELLO enviado: {payload}")

    def delay(self) -> None:
        if self.config.hop_delay:
            time.sleep(self.config.hop_delay)

    def send_token_to_successor(self, reason: str) -> None:
        successor = self.successor()
        self.delay()
        self.send_raw(TOKEN, successor.ip)
        with self.token_lock:
            self.last_token_target = successor.nickname
        self.log(f"TOKEN -> {successor.nickname} ({reason})")

        if self.is_controller():
            with self.token_lock:
                self.last_controller_token_time = time.monotonic()

    def forward_token(self) -> None:
        self.send_token_to_successor("encaminhado")

    def generate_token(self, reason: str) -> None:
        self.send_token_to_successor(reason)

    def build_packet(self, item: MessageItem) -> Tuple[DataPacket, bool]:
        """Create a DATA packet and optionally inject an error after CRC32."""
        message = item.message
        packet = DataPacket(
            origin=self.config.nickname,
            destination=item.destination,
            status=STATUS_UNKNOWN,
            crc=crc32_text(item.message),
            message=message,
        )

        should_inject_error = (
            item.retries == 0 and random.random() < self.config.error_rate
        )
        if should_inject_error:
            packet.message = corrupt_message(packet.message)
        return packet, should_inject_error

    def send_data_to_successor(self, packet: DataPacket, reason: str) -> None:
        successor = self.successor()
        self.delay()
        self.send_raw(packet.wire(), successor.ip)
        self.log(
            f"DADOS {packet.origin}->{packet.destination} "
            f"[{packet.status}] -> {successor.nickname} ({reason})"
        )

    def handle_token(self, sender: Tuple[str, int]) -> None:
        now = time.monotonic()
        self.log(f"TOKEN recebido de {sender[0]}")

        # The first machine in the ring controls loss and duplicate-token cases.
        if self.is_controller():
            with self.token_lock:
                last_seen = self.last_controller_token_time
                if (
                    last_seen is not None
                    and now - last_seen < self.config.min_token_interval
                ):
                    self.log(
                        "Mais de um token detectado: intervalo menor que o minimo. "
                        "Token atual removido."
                    )
                    return
                self.last_controller_token_time = now

        if self.drop_next_token:
            self.drop_next_token = False
            self.log("Token removido por comando local.")
            return

        with self.in_flight_lock:
            if self.in_flight is not None:
                self.log(
                    "Token recebido enquanto ha dados locais em circulacao. "
                    "Token extra removido."
                )
                return

        with self.queue_lock:
            item = self.queue[0] if self.queue else None

        if item is None:
            self.forward_token()
            return

        # Keep the queued item until ACK, maquinainexistente, or final NAK.
        packet, injected_error = self.build_packet(item)
        with self.in_flight_lock:
            self.in_flight = item

        if injected_error:
            self.log("Falha inserida aleatoriamente antes do envio dos dados.")
        elif item.retries:
            self.log("Retransmissao sem insercao de falha.")

        self.send_data_to_successor(packet, "mensagem da fila")

    def handle_data(self, raw: str) -> None:
        try:
            packet = DataPacket.parse(raw)
        except ValueError as exc:
            self.log(f"Pacote de dados invalido ignorado: {exc}")
            return

        # Origin sees the DATA packet only after it has gone around the ring.
        if packet.origin == self.config.nickname:
            self.handle_returned_data(packet)
        elif packet.destination == BROADCAST_NICK:
            self.handle_broadcast_data(packet)
        elif packet.destination == self.config.nickname:
            self.handle_data_for_me(packet)
        else:
            self.log(
                f"DADOS passando por aqui: {packet.origin}->{packet.destination} "
                f"[{packet.status}]"
            )
            self.send_data_to_successor(packet, "encaminhado")

    def handle_data_for_me(self, packet: DataPacket) -> None:
        calculated_crc = crc32_text(packet.message)
        ok = calculated_crc == packet.crc
        packet.status = STATUS_ACK if ok else STATUS_NAK

        if ok:
            self.log(f"Mensagem recebida de {packet.origin}: {packet.message}")
            self.log("CRC correto. Marcando pacote como ACK.")
        else:
            self.log(
                f"Mensagem com erro recebida de {packet.origin}: {packet.message}"
            )
            self.log(
                f"CRC incorreto. Esperado {packet.crc}, calculado {calculated_crc}. "
                "Marcando pacote como NAK."
            )

        self.send_data_to_successor(packet, "resposta do destino")

    def handle_broadcast_data(self, packet: DataPacket) -> None:
        calculated_crc = crc32_text(packet.message)
        state = "CRC correto" if calculated_crc == packet.crc else "CRC incorreto"
        self.log(f"BROADCAST de {packet.origin} ({state}): {packet.message}")
        packet.status = STATUS_UNKNOWN
        self.send_data_to_successor(packet, "broadcast")

    def handle_returned_data(self, packet: DataPacket) -> None:
        with self.in_flight_lock:
            self.in_flight = None

        # Only after DATA returns to the origin can the token be released again.
        with self.queue_lock:
            item = self.queue[0] if self.queue else None
            matches_queue_head = (
                item is not None
                and item.destination == packet.destination
                and crc32_text(item.message) == packet.crc
            )

            if item is None:
                if packet.destination == BROADCAST_NICK and packet.status == STATUS_UNKNOWN:
                    self.log("Broadcast completou a volta no anel.")
                else:
                    self.log(
                        "Pacote retornado para a origem, mas nao ha mensagem "
                        "pendente na fila local."
                    )
            elif not matches_queue_head:
                self.log(
                    "Pacote retornado nao corresponde ao primeiro item da fila. "
                    "Fila mantida sem alteracao."
                )
            elif packet.status == STATUS_ACK:
                self.queue.popleft()
                self.log(
                    f"ACK recebido para {packet.destination}. "
                    "Mensagem removida da fila."
                )
            elif packet.status == STATUS_NAK:
                if item.retries < 1:
                    item.retries += 1
                    self.log(
                        f"NAK recebido para {packet.destination}. "
                        "A mensagem sera retransmitida uma vez na proxima "
                        "passagem do token."
                    )
                else:
                    self.queue.popleft()
                    self.log(
                        f"NAK recebido novamente para {packet.destination}. "
                        "Mensagem descartada apos uma retransmissao."
                    )
            elif packet.status == STATUS_UNKNOWN:
                self.queue.popleft()
                if packet.destination == BROADCAST_NICK:
                    self.log("Broadcast completou a volta no anel.")
                else:
                    self.log(
                        f"Maquina destino inexistente: {packet.destination}. "
                        "Mensagem removida da fila."
                    )
            else:
                self.log(f"Controle de erro desconhecido: {packet.status}")

        self.forward_token()

    def handle_discover(self, raw: str) -> None:
        parts = raw.split(":", 2)
        if len(parts) != 3:
            self.log(f"DISCOVER invalido ignorado: {raw}")
            return

        nickname, ip = parts[1].upper(), parts[2]
        self.add_peer(nickname, ip)
        if nickname != self.config.nickname:
            self.log(f"DISCOVER recebido de {nickname}.")
            self.send_hello()

    def handle_hello(self, raw: str) -> None:
        parts = raw.split(":", 2)
        if len(parts) != 3:
            self.log(f"HELLO invalido ignorado: {raw}")
            return

        nickname, ip = parts[1].upper(), parts[2]
        self.add_peer(nickname, ip)
        if nickname != self.config.nickname:
            self.log(f"HELLO recebido de {nickname}.")

    def receiver_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                data, sender = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                if not self.stop_event.is_set():
                    self.log("Socket fechado inesperadamente.")
                break

            raw = data.decode("utf-8", errors="replace").strip()
            if not raw:
                continue

            self.mark_peer_seen_by_ip(sender[0])

            if raw == TOKEN:
                self.handle_token(sender)
            elif raw.startswith(f"{DATA}:"):
                self.handle_data(raw)
            elif raw.startswith(f"{DISCOVER}:"):
                self.handle_discover(raw)
            elif raw.startswith(f"{HELLO}:"):
                self.handle_hello(raw)
            else:
                self.log(f"Pacote desconhecido ignorado de {sender[0]}: {raw}")

    def watchdog_loop(self) -> None:
        sleep_time = max(0.2, min(1.0, self.config.token_timeout / 4))
        while not self.stop_event.is_set():
            time.sleep(sleep_time)
            if not self.is_controller():
                continue

            with self.token_lock:
                last_seen = self.last_controller_token_time

            if last_seen is None:
                continue

            elapsed = time.monotonic() - last_seen
            if elapsed > self.config.token_timeout:
                with self.token_lock:
                    last_target = self.last_token_target or "desconhecido"
                self.log(
                    f"Token perdido: timeout de {self.config.token_timeout:.2f}s "
                    f"atingido. Ultimo envio foi para {last_target}. "
                    "Gerando novo token."
                )
                self.generate_token("timeout")

    def enqueue_message(self, destination: str, message: str) -> None:
        destination = destination.upper()
        if not destination or ":" in destination:
            self.log("Destino invalido.")
            return
        if not message:
            self.log("Mensagem vazia nao foi adicionada.")
            return

        with self.queue_lock:
            if len(self.queue) >= 10:
                self.log("Fila cheia: limite de 10 mensagens.")
                return
            self.queue.append(MessageItem(destination, message))
            self.log(
                f"Mensagem adicionada na fila para {destination}. "
                f"Tamanho da fila: {len(self.queue)}/10."
            )

    def print_queue(self) -> None:
        with self.queue_lock:
            if not self.queue:
                self.log("Fila vazia.")
                return
            self.log("Fila de mensagens:")
            for index, item in enumerate(self.queue, start=1):
                retry = " retry" if item.retries else ""
                self.log(f"  {index}. {item.destination}{retry}: {item.message}")

    def print_peers(self) -> None:
        with self.peer_lock:
            if not self.peers:
                self.log("Nenhuma maquina conhecida.")
                return
            self.log(f"Anel: {self.ring_text()}")
            for peer in sorted(self.peers.values(), key=lambda item: item.nickname):
                age = time.monotonic() - peer.last_seen
                self.log(f"  {peer.nickname}: {peer.ip} (visto ha {age:.1f}s)")

    def print_help(self) -> None:
        help_text = """
Comandos:
  send <DESTINO> <mensagem>      adiciona mensagem unicast na fila
  broadcast <mensagem>           adiciona mensagem broadcast na fila
  token add                      gera um token agora
  token remove                   remove o proximo token que passar aqui
  peer add <APELIDO> <IP>        adiciona/atualiza maquina conhecida
  peer remove <APELIDO>          remove maquina conhecida
  discover                       envia DISCOVER novamente
  peers                          mostra maquinas conhecidas e anel
  queue                          mostra fila local
  help                           mostra esta ajuda
  quit                           encerra
"""
        with self.print_lock:
            print(help_text.strip(), flush=True)

    def handle_command(self, line: str) -> None:
        command, _, rest = line.partition(" ")
        command = command.lower()
        rest = rest.strip()

        if command in {"send", "msg"}:
            destination, _, message = rest.partition(" ")
            if not destination or not message:
                self.log("Uso: send <DESTINO> <mensagem>")
                return
            self.enqueue_message(destination, message)
        elif command in {"broadcast", "bc"}:
            self.enqueue_message(BROADCAST_NICK, rest)
        elif command == "token":
            action = rest.lower()
            if action in {"add", "gerar", "generate"}:
                self.generate_token("comando local")
            elif action in {"remove", "remover", "drop"}:
                self.drop_next_token = True
                self.log("O proximo token recebido por esta maquina sera removido.")
            else:
                self.log("Uso: token add | token remove")
        elif command in {"addtoken", "gerartoken"}:
            self.generate_token("comando local")
        elif command in {"removetoken", "retirartoken"}:
            self.drop_next_token = True
            self.log("O proximo token recebido por esta maquina sera removido.")
        elif command == "peer":
            action, _, args = rest.partition(" ")
            action = action.lower()
            if action in {"add", "adicionar"}:
                nickname, _, ip = args.strip().partition(" ")
                if not nickname or not ip:
                    self.log("Uso: peer add <APELIDO> <IP>")
                    return
                self.add_peer(nickname, ip)
            elif action in {"remove", "remover", "drop"}:
                nickname = args.strip()
                if not nickname:
                    self.log("Uso: peer remove <APELIDO>")
                    return
                self.remove_peer(nickname)
            else:
                self.log("Uso: peer add <APELIDO> <IP> | peer remove <APELIDO>")
        elif command == "discover":
            self.send_discover()
        elif command == "peers":
            self.print_peers()
        elif command == "queue":
            self.print_queue()
        elif command == "help":
            self.print_help()
        elif command in {"quit", "exit"}:
            self.stop()
        else:
            self.log("Comando desconhecido. Digite help.")

    def cli_loop(self) -> None:
        self.print_help()
        while not self.stop_event.is_set():
            try:
                line = input("> ").strip()
            except EOFError:
                self.stop()
                break
            except KeyboardInterrupt:
                self.stop()
                break

            if line:
                self.handle_command(line)

    def start(self) -> None:
        self.log(
            f"Iniciando maquina {self.config.nickname} em {self.advertise_ip}:"
            f"{self.port}. Broadcast: {self.broadcast_ip}. "
            f"Probabilidade de erro: {self.config.error_rate:.0%}."
        )

        threading.Thread(target=self.receiver_loop, daemon=True).start()
        threading.Thread(target=self.watchdog_loop, daemon=True).start()

        self.send_discover()
        time.sleep(self.discovery_wait)

        if self.is_controller():
            self.log("Esta maquina e a primeira do anel. Gerando token inicial.")
            self.generate_token("inicial")
        else:
            self.log(f"Aguardando token. Anel atual: {self.ring_text()}")

        self.cli_loop()

    def stop(self) -> None:
        self.stop_event.set()
        try:
            self.sock.close()
        except OSError:
            pass
        self.log("Encerrado.")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simulador de rede local em anel.")
    parser.add_argument("config", help="arquivo de configuracao")
    parser.add_argument(
        "--bind-ip",
        default="",
        help="IP local para bind do UDP; padrao: todas as interfaces",
    )
    parser.add_argument(
        "--advertise-ip",
        default=None,
        help="IP anunciado nos pacotes DISCOVER/HELLO; padrao: detectado",
    )
    parser.add_argument(
        "--broadcast-ip",
        default="255.255.255.255",
        help="endereco de broadcast UDP; padrao: 255.255.255.255",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help="porta UDP usada por todos os pacotes; padrao: 6000",
    )
    parser.add_argument(
        "--discovery-wait",
        type=float,
        default=3.0,
        help="segundos aguardando HELLO antes do token inicial",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()

    try:
        config = Config.from_file(args.config)
        node = RingNode(
            config=config,
            bind_ip=args.bind_ip,
            advertise_ip=args.advertise_ip or local_ip(),
            broadcast_ip=args.broadcast_ip,
            port=args.port,
            discovery_wait=max(0.0, args.discovery_wait),
        )
        node.start()
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
