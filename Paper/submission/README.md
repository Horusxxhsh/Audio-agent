# TMM Submission Package (2026-08-04)

Upload-facing package for the IEEE Transactions on Multimedia manuscript
"Texture-Resonance Retrieval (TRR) for Guitar Effect Preset Control"
(revision track, double-blind).

## Files for ScholarOne Manuscripts

| File | Purpose |
|---|---|
| `TMM_main_manuscript.pdf` | Main manuscript PDF (13 pp., double column, 10 pt, letter). |
| `TMM_supplementary_material.pdf` | Supplementary material PDF (4 pp., double column, 10 pt). |
| `TMM_source_package.zip` | LaTeX source (main + supplement + bibliography + figures) for reproducibility or final source-file upload. |
| `figures/` | Standalone figure PDFs (12 figures), if the portal requests separate figure files. |

## Compliance Status (verified 2026-08-04)

- Main manuscript: **13 pages** — within the TMM revised regular-paper limit of
  14 double-column pages (initial submission limit is 10; this package targets
  the revision track).
- Supplementary material: **4 pages** — exactly at the TMM 4-page supplement
  limit (double column, 10 pt).
- Abstract: 161 words, single paragraph — within the required 150–250 words.
- Fonts: no Type 3 fonts in either PDF; body text set in Times (Type 1),
  figure text embedded (TrueType). All fonts embedded.
- Formatting: IEEEtran double-column, 10-pt, letter paper, ≥1-inch margins.
- Build: `latexmk -pdf` passes with zero undefined citations (58 bibliography
  entries, all verified against arXiv/Crossref/DBLP).

## Source Package Contents

`source/` (also zipped as `TMM_source_package.zip`):

- `main.tex`, `content.tex`, `supplementary.tex`, `math_commands.tex`
- `reference.bib` (58 entries)
- `IEEEtran.cls`, `IEEEtranN.bst`
- `figures/` — 12 figure PDFs + `trr_system_framework_v2.svg` (framework source)

Build both PDFs locally:
```
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error supplementary.tex
```
(main needs two `pdflatex` + `bibtex` passes; a clean build regenerates the
`.bbl`.)

## Manual Items Before Upload (author responsibility)

1. **Author metadata**: `main.tex` still carries `\author{Anonymous Authors}`
   for double-blind review. Replace with the final author list, affiliations,
   and corresponding-author contact only if the portal requires a
   non-anonymized file; otherwise keep anonymous and fill metadata in the
   ScholarOne form.
2. **ScholarOne metadata**: title, abstract, index terms, author ORCIDs for
   every author, funding statement, conflict-of-interest declarations,
   EDICS category, and preprint link (arXiv:2603.09332) if desired.
3. **Supplement upload**: upload `TMM_supplementary_material.pdf` as the
   supplemental file at initial submission so it is considered in review.
4. **Page-limit note**: if the editor treats this as an initial submission,
   the 13-page main manuscript exceeds the 10-page initial limit and must be
   trimmed; the package is intentionally formatted for the 14-page revision
   boundary.
