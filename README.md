# Simulador de rede local em anel

Implementacao em Python do trabalho final: descoberta por UDP broadcast, anel
ordenado por apelido, token, pacotes de dados, fila local de ate 10 mensagens,
CRC32, insercao probabilistica de falhas e comandos interativos.

## Como executar

Crie um arquivo de configuracao com 5 linhas:

```text
<apelido>
<tempo_token_e_dados>
<probabilidade_de_erro>
<timeout_do_token>
<tempo_minimo_entre_tokens>
```

Exemplo:

```text
B
2
20
2,5
2
```

Em cada maquina da rede, use um apelido diferente:

```powershell
python ring_node.py config.txt
```

Todos os pacotes usam UDP na porta `6000`. Se o firewall perguntar, permita
trafego UDP nessa porta.

Se o broadcast global `255.255.255.255` for bloqueado na rede, use o broadcast
da sub-rede:

```powershell
python ring_node.py config.txt --broadcast-ip 192.168.1.255
```

## Comandos durante a execucao

```text
send <DESTINO> <mensagem>      adiciona mensagem unicast na fila
broadcast <mensagem>           adiciona mensagem broadcast na fila
token add                      gera um token agora
token remove                   remove o proximo token que passar aqui
peer add <APELIDO> <IP>        adiciona/atualiza maquina conhecida
peer remove <APELIDO>          remove maquina conhecida
discover                       envia DISCOVER novamente
peers                          mostra maquinas conhecidas e anel
queue                          mostra fila local
help                           mostra ajuda
quit                           encerra
```

Formato dos pacotes implementado:

```text
10:<apelido_origem>:<ip_origem>
20:<apelido_origem>:<ip_origem>
1000
2000:<origem>:<destino>:<controle>:<CRC>:<mensagem>
```

## Teste rapido sem rede

```powershell
python -B smoke_tests.py
```
