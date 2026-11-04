# Building the report

The PDF is `main.pdf` (built 2026-11-04 with latexmk/pdflatex from the files here). To rebuild:

```sh
python3 commitments.py --edition v1.1  # Merkle roots over the per-game log and the run artefacts (needs the private per-game log; the released commitments.json is its output)
python3 figures.py --edition v1.1      # regenerates generated/*.tex and figures/* from the result files
python3 manifest.py --edition v1.1     # the edition manifest (Appendix E) from the frozen artefacts and the roots
latexmk -pdf -interaction=nonstopmode main.tex
```

`figures.py` reads the result files from `research/bench/results/v1.1/` relative to the repository root (the `RES`
path near its top); point it at `../data` when building from this package alone. `drafts_v11.py` recomputes
`drafts.json` (draft compositions seen in public replays) and is optional; `generated/` already holds its output.
Requirements: Python 3 with numpy and matplotlib; a TeX distribution with latexmk, natbib and the standard packages
listed in `main.tex`.
