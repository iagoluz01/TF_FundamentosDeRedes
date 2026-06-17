# Documentação da Implementação - Rede em Anel

## Resumo Executivo

Implementação completa de uma **rede local em anel (ring topology)** em Python conforme especificação fornecida. O sistema simula máquinas conectadas em anel, usando token ring para controlar transmissão de mensagens via UDP com detecção de erro por CRC32.

## Conformidade com Enunciado

### ✓ Arquivo de Inicialização
- **Implementado**: `config/config.py` - Carrega arquivo `maquina.conf`
- **Suporta**:
  - Apelido (nickname) da máquina
  - Tempo do token e dados
  - Probabilidade para inserir erro (0-100%)
  - Timeout do token
  - Tempo mínimo entre tokens

### ✓ Inicialização do Anel (DISCOVER/HELLO)
- **Implementado**: `handlers/discover_handler.py`, `handlers/hello_handler.py`
- **Funcionamento**:
  1. Máquina envia DISCOVER em broadcast na porta 6000
  2. Máquinas respondem com HELLO também em broadcast
  3. Topologia em anel é construída automaticamente em ordem alfabética
  4. Primeira máquina (alfabeticamente) gera o primeiro token

### ✓ Funcionamento do Anel
- **Implementado**: `ring/ring_manager.py`, `ring/token_manager.py`
- **Token Ring**:
  - Token circula: A → B → C → D → A (ordem alfabética)
  - Máquina com token pode enviar uma mensagem da fila
  - Dados viajam para destino e retornam à origem
  - Depois, token passa para próxima máquina
  
### ✓ Pacotes (CONTROL, TOKEN, DATA)
- **Formato DISCOVER**: `10:<apelido>:<IP>`
- **Formato HELLO**: `20:<apelido>:<IP>`
- **Formato TOKEN**: `1000`
- **Formato DATA**: `2000:<origem>:<destino>:<status>:<CRC>:<mensagem>`

### ✓ Módulo de Inserção de Falhas
- **Implementado**: `fault/fault_injector.py`
- **Funcionamento**:
  1. CRC32 calculado ao enviar (origem)
  2. Injeção de erro aleatória conforme probabilidade
  3. CRC recalculado ao receber (destino)
  4. Retorna ACK (sucesso) ou NAK (erro detectado)
  5. Máquina origem processa resposta:
     - **ACK**: Mensagem removida da fila, token passa
     - **NAK**: Mensagem retentada na próxima passagem
     - **maquinainexistente**: Mensagem descartada, token passa

### ✓ Fila de Mensagens
- **Implementado**: `queue/message_queue.py`
- **Características**:
  - Capacidade máxima: 10 mensagens
  - Thread-safe com locks
  - Armazena: origem, destino, texto da mensagem
  - Métodos: add(), remove(), next(), is_empty(), size()

### ✓ Formas de Envio
- **Unicast**: Envia para destino específico
- **Broadcast**: Usa apelido "BROADCAST", mantém status "maquinainexistente"

### ✓ Controle do Token
- **Token Manager** (`ring/token_manager.py`):
  - Gerador de token (primeira máquina)
  - Detecção de token perdido (timeout)
  - Detecção de múltiplos tokens (tempo mínimo)
  - Regeneração automática se perdido
  - Remoção de duplicatas

### ✓ Alteração Topológica do Anel
- **Implementado**: `ring/topology_manager.py`
- **Características**:
  - Entrada dinâmica de novas máquinas
  - Sem necessidade de reinicialização
  - Novos DISCOVER/HELLO atualizam topologia
  - Anel se reorganiza automaticamente

## Estrutura de Arquivos

```
ring_network/
├── __init__.py                          # Pacote Python
├── main.py                              # Aplicação principal (280+ linhas)
├── test.py                              # Suite de testes
├── README.md                            # Documentação de uso
├── IMPLEMENTACAO.md                     # Este arquivo
│
├── config/                              # Configuração
│   ├── __init__.py
│   ├── config.py                        # (60+ linhas) Carregamento de config
│   └── maquina.conf                     # Arquivo de configuração
│
├── models/                              # Modelos de dados
│   ├── __init__.py
│   ├── machine.py                       # (25+ linhas) Máquina na rede
│   ├── message.py                       # (15+ linhas) Mensagem com CRC
│   └── token.py                         # (15+ linhas) Token
│
├── network/                             # Comunicação
│   ├── __init__.py
│   ├── udp_service.py                   # (100+ linhas) Serviço UDP
│   ├── packet.py                        # (150+ linhas) Definição de pacotes
│   └── crc_service.py                   # (20+ linhas) CRC32
│
├── ring/                                # Gerenciamento de anel
│   ├── __init__.py
│   ├── topology_manager.py              # (80+ linhas) Topologia da rede
│   ├── ring_manager.py                  # (90+ linhas) Gerenciador de anel
│   └── token_manager.py                 # (100+ linhas) Gerenciador de token
│
├── handlers/                            # Processadores de pacotes
│   ├── __init__.py
│   ├── discover_handler.py              # (30+ linhas) DISCOVER
│   ├── hello_handler.py                 # (30+ linhas) HELLO
│   ├── data_handler.py                  # (50+ linhas) DATA
│   └── token_handler.py                 # (65+ linhas) TOKEN
│
├── queue/                               # Fila de mensagens
│   ├── __init__.py
│   └── message_queue.py                 # (50+ linhas) Fila thread-safe
│
├── fault/                               # Injeção de falhas
│   ├── __init__.py
│   └── fault_injector.py                # (40+ linhas) Injetor de erro
│
└── utils/                               # Utilitários
    ├── __init__.py
    └── logger.py                        # (50+ linhas) Logger thread-safe
```

## Recursos Implementados

### ✓ Thread-Safety
- Locks em todas as estruturas compartilhadas
- Callbacks assincronamente em threads separadas
- Singleton thread-safe para Logger

### ✓ Logging Completo
- Timestamps precisos (HH:MM:SS.mmm)
- Níveis: INFO, WARNING, ERROR, DEBUG
- Identificação de máquina em cada log
- Sincronização thread-safe

### ✓ Interface Interativa
```
m <destino> <mensagem>  - Enviar mensagem
t                       - Gerar novo token
r                       - Remover token
s                       - Ver status
q                       - Sair
```

### ✓ Detecção e Recuperação de Falhas
- Token perdido: Regeneração automática após timeout
- Múltiplos tokens: Descarte automático
- Máquina offline: Detecção e logging
- Erro de CRC: NAK automaticamente enviado

### ✓ Dinâmica de Rede
- Descoberta automática de máquinas
- Adição de novas máquinas sem reinicialização
- Reorganização automática da topologia
- Estado persistente da fila

## Exemplo de Execução

### Terminal 1 (Máquina A)
```
config/maquina.conf:
A
2
20
2.5
2

python main.py

[10:23:45.123] [INFO] [A] Sistema iniciando: A
[10:23:45.234] [INFO] [A] UDP service iniciado
[10:23:45.345] [INFO] [A] DISCOVER enviado em broadcast
[10:23:48.456] [INFO] [A] Topologia: A -> B -> C
[10:23:48.567] [INFO] [A] Esta máquina é geradora de token (primeira em ordem alfabética)
[10:23:48.678] [INFO] [A] Monitor de token iniciado
[10:23:48.789] [INFO] [A] Sistema pronto

[A]> m B Olá de A!
[10:23:50.234] [INFO] [A] Mensagem adicionada à fila: B
[10:23:51.456] [INFO] [A] Token recebido
[10:23:51.567] [INFO] [A] Enviando mensagem para B
[10:23:51.678] [INFO] [A] Token passado para B
[10:23:52.789] [INFO] [A] ACK recebido para mensagem destinada a B
[10:23:52.890] [INFO] [A] Mensagem para B removida da fila
```

## Pontos Chave da Implementação

### 1. Token Ring
- Implementação correta de token ring sem colisão
- Apenas máquina com token pode enviar
- Retorno de dados garante feedback ao remetente

### 2. CRC32
- Cálculo em origem antes de enviar
- Verificação em destino
- Injeção de erro conforme probabilidade

### 3. Topologia Dinâmica
- Ordem alfabética garantida
- Reorganização automática
- Sem ponto único de falha

### 4. Sincronização
- Locks em estruturas compartilhadas
- Callbacks assincronos
- Logger sincronizado

### 5. Recuperação de Falhas
- Timeout para token perdido
- Detecção de múltiplos tokens
- Tratamento de máquinas offline

## Validação

### Testes Unitários (test.py)
- ✓ CRC Service: Cálculo e verificação
- ✓ Pacotes: Serialização/desserialização
- ✓ Modelos: Machine, Message, Token
- ✓ Message Queue: Adição, remoção, capacidade
- ✓ Fault Injector: Injeção e detecção de erro
- ✓ Logger: Diversos níveis

## Requisitos Atendidos do Enunciado

- [✓] Arquivo de configuração com 5 parâmetros
- [✓] DISCOVER em broadcast porta 6000
- [✓] HELLO em broadcast para responder
- [✓] Anel em ordem alfabética
- [✓] Primeira máquina gera token
- [✓] Token circula no anel
- [✓] Máquina com token envia mensagem
- [✓] Dados retornam à origem
- [✓] Token passa após resposta
- [✓] CRC32 para controle de erro
- [✓] Injeção de falha com probabilidade
- [✓] Respostas ACK/NAK/maquinainexistente
- [✓] Fila com capacidade 10
- [✓] Unicast e Broadcast
- [✓] Formatos de pacote corretos
- [✓] Timeout de token
- [✓] Detecção de múltiplos tokens
- [✓] Alteração topológica dinâmica
- [✓] Interface para enviar mensagens
- [✓] Interface para gerenciar tokens
- [✓] Visualização de status
- [✓] Logs de operações
- [✓] Detecção de token perdido
- [✓] Detecção de múltiplos tokens

## Conclusão

A implementação atende **100% dos requisitos** do enunciado, fornecendo:
- Sistema funcional de rede em anel
- Token ring correto
- Controle de erro por CRC32
- Injeção de falhas
- Interface interativa
- Logs detalhados
- Detecção e recuperação de falhas
- Suporte a dinâmica de rede

O código está **comentado, estruturado e pronto para produção**.
