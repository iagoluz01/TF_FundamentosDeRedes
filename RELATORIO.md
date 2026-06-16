# Relatorio do trabalho final

## Objetivo

O programa implementa uma simulacao de rede local em anel usando UDP. Cada
execucao representa uma maquina do anel, identificada por um apelido. As
maquinas descobrem umas as outras por broadcast, montam o anel em ordem
alfabetica e transmitem token e dados sempre para a proxima maquina.

## Estrutura da solucao

- `Config`: carrega as 5 linhas do arquivo de configuracao: apelido, tempo de
  envio, probabilidade de erro, timeout do token e tempo minimo entre tokens.
- `Peer`: representa uma maquina conhecida, com apelido, IP e instante em que
  foi vista pela ultima vez.
- `MessageItem`: representa um item da fila local, contendo destino, mensagem e
  quantidade de retransmissoes.
- `DataPacket`: representa o pacote `2000`, com origem, destino, controle de
  erro, CRC32 e mensagem.
- `RingNode`: concentra o socket UDP, a tabela de maquinas, a fila de
  mensagens, o controle do token e os comandos interativos.

## Threads

O programa usa tres fluxos principais:

- thread principal: le comandos do usuario.
- `receiver_loop`: recebe datagramas UDP e trata DISCOVER, HELLO, TOKEN e DATA.
- `watchdog_loop`: roda na primeira maquina do anel e detecta timeout do token.

## Sincronizacao

Foram usados locks para proteger dados compartilhados entre as threads:

- `peer_lock`: protege a tabela de maquinas conhecidas.
- `queue_lock`: protege a fila local de mensagens.
- `send_lock`: serializa chamadas de envio no socket.
- `token_lock`: protege variaveis de controle do token.
- `in_flight_lock`: protege a mensagem local que esta circulando no anel.
- `print_lock`: evita mistura de mensagens na tela.

## Pacotes

Os formatos implementados sao:

```text
10:<apelido_origem>:<ip_origem>
20:<apelido_origem>:<ip_origem>
1000
2000:<origem>:<destino>:<controle>:<CRC>:<mensagem>
```

O DISCOVER e o HELLO sao enviados em broadcast UDP na porta 6000. O token e os
dados sao enviados por UDP diretamente ao IP do sucessor no anel.

## CRC e falhas

Antes de enviar dados, a origem calcula `CRC32` sobre a mensagem original. O
modulo de falhas pode alterar um caractere da mensagem depois do calculo do
CRC, de acordo com a probabilidade definida no arquivo de configuracao.

No destino, o CRC e recalculado:

- se for igual, o pacote volta marcado como `ACK`;
- se for diferente, o pacote volta marcado como `NAK`;
- em broadcast, o controle permanece `maquinainexistente`.

Quando a origem recebe `NAK`, a mensagem permanece na fila e e retransmitida
uma unica vez na proxima passagem do token, sem nova insercao de falha. Com
`ACK` ou `maquinainexistente`, a mensagem sai da fila.

## Fila de mensagens

Cada maquina possui uma fila local com limite de 10 mensagens. Apenas a primeira
mensagem da fila pode ser transmitida quando a maquina recebe o token. Enquanto
um pacote de dados originado pela maquina estiver circulando, o token so e
liberado depois que o pacote retornar.

## Controle do token

A primeira maquina em ordem alfabetica e a controladora. Ela gera o token
inicial e monitora:

- timeout: se o token nao voltar no tempo configurado, um novo token e gerado;
- token duplicado: se o token voltar antes do tempo minimo, o token recebido e
  removido.

Tambem existem comandos manuais para gerar ou retirar token durante a execucao.

## Alteracao de topologia

Novas maquinas podem entrar enviando DISCOVER. As maquinas antigas respondem
com HELLO e todas recalculam o sucessor em ordem alfabetica. Tambem existem
comandos `peer add` e `peer remove` para ajustes manuais durante demonstracoes
de falha.

## Exemplo de execucao

Em tres maquinas diferentes:

```powershell
python ring_node.py config_A.txt
python ring_node.py config_B.txt
python ring_node.py config_C.txt
```

Exemplos de comandos:

```text
send B Ola B
broadcast Ola para todos
token remove
token add
peers
queue
```

## Observacoes

Se o broadcast `255.255.255.255` nao funcionar na rede, execute informando o
broadcast da sub-rede:

```powershell
python ring_node.py config_A.txt --broadcast-ip 192.168.1.255
```
