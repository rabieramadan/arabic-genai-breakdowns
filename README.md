# Arabic generative-AI breakdowns: survey and evaluation suite

Data, code and evaluation suite for a two-study paper pairing a learner survey of Arabic
language and literature students with a direct evaluation of generative-AI output on the
failure categories those learners reported.

The survey covers 145 Arabic language and literature students at a public university in Oman.
The evaluation operationalises the breakdowns those students reported as three probes with
independent gold standards, run across four commercially available models. The contribution is
the integration: reported prevalence and measured failure rate are close to inverted — the
breakdown students named most often is the one models fail least, and the breakdown they named
third is the one models fail most.

## Layout

| Folder | Contents |
|---|---|
| `code/` | Six runnable analysis and figure scripts |
| `data/` | De-identified survey responses, codebook, and the UD Arabic-PADT test split |
| `probes/` | Probe items, gold annotations, prompts, and raw model returns |
| `results/` | Every result table and figure reported in the paper |
| `docs/` | Statistical methods: every equation and every figure specification |
| `archive_superseded/` | Earlier-revision working files, kept for transparency, not for citation |

## Scripts

| Script | What it does |
|---|---|
| `01_survey_analysis.py` | Composites, paired comparison, repeated-measures ANOVA, stance comparison, calibration models |
| `02_probe_morphosyntax.py` | `build` samples gold case-bearing targets from CoNLL-U; `score` scores model returns and writes the confusion matrix and McNemar tests |
| `03_probe_citations.py` | Strict reference parsing, then Crossref and OpenAlex verification with the three-way classification |
| `04_probe_confabulation.py` | `check-absent` verifies constructed bibliographic entities are absent from both indexes; `score` applies the strict scheme |
| `05_figures.py` | Regenerates the five main paper figures from the result tables |
| `06_figures_extra.py` | Regenerates the three supplementary figures |

Model querying is not built in. `02_probe_morphosyntax.py run` takes a callable, so any provider
SDK can be plugged in without editing the scoring code. The raw returns used in the paper are in
`probes/`, so every scoring step reproduces offline.

## Quick start

```bash
pip install -r requirements.txt
cd code

# survey statistics -> results/repro_study1_statistics.json
python 01_survey_analysis.py --data ../data/arabic_genai_competency_data.csv \
    --coding ../results/q4_coding_reconciliation.csv \
    --themes ../results/barrier_theme_coding.csv --out ../results

# all eight figures -> results/figures/
python 05_figures.py --results ../results --data ../data --out ../results/figures
python 06_figures_extra.py --results ../results --out ../results/figures
```

`01_survey_analysis.py` reproduces the four dimension means (2.76, 2.97, 3.37, 4.07), the paired
comparison t(143) = 13.68 with a mean difference of 1.11 scale points, the repeated-measures
F(3, 429) = 115.53, and the stance comparison F(2, 132) = 17.76 with eta-squared = .21 over
n = 135.

Scoring the probes offline:

```bash
python 02_probe_morphosyntax.py score --raw ../probes/probe_morphosyntax_raw.json \
    --gold ../probes/probe_morphosyntax_gold.json --out ../results
python 04_probe_confabulation.py score --raw ../probes/probe_e3_raw.json \
    --items ../probes/probe_e3_items.csv --out ../results
```

`03_probe_citations.py verify` is the one step that needs network access, because it queries
Crossref and OpenAlex:

```bash
python 03_probe_citations.py verify --raw ../probes/probe_citation_raw.json \
    --out ../results --openalex-key $OPENALEX_API_KEY
```

OpenAlex requires an API key on every request; Crossref does not, but accepts a contact address
via `--email` and gives better service when one is supplied. Verification results depend on the
state of both indexes on the day you run it, so counts may drift slightly from the published
ones as records are added.

## Figures

All eight figures in `results/figures/` regenerate from the result tables alone.

| File | Content |
|---|---|
| `fig_survey_dimensions.png` | Four competency dimension means with 95% intervals |
| `fig_survey_barriers.png` | Prevalence of the eight reported breakdown themes with coder agreement |
| `fig_survey_stance.png` | Overall competency by stance toward generative AI |
| `fig_model_evaluation.png` | Case accuracy, reference verification and confabulation by model |
| `fig_alignment.png` | Reported prevalence against measured failure rate, the paper's headline result |
| `fig_instrument.png` | Subscale reliability and inter-dimension correlations |
| `fig_cooccurrence.png` | Theme co-reporting matrix and superordinate-theme odds ratios |
| `fig_error_structure.png` | Case confusion matrix and capability trend by case class |

`docs/` documents the equation behind every statistic and the full specification of every figure.

## Notes on method

Three decisions in this code matter for anyone reusing it.

First, reference parsing is strict: a permissive split on the field delimiter turns a model's own
format explanation into a phantom reference, which inverts the abstention rate for models that
decline to answer.

Second, absence of a constructed title is established by subject-phrase containment rather than a
title-similarity threshold, because shared frame wording alone pushes Arabic titles above 0.60
similarity against unrelated works.

Third, a reply counts as substantive — and so enters the barrier-corpus denominator of 141 — only
if it is not blank, not bare punctuation, and not a bare affirmative or negative. The rule is
implemented in `substantive()` in `01_survey_analysis.py` and governs every reported denominator.

## Coding provenance

Qualitative coding in the released files was produced by a documented rule-based first pass, an
independent second pass, and automated adjudication of the 29 disagreements. Per-record decisions
are in `results/q4_adjudication_sheet.csv`, which keeps the `coder_A_rule_based`,
`coder_B_independent` and `automated_adjudication` columns separate, plus an empty
`human_decision` column for confirmation. Human confirmation of those decisions is pending.
`results/which_results_depend_on_coding.csv` lists which reported results depend on text coding
and which do not; the Likert-based statistics do not.

## Data and ethics

Survey data are de-identified. Respondents are identified only by `participant_id` (P001 to
P145). No free-text response in the released files contains an email address, URL, phone number,
numeric identifier or personal name. Participants gave informed consent for anonymised data to be
used for research and publication. The study was approved by the Research and Ethics Committee of
the College of Arts and Social Sciences, Sultan Qaboos University, Muscat, Oman.

Note that `study_level` and `gpa` are retained and are, in combination, weakly identifying within
a single department. Anyone redistributing this file in a smaller or more targeted subset should
consider dropping them.

## Licences

Three licences apply, by folder. See [`DATA_LICENSE.md`](DATA_LICENSE.md) for the full statement.

- `code/` — MIT, see [`LICENSE`](LICENSE)
- Authors' own data, probes and results — CC BY 4.0
- `data/gold/` and the four files derived from it — CC BY-NC-SA 3.0, inherited from UD
  Arabic-PADT; non-commercial, attribution, share-alike

## Citation

See [`CITATION.cff`](CITATION.cff). Replace `USERNAME/REPOSITORY` with the repository path once
it is published, and add the Zenodo DOI if you archive a release.
