LATEXMK ?= latexmk
BRAND_LOGO_SVG := ../../assets/brand/trace-logo.svg
BRAND_LOGO_PDF := figures/trace-logo.pdf
FIGURE_ASSETS := $(wildcard figures/*.pdf figures/*.png figures/scene_atlas/assets/*.png)
TABLE_ASSETS := $(wildcard tables/*.tex)

.PHONY: all clean

all: main.pdf

$(BRAND_LOGO_PDF): $(BRAND_LOGO_SVG)
	python -c "import cairosvg; cairosvg.svg2pdf(url='$(BRAND_LOGO_SVG)', write_to='$(BRAND_LOGO_PDF)')"

main.pdf: main.tex preamble.tex references.bib $(wildcard sections/*.tex) neurips_2026.sty $(FIGURE_ASSETS) $(TABLE_ASSETS) $(BRAND_LOGO_PDF)
	$(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error main.tex

clean:
	$(LATEXMK) -C main.tex
