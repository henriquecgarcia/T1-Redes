# Parte 2 — Rede emulada e avaliação experimental

Foram concluídas 528 rodadas, 48 configurações e 2288 transferências corretas.
O piloto separado teve quatro rodadas e 16 transferências. O CORE 9.2.0 foi
executado no container Docker privilegiado `core`.

## Arquivos

- `core/`: topologia executável, perfis e XML exportado.
- `scripts/`: geração da matriz, execução, conferência e análise.
- `tests/`: testes estatísticos e piloto de reprodução isolado.
- `matriz_experimental.csv`: ordem das configurações planejadas.
- `resultados_brutos.csv`: observações reais, status e SHA-256.
- `resultados_resumidos.csv`: médias, medianas, desvios, IC e taxas.
- `graficos/`: gráficos originais da coleta, preservados.
- `evidencias/`: validações, journals, logs e arquivos históricos.

O artigo está separado em `../relatorio/`. Suas figuras foram adaptadas para
impressão usando os mesmos CSV, sem substituir os gráficos originais.

## Dependências e CORE

São necessários Docker, Python 3, NumPy, SciPy e Matplotlib. A imagem `core`
deve conter CORE 9.2.0 em `/opt/core/venv`. O identificador da imagem e o
ambiente estão em `evidencias/ambiente.log`. Consulte os materiais da disciplina
em `../materiais/` e a [instalação oficial](https://coreemu.github.io/core/install.html).

A rede contém acesso cliente `10.10.0.0/24`, núcleo `10.20.0.0/24` e acesso
servidor `10.30.0.0/24`. O servidor atende na porta 8080. HTB/netem nas saídas
para o núcleo modelam o gargalo bidirecional:

| Perfil | Taxa por sentido | Atraso por direção | RTT nominal |
| --- | --- | --- | --- |
| A | 100 Mbps | 5 ms | 10 ms |
| B | 20 Mbps | 30 ms | 60 ms |

São cenários didáticos de conectividade com capacidades e atrasos diferentes,
sem pretensão de medir uma tecnologia comercial específica. Os acessos não
recebem limitação adicional. Não há perda artificial; perdas por congestionamento
continuam possíveis. O TCP usa CUBIC, com TSO/GSO/GRO desativados nos nós.
O XML registra o desenho; o script reaplica rotas e filas.

## Executar ou retomar

A partir da raiz do projeto:

```bash
make -C parte1
sudo bash parte2/scripts/run_docker.sh pilot
sudo bash parte2/scripts/run_docker.sh main
```

O script usa `CORE_CONTAINER=core` e `CORE_WORKDIR=/tmp/redest1-work`. Compila
os programas e o iperf 3.22 e executa ping, traceroute e iperf bidirecional.
A fonte oficial compactada do iperf está em `tools/`, com hash registrado.
Se não encontrar o container, tenta criá-lo da imagem `CORE_IMAGE=core`.

No ambiente original, a campanha está concluída. O journal confirma cada
rodada após sincronizar o CSV; a retomada só ignora tentativas completas.
Falhas terminais permanecem como falhas. O teste de retomada foi feito após
duas rodadas e depois da conclusão, sem duplicações. Não foi simulado
corrompimento do arquivo ou desligamento físico.

Para outra campanha, faça uma cópia do projeto e escolha outro diretório:

```bash
sudo CORE_WORKDIR=/tmp/redest1-nova bash parte2/scripts/run_docker.sh main
```

A sincronização copia a campanha escolhida para os CSV locais; por isso,
conserve a entrega original antes de iniciar outra coleta.
`CORE_EXPORT_DIR` permite escolher o destino da cópia. Não execute duas
campanhas no mesmo diretório Docker.

## Conferir dados e analisar em uma cópia

```bash
python3 parte2/scripts/check_outputs.py
python3 parte2/tests/test_analysis.py
mkdir -p parte2/build/analise/evidencias
cp parte2/{resultados_brutos.csv,resultados_resumidos.csv,matriz_experimental.csv} \
  parte2/build/analise/
cp parte2/evidencias/rodadas_concluidas.jsonl parte2/build/analise/evidencias/
T1_RESULT_ROOT="$PWD/parte2/build/analise" python3 parte2/scripts/analyze.py
```

O IC da média usa Student entre médias de rodada. O IC da mediana usa bootstrap
de rodadas inteiras. O desvio entre clientes é descritivo. O resumo inclui
taxas por observação e rodada; configurações incompletas são marcadas pendentes.
A revisão recalculou o resumo em uma cópia e obteve bytes idênticos ao CSV entregue.

O piloto de reprodução pode ser executado sem substituir os resultados originais:

```bash
sudo python3 parte2/tests/test_reproduction.py
```

Ele usa diretórios novos e guarda os logs em `parte2/build/revisao/`.
As figuras e tabelas do artigo podem ser regeneradas dos CSV existentes:

```bash
python3 parte2/scripts/graficos_relatorio.py
python3 parte2/scripts/tabelas_relatorio.py
make -C relatorio
```

## Preservação e limites

Os arquivos `codigo_executado.tar.gz`, `fontes_medicao.tar.gz` e os arquivos
de logs em `evidencias/` conservam as versões anteriores à formatação.
As novas verificações estão em `evidencias/revisao/`.

Todos os nós compartilham um host WSL/Docker. Não foram isolados CPU, cache ou
disco frio. Os perfis variam taxa e atraso juntos; os efeitos individuais não
foram separados. Essas limitações e a discussão dos resultados estão no artigo.
