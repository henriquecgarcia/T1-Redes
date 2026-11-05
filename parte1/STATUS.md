# Parte 1 — concluída e revisada

- [x] Referências funcionais tcp_client.c e tcp_server.c auditadas e preservadas.
- [x] Fontes C com TABs reais, espaçamento consistente e comentários úteis.
- [x] Compilação GCC/C11/OpenMP com avisos tratados como erros.
- [x] Assembly idêntico antes/depois da revisão de formatação.
- [x] GET/PUT binários, arquivos vazios e sobrescrita testados.
- [x] Oito atendimentos simultâneos e conflitos de nome verificados.
- [x] Desconexões, truncamentos, I/O parcial e EINTR testados.
- [x] 11 testes normais e 11 com interposição aprovados na revisão.
- [x] SHA-256 dos originais conferido no arquivo preservado.
- [x] Testes separados em tests/; novas saídas não sobrescrevem os logs anteriores.
- [x] Commits incrementais registrados, sem reescrever o histórico.

Sem pendências obrigatórias nesta parte. TLS, autenticação e durabilidade após
queda de energia não fazem parte das garantias do protótipo. O artigo está em
`../relatorio/`; evidências da revisão estão em `evidencias/revisao/`.
