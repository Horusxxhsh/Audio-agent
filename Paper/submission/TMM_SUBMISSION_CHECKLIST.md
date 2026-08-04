# TMM Submission Checklist (updated 2026-08-04)

Local submission state for the IEEE Transactions on Multimedia revision
package in `Paper/submission/`.

## Official Format Constraints (from IEEE SPS Information for Authors)

- TMM regular paper, **initial submission**: max **10 double-column pages**,
  10-point font (counts title, authors, abstract, text, figures, tables,
  references). Supplemental material excluded.
- TMM regular paper, **revision**: max **14 double-column pages**, 10-point
  font; appendices/proofs may go to supplemental material.
- Supplementary material: max **4 double-column pages**, 10-point font;
  multimedia/code/data allowed with a README.
- Abstract: one paragraph, **150–250 words**, no citations/abbreviations/
  displayed equations.
- Figures: PS/EPS/PDF/PNG/TIFF with embedded fonts (no Type 3 for TMM PDFs);
  text in figures 8–10 pt; color figures must remain readable in grayscale.
- All authors need ORCIDs; portal metadata must match the manuscript.

Sources:
- https://signalprocessingsociety.org/index.php/publications-resources/information-authors
- https://signalprocessingsociety.org/index.php/publications-resources/ieee-transactions-multimedia
- https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/prepare-supplementary-materials/

## Verified Local State (2026-08-04)

| Check | Result |
|---|---|
| `main.pdf` page count | 13 (letter, double column) — within 14-page revision limit |
| `supplementary.pdf` page count | 4 — within 4-page supplement limit |
| Abstract word count | 161 |
| Type 3 fonts (both PDFs) | none; Type 1 (Times) + embedded TrueType only |
| Undefined citations | 0 (58 verified bibliography entries) |
| Build (`latexmk -pdf`, both files) | passed |
| Framework figure installed | `figures/retrieval_grounded_pipeline.pdf` (from user SVG, ≥8 pt text) |
| Data freeze | all figures drawn from frozen CSV/JSON; experiment code untouched |

## Human Items Before ScholarOne Submission

- [ ] Decide anonymization: `main.tex` currently uses `Anonymous Authors`
  (double-blind mode). If not blind, fill real authors/affiliations.
- [ ] Fill ScholarOne metadata: title, abstract, index terms, all author
  ORCIDs, funding statement, COI declaration, EDICS, preprint link
  (arXiv:2603.09332).
- [ ] Confirm submission track: revision (14-page limit, current package OK)
  vs. initial (10-page limit — would require trimming ~3 pages).
- [ ] Upload: `TMM_main_manuscript.pdf` (main), `TMM_supplementary_material.pdf`
  (supplement), optionally `TMM_source_package.zip` (source) and `figures/`
  (standalone figure PDFs).
- [ ] If resubmission after prior reviews: attach prior review reports
  verbatim plus a point-by-point response.
