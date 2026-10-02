# Licences for non-code material

This repository contains material under three different licences. The folder a
file sits in determines which one applies.

## 1. Code — MIT

Everything in `code/` is released under the MIT License in [`LICENSE`](LICENSE).

## 2. Authors' own data and results — CC BY 4.0

The following are released under the Creative Commons Attribution 4.0
International licence (<https://creativecommons.org/licenses/by/4.0/>):

- `data/arabic_genai_competency_data.csv`
- `data/codebook.csv`
- `data/human_coding_sheet_BLANK.xlsx`
- everything in `results/`
- `probes/probe_citation_raw.json`, `probes/probe_citation_topics.json`,
  `probes/probe_e3_items.csv`, `probes/probe_e3_raw.json`,
  `probes/probe_attribution_spec.json`, `probes/ms_models.json`, `probes/ms_sys.txt`

You may share and adapt this material for any purpose, including commercially,
provided you give appropriate credit to Fayez Sobhy Abdelsalam Torky, Mohamed Mustafa Hassanein, Rabie A. Ramadan and Sundos Al Subhi and cite the accompanying paper.

## 3. Material derived from UD Arabic-PADT — CC BY-NC-SA 3.0

`data/gold/ar_padt-ud-test.conllu` is the test split of the Universal
Dependencies Arabic-PADT treebank, redistributed unmodified under its original
licence, Creative Commons Attribution-NonCommercial-ShareAlike 3.0
(<https://creativecommons.org/licenses/by-nc-sa/3.0/>). The original licence and
README are kept alongside it in `data/gold/PADT_LICENSE.txt` and
`data/gold/PADT_README.md`.

The ShareAlike term carries over to work derived from the treebank. The
following files are therefore also released under CC BY-NC-SA 3.0, not CC BY 4.0,
because their content is extracted from PADT annotation:

- `probes/probe_morphosyntax_gold.json` (gold UPOS and case labels for the sampled targets)
- `probes/probe_morphosyntax_prompts.json` (prompts containing PADT sentence text)
- `probes/probe_morphosyntax_raw.json` (model returns over PADT sentences)
- `results/results_e1_morphosyntax_items.csv` (item-level scoring against PADT gold)

Reuse of those four files is non-commercial, requires attribution to the PADT
and UD teams as set out in `data/gold/PADT_README.md`, and derivative works must
be shared under the same licence.
