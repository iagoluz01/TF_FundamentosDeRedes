# Rede em Anel (Ring Network)

## Descrição
Simulação de uma rede local em anel (ring topology) usando UDP como protocolo de transporte. Implementa token ring para controlar acesso ao meio, com suporte a DISCOVER, HELLO, TOKEN e pacotes DATA com controle de erro CRC32.

## Estrutura do Projeto

### `/config` - Configuração
- `config.py` - Carrega configurações do arquivo
- `maquina.conf` - Arquivo de configuração (nickname, tempos, probabilidade de erro)

### `/models` - Modelos de Dados
- `machine.py` - Representação de uma máquina na rede
- `message.py` - Mensagem com CRC
- `token.py` - Token que circula na rede

### `/network` - Comunicação
- `udp_service.py` - Serviço UDP para envio/recebimento
- `packet.py` - Definição de pacotes (DISCOVER, HELLO, TOKEN, DATA)
- `crc_service.py` - Cálculo e verificação de CRC32

### `/ring` - Gerenciamento de Anel
- `topology_manager.py` - Gerencia máquinas ativas
- `ring_manager.py` - Gerencia fila de mensagens e posição no anel
- `token_manager.py` - Controla ciclo de vida do token

### `/handlers` - Processadores de Pacotes
- `discover_handler.py` - Processa DISCOVER
- `hello_handler.py` - Processa HELLO
- `data_handler.py` - Processa dados
- `token_handler.py` - Processa tokens

### `/fault` - Injeção de Falhas
- `fault_injector.py` - Injeta erros aleatoriamente

### `/queue` - Fila de Mensagens
- `message_queue.py` - Fila thread-safe com capacidade máxima

### `/utils` - Utilitários
- `logger.py` - Sistema de logging thread-safe

## Configuração

### Arquivo `config/maquina.conf`
```
<nickname>
<token_time>
<error_probability>
<token_timeout>
<min_token_time>
```

Exemplo:
```
B
2
20
2.5
2
```

- **nickname**: Apelido da máquina (A, B, C, D...)
- **token_time**: Tempo de circulação do token em segundos
- **error_probability**: Probabilidade de erro (0-100%)
- **token_timeout**: Timeout para detecção de token perdido
- **min_token_time**: Tempo mínimo entre tokens (detecta duplicatas)

## Como Executar

### Pré-requisitos
- Python 3.6+
- Sistema Windows/Linux/Mac com suporte UDP

### Executar uma instância
```bash
cd c:\t2_redes\ring_network
python main.py
```

### Executar múltiplas instâncias (máquinas diferentes)
1. Abra múltiplos terminais
2. Em cada terminal, modifique `config/maquina.conf` com um nickname diferente (A, B, C...)
3. Execute `python main.py` em cada terminal

## Funcionamento

### Fase 1: Descoberta (DISCOVER/HELLO)
1. Cada máquina envia DISCOVER em broadcast
2. Máquinas respondem com HELLO
3. Topologia em anel é construída em ordem alfabética

### Fase 2: Token Ring
1. Primeira máquina (alfabética) gera token
2. Token circula: A → B → C → D → A
3. Máquina com token pode enviar uma mensagem

### Fase 3: Transmissão de Dados
1. Pacote DATA viaja até destino
2. Destino valida CRC e responde ACK/NAK
3. Pacote retorna ao remetente
4. Token passa para próxima máquina

## Comandos Interativos

```
m <destino> <mensagem>  - Enviar mensagem
  Exemplo: m C Oi pessoal!

t                       - Gerar novo token (força retirada de token perdido)

r                       - Remover token da rede

s                       - Ver status (máquinas, fila, próxima máquina)

q                       - Sair
```

## Formatos de Pacotes

### DISCOVER
```
10:<nickname>:<IP>
Exemplo: 10:A:192.168.1.100
```

### HELLO
```
20:<nickname>:<IP>
Exemplo: 20:B:192.168.1.101
```

### TOKEN
```
1000
```

### DATA
```
2000:<origem>:<destino>:<status>:<CRC>:<mensagem>
Exemplo: 2000:B:A:maquinainexistente:19385749:Oi pessoal!
```

**Status:**
- `maquinainexistente`: Enviado pela origem
- `ACK`: Recebido corretamente
- `NAK`: Erro detectado (falha CRC)

## Logs

O sistema imprime logs com formato:
```
[HH:MM:SS.mmm] [LEVEL] [MACHINE] mensagem
```

**Níveis:**
- INFO: Operações normais
- WARNING: Condições anormais (NAK, máquina offline)
- ERROR: Erros
- DEBUG: Informações de debug

## Detecção de Falhas

### Token Perdido
- Se gerador não recebe token em `token_timeout` segundos
- Novo token é gerado automaticamente
- Log: "Token perdido! Timeout excedido"

### Múltiplos Tokens
- Se dois tokens chegam em menos de `min_token_time` segundos
- Token duplicado é descartado
- Log: "Múltiplos tokens detectados!"

### Máquina Offline
- Se dados retornam com `maquinainexistente`
- Mensagem é descartada
- Log: "Máquina X não existe ou está desligada"

## Controle de Erro

- **CRC32** calculado ao enviar
- Verificado ao receber
- NAK enviado se erro detectado
- Injeção de erro conforme probabilidade configurada

## Exemplo de Execução com 3 Máquinas

### Terminal 1 (Máquina A)
```
cd c:\t2_redes\ring_network
# Editar config/maquina.conf com nickname=A
python main.py

# Dentro da aplicação:
[A]> m C Olá de A!
[A]> s
```

### Terminal 2 (Máquina B)
```
cd c:\t2_redes\ring_network
# Editar config/maquina.conf com nickname=B
python main.py

# Dentro da aplicação:
[B]> m A Oi A!
[B]> s
```

### Terminal 3 (Máquina C)
```
cd c:\t2_redes\ring_network
# Editar config/maquina.conf com nickname=C
python main.py

# Dentro da aplicação:
[C]> s
```

## Observações

- Máquinas descobrem-se automaticamente via broadcast
- Topologia é dinâmica - novas máquinas podem entrar
- Fila de mensagens tem capacidade máxima de 10
- CRC32 usado para detecção de erro
- Thread-safe em toda a implementação
- Logs sincronizados para múltiplas máquinas
