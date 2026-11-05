# Artigo técnico — modelo SBC

Esta pasta contém somente o relatório e seus arquivos de apoio:

- `relatorio_final.tex`: fonte principal, organizado por seções.
- `relatorio_final.pdf`: versão compilada.
- `relatorio_final.md`: versão complementar legível.
- `autores.tex`: nomes, instituição e e-mails fornecidos/confirmados.
- `referencias.bib` e `sbc.bst`: referências e estilo bibliográfico.
- `sbc-template.sty`: estilo SBC oficial, sem modificações.
- `figuras/` e `tabelas/`: elementos usados no artigo.
- `modelo_sbc/`: origem e hashes dos arquivos oficiais.

A pasta é autossuficiente para compilar o artigo. No Ubuntu, são necessários
TeX Live com os pacotes recomendados/extras, fontes recomendadas e suporte a português.

## Compilar

A partir da raiz do projeto:

```bash
make -C relatorio
```

Ou, dentro desta pasta:

```bash
pdflatex -interaction=nonstopmode -halt-on-error relatorio_final.tex
bibtex relatorio_final
pdflatex -interaction=nonstopmode -halt-on-error relatorio_final.tex
pdflatex -interaction=nonstopmode -halt-on-error relatorio_final.tex
```

O Makefile mantém os intermediários em `build/` e copia o PDF final para esta pasta.
Pandoc não é necessário para compilar. O `.tex` é o fonte principal editável;
o Markdown é uma cópia complementar e deve acompanhar revisões do texto.

O estilo define papel, margens, fontes, títulos e legendas. Não edite o arquivo
oficial para ajustar o artigo; a procedência está em `modelo_sbc/ORIGEM.md`.
O enunciado da disciplina foi conferido e não impõe outro modelo de relatório.

Os dados do artigo vêm dos CSV de `../parte2/`. As figuras de impressão e as
tabelas podem ser atualizadas pelos scripts indicados no README da Parte 2.
Os valores experimentais originais permanecem preservados.
