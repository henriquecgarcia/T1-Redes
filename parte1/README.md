# Parte 1 — Cliente e servidor TCP

A versão final está em `src/tcp_client.c`, `src/tcp_server.c` e `src/protocol.h`.
A referência funcional é o par `tcp_client.c`/`tcp_server.c` fornecido pelo usuário.
Os arquivos antigos chamados `tcp.c` não são necessários.

## Compilar e executar

Dentro de `parte1/`:

```bash
make
mkdir -p build/arquivos
./build/server 8080 build/arquivos
```

Em outro terminal:

```bash
./build/client 127.0.0.1 8080 PUT exemplo.bin ./exemplo.bin
./build/client 127.0.0.1 8080 GET exemplo.bin ./download.bin
sha256sum exemplo.bin build/arquivos/exemplo.bin download.bin
```

O arquivo de origem deve existir antes do PUT. O cliente recebe IPv4, porta,
GET/PUT, nome remoto e caminho local. Retorno 0 significa sucesso; 1 indica
falha de operação/rede; 2 indica argumentos inválidos. O JSON inclui duração
monotônica, bytes e vazão útil em Mbps.

O servidor usa oito trabalhadores OpenMP. Arquivos vazios e binários são
aceitos até 1 GiB. Nomes remotos são simples, sem caminho ou espaço. PUT e GET
substituem o destino somente após concluir a transferência. Se vários PUTs
usarem o mesmo nome, a última publicação concluída vence. GET mantém a versão
que abriu. Os timeouts de comunicação são de 15 segundos por espera.

## Testes

```bash
bash scripts/verify.sh
python3 scripts/audit_originals.py
```

Os 11 testes cobrem GET/PUT, SHA-256, sobrescrita, oito atendimentos simultâneos,
conflitos de nome, fragmentação, desconexões, truncamento, erros e timeout.
A suíte é repetida com send/recv parciais e EINTR forçados.
Os novos logs ficam em `build/testes/<data-hora>/`; a variável
`T1_TEST_EVIDENCE_DIR` permite escolher outro diretório.
As evidências anteriores continuam em `evidencias/`.

## Originais e organização

`originais/originais.tar.gz` preserva os bytes dos fontes e arquivos de exemplo.
Para inspecioná-los sem substituir os fontes atuais:

```bash
mkdir -p build/originais
tar -xzf originais/originais.tar.gz -C build/originais
```

O script de auditoria confere os hashes dos fontes funcionais diretamente
no arquivo compactado. `tests/` contém a suíte e o interpositor de sockets;
`scripts/` contém os comandos de verificação.

O relatório das duas partes está em `../relatorio/`. O protótipo não oferece
TLS, autenticação ou durabilidade garantida após queda de energia.
