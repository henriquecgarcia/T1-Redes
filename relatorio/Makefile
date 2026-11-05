.PHONY: all clean

all:
	mkdir -p build
	pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build relatorio_final.tex
	bibtex build/relatorio_final
	pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build relatorio_final.tex
	pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build relatorio_final.tex
	cp build/relatorio_final.pdf relatorio_final.pdf

clean:
	rm -f build/relatorio_final.aux build/relatorio_final.log build/relatorio_final.bbl
	rm -f build/relatorio_final.blg build/relatorio_final.out build/relatorio_final.pdf
