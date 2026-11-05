# Parte 2 — concluída e revisada

- [x] CORE 9.2.0 existente no Docker utilizado.
- [x] Duas redes de acesso, núcleo, oito clientes, servidor e dois roteadores funcionais.
- [x] Gargalo bidirecional HTB/netem validado, sem perda artificial.
- [x] Ping, traceroute e iperf executados em ambos os perfis.
- [x] Piloto e campanha principal completos e separados.
- [x] 528 rodadas, 48 configurações, 11 repetições e 2288 transferências corretas.
- [x] SHA-256 correspondente em todas as observações.
- [x] Concorrência temporal e retomada sem duplicação verificadas.
- [x] Média, mediana, desvios, IC e taxas calculados considerando agrupamento por rodada.
- [x] Três testes da análise aprovados.
- [x] Recálculo isolado com CSV resumido idêntico ao original.
- [x] Scripts ativos com TABs reais e sintaxe validada.
- [x] Piloto CORE reproduzido após a revisão, em diretório novo, com 16 sucessos.
- [x] Gráficos originais, CSV, timestamps, hashes e logs preservados.
- [x] Artigo separado em ../relatorio/, com pacote SBC original, ajuste de citações em `sbc.bst` e PDF compilado.
- [x] Autores e instituição preenchidos com dados fornecidos/confirmados.
- [x] Enunciado e guia preservados em ../materiais/.
- [x] Parte 3 não implementada.

Sem pendências obrigatórias no escopo solicitado. A imagem Docker não é
incluída no repositório. O host é compartilhado, o cache não foi isolado e os
perfis variam taxa e atraso conjuntamente. A retomada foi verificada com
checkpoint íntegro. As limitações completas estão no artigo.
