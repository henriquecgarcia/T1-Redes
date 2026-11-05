# Trabalho 1 — Redes de Computadores — ICT/UNIFESP

Implementação de um cliente-servidor de arquivos em C/Linux e avaliação de
GET e PUT no CORE 9.2.0. O servidor atende até oito clientes simultaneamente
com OpenMP. A campanha concluiu **528 rodadas e 2288 transferências**, todas
com status de sucesso e SHA-256 correspondente.

## Organização

- [`parte1/`](parte1/README.md): fontes C, Makefile, testes, originais preservados e logs.
- [`parte2/`](parte2/README.md): topologia CORE, scripts, dados, estatísticas e gráficos originais.
- [`relatorio/`](relatorio/README.md): artigo em LaTeX no modelo oficial SBC e PDF compilado.
- [`materiais/`](materiais/README.md): enunciado e guia de instalação fornecidos para a disciplina.

O relatório está em [PDF](relatorio/relatorio_final.pdf),
[LaTeX](relatorio/relatorio_final.tex) e [Markdown](relatorio/relatorio_final.md).
A pasta `relatorio/` contém todos os arquivos necessários para compilar o artigo.

## Pré-requisitos

No Ubuntu/WSL:

```bash
sudo apt-get update
sudo apt-get install -y build-essential python3 python3-numpy python3-scipy \
  python3-matplotlib texlive-latex-base texlive-latex-recommended \
  texlive-latex-extra texlive-lang-portuguese texlive-fonts-recommended
```

Para executar a rede emulada, é necessário Docker e uma imagem `core` com
CORE 9.2.0 em `/opt/core/venv`. A imagem não faz parte deste repositório.
Consulte o [guia do ambiente](materiais/Guia_CORE_WSL2_Ubuntu_22_04.pdf) e a
[documentação oficial](https://coreemu.github.io/core/install.html).

## Compilação e uso

```bash
make -C parte1
mkdir -p parte1/build/arquivos
./parte1/build/server 8080 parte1/build/arquivos
```

Em outro terminal, crie um arquivo de exemplo e faça PUT e GET:

```bash
dd if=/dev/urandom of=parte1/build/exemplo.bin bs=1024 count=32 status=none
./parte1/build/client 127.0.0.1 8080 PUT exemplo.bin parte1/build/exemplo.bin
./parte1/build/client 127.0.0.1 8080 GET exemplo.bin parte1/build/download.bin
sha256sum parte1/build/exemplo.bin parte1/build/arquivos/exemplo.bin \
  parte1/build/download.bin
```

O cliente recebe IPv4, porta, operação, nome remoto e caminho local. O JSON
informa início monotônico, duração, bytes, vazão e status. Nomes remotos são
restritos ao diretório de armazenamento; subdiretórios remotos não são aceitos.
O destino anterior só é substituído depois da transferência completa.

## Testes e conferência dos dados

```bash
bash parte1/scripts/verify.sh
python3 parte2/tests/test_analysis.py
python3 parte2/tests/test_preservation.py
python3 parte2/scripts/check_outputs.py
```

Os testes de transferência usam diretórios temporários. Os novos logs ficam
em `parte1/build/testes/`, sem sobrescrever as evidências originais. A suíte
inclui 11 testes normais e 11 com I/O parcial e EINTR forçados; há também três
testes da análise. O teste de timeout ocioso leva cerca de 15 segundos por execução.

Os dados originais estão em `parte2/resultados_brutos.csv`; o resumo contém
48 configurações com 11 repetições. A incerteza usa a rodada como unidade de
repetição, pois os clientes de uma rodada compartilham a rede e o servidor.

## CORE e experimentos

A topologia tem oito clientes em `10.10.0.0/24`, núcleo em `10.20.0.0/24` e
servidor `10.30.0.10:8080`, com dois roteadores e três switches. O gargalo
HTB/netem usa A = 100 Mbps/5 ms e B = 20 Mbps/30 ms **por direção**, sem perda
artificial. Os RTT nominais são 10 e 60 ms. São perfis propostos para o
experimento, não medições universais de tecnologias de acesso.

```bash
sudo bash parte2/scripts/run_docker.sh pilot
sudo bash parte2/scripts/run_docker.sh main
```

Esses comandos usam o container `core` e `/tmp/redest1-work`. No ambiente
original, a campanha já está concluída; a retomada não repete rodadas confirmadas.
Para outra coleta, trabalhe em uma cópia do projeto e use outro `CORE_WORKDIR`.
Veja os parâmetros e a análise isolada no [README da Parte 2](parte2/README.md).

## Compilação do artigo SBC

```bash
make -C relatorio
```

O comando executa pdfLaTeX, BibTeX e mais dois passes de pdfLaTeX. O arquivo
final é `relatorio/relatorio_final.pdf`. Não é necessário Pandoc para compilar.
Os nomes e e-mails dos autores ficam em `relatorio/autores.tex`.

## Preservação e escopo

Os fontes funcionais originais estão em `parte1/originais/originais.tar.gz`.
O código usado na medição e os logs históricos também foram preservados em
arquivos compactados, com verificação de conteúdo. Os CSV, timestamps, hashes
e gráficos originais não foram alterados na revisão.

O código ativo usa TABs reais para indentação. O pacote `sbc-template.sty` e
os registros experimentais mantêm os bytes originais. O arquivo `sbc.bst`
recebeu um ajuste pontual para formatar as citações autor-ano.
Os limites do ambiente compartilhado e da metodologia estão no artigo.
A Parte 3, referente ao vídeo, permanece fora do escopo.
