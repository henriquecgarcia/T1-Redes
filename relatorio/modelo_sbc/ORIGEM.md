# Modelo SBC utilizado

O relatório utiliza `article` com a opção `12pt` e o pacote oficial
`sbc-template`, atualizado em dezembro de 2017. O próprio pacote define papel,
margens, Times, títulos, legendas e ausência de numeração de páginas.
Nenhuma dessas propriedades foi redefinida no artigo.

O portal da SBC foi consultado em 05/11/2026, mas as páginas antigas de download
não responderam nesta sessão. A autoria e as instruções do modelo foram
conferidas na publicação da própria SBC no Overleaf:

- https://www.overleaf.com/latex/templates/sbc-conferences-template/blbxwjwzdngr

Os arquivos foram obtidos da distribuição do SBGames, evento da SBC:

- https://www.sbgames.org/arquivos/Template_SBC/template-latex/sbc-template.sty
- https://www.sbgames.org/arquivos/Template_SBC/template-latex/sbc.bst

`sbc-template.sty` permanece igual ao arquivo obtido. O arquivo `sbc.bst`
foi ajustado depois para produzir rótulos de citação no formato `(Autor, Ano)`
e conservar anos como `s.d.`. `SHA256SUMS` registra os hashes dos dois arquivos
originais; por isso, o hash ali registrado para `sbc.bst` não corresponde à
versão ajustada utilizada na compilação.
O template no Overleaf é atribuído à Sociedade Brasileira de Computação e
indica licença CC BY 4.0. Os avisos de autoria dos arquivos foram preservados.

O modelo pede abstract em inglês e resumo em português para artigos em
português. Ele não define um campo de palavras-chave, por isso esse campo não
foi criado manualmente. O enunciado `materiais/trabalho-1-sockets-26.pdf` foi conferido após ser
adicionado ao repositório. Ele identifica ICT/UNIFESP e não exige um modelo
de relatório em LaTeX. A adoção do SBC atende à orientação direta do usuário.
