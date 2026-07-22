LATEXMK ?= latexmk
BRAND_LOGO_SVG := ../../assets/brand/trace-logo.svg
BRAND_LOGO_PDF := figures/trace-logo.pdf
BRAND_MARK_SVG := ../../assets/brand/trace-mark.svg
BRAND_MARK_PDF := figures/trace-mark.pdf
FIGURE_ASSETS := $(wildcard figures/*.pdf figures/*.png figures/scene_atlas/assets/*.png)
TABLE_ASSETS := $(wildcard tables/*.tex)

.PHONY: all clean results training-dynamics iid-taxonomy external-cis

all: main.pdf

results:
	python scripts/build_results_assets.py

training-dynamics:
	python scripts/build_training_dynamics.py

iid-taxonomy:
	python scripts/build_iid_taxonomy_analysis.py

external-cis:
	python scripts/build_external_bootstrap_cis.py

$(BRAND_LOGO_PDF): $(BRAND_LOGO_SVG)
	python -c "import cairosvg; cairosvg.svg2pdf(url='$(BRAND_LOGO_SVG)', write_to='$(BRAND_LOGO_PDF)')"

$(BRAND_MARK_PDF): $(BRAND_MARK_SVG)
	python -c "import cairosvg; cairosvg.svg2pdf(url='$(BRAND_MARK_SVG)', write_to='$(BRAND_MARK_PDF)')"

main.pdf: results training-dynamics main.tex preamble.tex references.bib $(wildcard sections/*.tex) neurips_2026.sty $(FIGURE_ASSETS) $(TABLE_ASSETS) $(BRAND_LOGO_PDF) $(BRAND_MARK_PDF)
	$(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error main.tex

clean:
	$(LATEXMK) -C main.tex
