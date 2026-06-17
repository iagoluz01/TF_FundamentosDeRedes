#!/usr/bin/env python
"""
Script de teste para validar a implementação da rede em anel
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from network.crc_service import CRCService
from network.packet import DiscoverPacket, HelloPacket, TokenPacket, DataPacket
from models.machine import Machine
from models.message import Message
from models.token import Token
from message_queue.message_queue import MessageQueue
from fault.fault_injector import FaultInjector
from utils.logger import Logger


def test_crc_service():
    """Testa serviço de CRC"""
    print("\n=== Teste de CRC Service ===")
    data = "Oi pessoal!"
    crc = CRCService.calculate_crc(data)
    print(f"CRC de '{data}': {crc}")
    print(f"Verificação OK: {CRCService.verify_crc(data, crc)}")
    
    # Testa com dado modificado
    wrong_crc = crc + 1
    print(f"Verificação com CRC errado: {CRCService.verify_crc(data, wrong_crc)}")
    assert CRCService.verify_crc(data, crc) == True
    assert CRCService.verify_crc(data, wrong_crc) == False
    print("✓ CRC Service OK")


def test_packets():
    """Testa serialização de pacotes"""
    print("\n=== Teste de Pacotes ===")
    
    # DISCOVER
    discover = DiscoverPacket("A", "192.168.1.100")
    discover_str = discover.serialize()
    print(f"DISCOVER: {discover_str}")
    assert discover_str == "10:A:192.168.1.100"
    discovered = DiscoverPacket.deserialize(discover_str)
    assert discovered.nickname == "A"
    
    # HELLO
    hello = HelloPacket("B", "192.168.1.101")
    hello_str = hello.serialize()
    print(f"HELLO: {hello_str}")
    assert hello_str == "20:B:192.168.1.101"
    
    # TOKEN
    token = TokenPacket()
    token_str = token.serialize()
    print(f"TOKEN: {token_str}")
    assert token_str == "1000"
    
    # DATA
    data = DataPacket("A", "B", "maquinainexistente", 12345, "Teste")
    data_str = data.serialize()
    print(f"DATA: {data_str}")
    assert "2000:A:B:maquinainexistente:12345:Teste" == data_str
    
    print("✓ Pacotes OK")


def test_models():
    """Testa modelos"""
    print("\n=== Teste de Modelos ===")
    
    # Machine
    machine = Machine("A", "192.168.1.100")
    print(f"Machine: {machine}")
    assert machine.nickname == "A"
    
    # Message
    msg = Message("A", "B", "Olá!")
    print(f"Message: {msg}")
    assert msg.origin == "A"
    assert msg.destination == "B"
    assert msg.crc == CRCService.calculate_crc("Olá!")
    
    # Token
    tok = Token()
    tok_str = tok.serialize()
    assert tok_str == "1000"
    
    print("✓ Modelos OK")


def test_message_queue():
    """Testa fila de mensagens"""
    print("\n=== Teste de Message Queue ===")
    
    queue = MessageQueue(max_size=3)
    
    # Teste de adição
    msg1 = Message("A", "B", "Msg1")
    msg2 = Message("A", "C", "Msg2")
    msg3 = Message("A", "D", "Msg3")
    
    assert queue.add(msg1) == True
    assert queue.add(msg2) == True
    assert queue.add(msg3) == True
    print(f"Fila com 3 mensagens: {queue.size()}")
    assert queue.size() == 3
    
    # Teste de capacidade máxima
    msg4 = Message("A", "E", "Msg4")
    assert queue.add(msg4) == False
    print("Fila cheia, rejeitou msg4")
    
    # Teste de remoção
    next_msg = queue.next()
    assert next_msg.destination == "B"
    removed = queue.remove()
    assert removed.destination == "B"
    assert queue.size() == 2
    
    print("✓ Message Queue OK")


def test_fault_injector():
    """Testa injetor de falhas"""
    print("\n=== Teste de Fault Injector ===")
    
    injector = FaultInjector(error_probability=50)  # 50% de erro
    
    original = "Teste sem erro"
    with_error = injector.inject_error(original)
    
    original_crc = CRCService.calculate_crc(original)
    
    # Com baixa probabilidade, pode não ter injetado erro
    if with_error != original:
        print(f"Erro injetado: '{original}' -> '{with_error}'")
        has_error = injector.has_error(with_error, original_crc)
        print(f"Erro detectado por CRC: {has_error}")
    else:
        print("Nenhum erro injetado desta vez (aleatório)")
    
    print("✓ Fault Injector OK")


def test_logger():
    """Testa logger"""
    print("\n=== Teste de Logger ===")
    
    logger = Logger()
    logger.info("Mensagem de INFO", "TESTE")
    logger.warning("Mensagem de WARNING", "TESTE")
    logger.error("Mensagem de ERROR", "TESTE")
    logger.debug("Mensagem de DEBUG", "TESTE")
    
    print("✓ Logger OK")


def run_all_tests():
    """Executa todos os testes"""
    print("\n" + "="*60)
    print("TESTES DA REDE EM ANEL")
    print("="*60)
    
    try:
        test_crc_service()
        test_packets()
        test_models()
        test_message_queue()
        test_fault_injector()
        test_logger()
        
        print("\n" + "="*60)
        print("✓ TODOS OS TESTES PASSARAM!")
        print("="*60 + "\n")
        return 0
    except AssertionError as e:
        print(f"\n✗ Teste falhou: {e}\n")
        return 1
    except Exception as e:
        print(f"\n✗ Erro inesperado: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
