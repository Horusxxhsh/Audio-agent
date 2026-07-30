# TMM Submission Checklist

This checklist records the local submission state for the current IEEE
Transactions on Multimedia manuscript package.

## Official Format Constraints Checked

- IEEE Transactions on Multimedia regular-paper initial submission page limit:
  10 double-column pages, 10-point font, including title, authors, abstract,
  text, figures, tables, and references. Supplemental material is not counted.
- IEEE Signal Processing Society revised regular-paper limit for TMM: 14
  double-column pages.
- IEEE article structure includes title page, abstract, index terms, body,
  conclusion, acknowledgments if any, references, and optional biographies.
- IEEE abstract guidance: one paragraph, 150--250 words.

Official sources:

- https://signalprocessingsociety.org/publications-resources/information-authors
- https://signalprocessingsociety.org/index.php/publications-resources/ieee-transactions-multimedia
- https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/authoring-tools-and-templates/tools-for-ieee-authors/ieee-article-templates/
- https://journals.ieeeauthorcenter.ieee.org/wp-content/uploads/sites/7/IEEE-Editorial-Style-Manual-for-Authors.pdf

## Local Package State

- Main manuscript: `Paper/main.tex`
- Main body: `Paper/content.tex`
- Supplement: `Paper/supplementary.tex`
- Bibliography: `Paper/reference.bib`
- Main PDF: `Paper/main.pdf`
- Supplement PDF: `Paper/supplementary.pdf`

Current local validation:

- `Paper/main.pdf`: 12 pages, letter paper.
- Abstract: 154 words, single paragraph.
- `latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex`: passed.
- `latexmk -pdf -interaction=nonstopmode -halt-on-error supplementary.tex`: passed.
- Claim audit on `content.tex` and `supplementary.tex`: passed with no findings.

## Human Items Before ScholarOne Submission

- Replace `Anonymous Authors` in `Paper/main.tex` with the final author list,
  affiliations, and corresponding-author contact information unless the
  submission portal explicitly requires anonymization.
- Confirm whether this is an initial submission or a revision. The current
  expanded manuscript is formatted for the revised regular-paper 14-page
  boundary, not for the stricter initial 10-page limit.
- Prepare the ScholarOne metadata: title, abstract, index terms, author ORCIDs,
  funding statement, conflict-of-interest declarations, and any preprint links.
- Upload `Paper/main.pdf` as the main manuscript and `Paper/supplementary.pdf`
  as supplemental material if the portal requests separate supplemental files.
