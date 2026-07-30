# TMM Major Revision Paper

This directory is the canonical LaTeX workspace for the current TMM major
revision manuscript on the `tmm-major-revision-hard-split` branch.

Primary files:

- `main.tex`: main IEEE Transactions entry point.
- `content.tex`: main manuscript body.
- `supplementary.tex`: supplementary material entry point.
- `reference.bib`: bibliography source.
- `figures/`: figures used by the current manuscript.

Build commands:

```bash
cd Paper
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error supplementary.tex
```

Legacy paper outputs that previously occupied `Paper/` were moved to
`archive/Paper_legacy_20260516/`.
