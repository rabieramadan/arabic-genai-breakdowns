#!/usr/bin/env python3
"""Study 1: survey analysis. Reproduces every survey statistic in the paper.

Usage:  python 01_survey_analysis.py --data ../../04_data/arabic_genai_competency_data.csv \
                                     --coding ../../05_results/q4_coding_reconciliation.csv \
                                     --themes ../../05_results/barrier_theme_coding.csv \
                                     --out ../../05_results
"""
import argparse, json, re
import numpy as np, pandas as pd
from scipy import stats
import statsmodels.api as sm

DIMS = ("AW", "AP", "PC", "AS")
JUNK = {"", ".", "..", "...", "-", "لا", "لا شيء", "لاشيء", "لايوجد", "لا يوجد", "لا توجد",
        "لاتوجد", "لا اعلم", "لا أعلم", "لا اعرف", "لا أعرف", "ولا شيء", "نعم",
        "ok", "no", "none", "na", "n/a", "؟", "?"}


def substantive(s):
    """A response counts as substantive if it is not blank, not punctuation, and not a
    bare affirmative/negative. This is the definition used for every reported denominator."""
    if pd.isna(s):
        return False
    t = re.sub(r"\s+", " ", str(s)).strip().strip("،.!؟").strip()
    return t.lower() not in JUNK and len(t) >= 3


def composites(dat):
    cols = {d: [c for c in dat.columns if c.startswith(d)] for d in DIMS}
    comp = pd.DataFrame({d: dat[c].mean(axis=1, skipna=True) for d, c in cols.items()})
    comp["overall"] = comp[list(DIMS)].mean(axis=1)
    return comp, cols


def rm_anova(X):
    """One-way repeated-measures ANOVA on complete cases across the four composites."""
    n, k = X.shape
    gm = X.values.mean()
    ss_cond = n * ((X.mean(0) - gm) ** 2).sum()
    ss_subj = k * ((X.mean(1) - gm) ** 2).sum()
    ss_err = ((X.values - gm) ** 2).sum() - ss_cond - ss_subj
    df1, df2 = k - 1, (k - 1) * (n - 1)
    return (ss_cond / df1) / (ss_err / df2), df1, df2, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--coding", required=True, help="q4_coding_reconciliation.csv (final stance codes)")
    ap.add_argument("--themes", required=True, help="barrier_theme_coding.csv (final theme labels)")
    ap.add_argument("--out", default=".")
    a = ap.parse_args()

    dat = pd.read_csv(a.data)
    comp, cols = composites(dat)
    out = {"n_respondents": int(len(dat))}

    # --- competency profile -------------------------------------------------
    prof = pd.DataFrame({
        "dimension": list(DIMS),
        "n_items": [len(cols[d]) for d in DIMS],
        "n": [int(comp[d].notna().sum()) for d in DIMS],
        "mean": [round(comp[d].mean(), 3) for d in DIMS],
        "sd": [round(comp[d].std(), 3) for d in DIMS],
    })
    prof.to_csv(f"{a.out}/repro_dimension_profile.csv", index=False)

    # aspiration vs application, paired on respondents with both composites
    pair = comp[["AS", "AP"]].dropna()
    t, p = stats.ttest_rel(pair["AS"], pair["AP"])
    d_z = (pair["AS"] - pair["AP"]).mean() / (pair["AS"] - pair["AP"]).std()
    out["aspiration_vs_application"] = {
        "n": int(len(pair)), "df": int(len(pair) - 1), "t": round(float(t), 4),
        "p": float(p), "mean_diff": round(float((pair["AS"] - pair["AP"]).mean()), 4),
        "d_z": round(float(d_z), 3)}

    F, df1, df2, n_rm = rm_anova(comp[list(DIMS)].dropna())
    out["rm_anova_four_dimensions"] = {"F": round(float(F), 2), "df1": df1, "df2": df2, "n": int(n_rm)}

    # --- denominators ------------------------------------------------------
    barrier = dat[["Q2", "Q6"]].apply(lambda r: substantive(r.Q2) or substantive(r.Q6), axis=1)
    out["barrier_corpus_n"] = int(barrier.sum())
    out["stance_substantive_n"] = int(dat["Q4"].apply(substantive).sum())

    # --- stance x competency ----------------------------------------------
    codes = pd.read_csv(a.coding)[["participant_id", "final_code"]]
    m = dat[["participant_id"]].merge(codes, on="participant_id", how="left")
    m["overall"] = comp["overall"].values
    sub = m[m.final_code.isin(["dependency", "conditional", "innovation"]) & m.overall.notna()]
    groups = [g.overall.values for _, g in sub.groupby("final_code")]
    F2, p2 = stats.f_oneway(*groups)
    H, ph = stats.kruskal(*groups)
    k, N = len(groups), len(sub)
    out["stance_anova"] = {
        "n": int(N), "F": round(float(F2), 2), "df1": k - 1, "df2": int(N - k), "p": float(p2),
        "eta2": round(float((F2 * (k - 1)) / (F2 * (k - 1) + (N - k))), 3),
        "kruskal_H": round(float(H), 2), "kruskal_p": float(ph),
        "group_means": {str(g): round(float(v), 3) for g, v in sub.groupby("final_code").overall.mean().items()},
        "group_n": {str(g): int(v) for g, v in sub.groupby("final_code").size().items()}}
    out["stance_uncodable_n"] = int(len(m) - N)

    # --- calibration models ------------------------------------------------
    th = pd.read_csv(a.themes)
    X = pd.DataFrame({
        "T4": th["T4_fabricated_references"].astype(int),
        "T2": th["T2_arabic_grammar_morphology"].astype(int),
        "PC": comp["PC"].values,
        "prior": dat.prior_ai_training.astype(str).str.strip().str.lower()
                    .isin(["yes", "نعم", "1", "true"]).astype(int),
        "heavy": dat.weekly_ai_use.astype(str).str.contains(">5|3-5", na=False).astype(int),
    })[barrier.values].dropna()
    calib = {}
    for target in ("T4", "T2"):
        fit = sm.Logit(X[target], sm.add_constant(X[["PC", "prior", "heavy"]])).fit(disp=0)
        calib[target] = {"n": int(len(X)),
                         "OR_PC": round(float(np.exp(fit.params["PC"])), 2),
                         "p_PC": round(float(fit.pvalues["PC"]), 4),
                         "pseudo_r2": round(float(fit.prsquared), 3)}
    out["calibration"] = calib

    with open(f"{a.out}/repro_study1_statistics.json", "w") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
