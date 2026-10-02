#!/usr/bin/env python3
"""Regenerate all five paper figures from the saved result tables.

  python 05_figures.py --results ../../05_results --data ../../04_data --out ../../05_results/figures
"""
import argparse, os
import numpy as np, pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

SHORT = {"claude-haiku-4-5-20251001": "Haiku 4.5", "claude-sonnet-4-5-20250929": "Sonnet 4.5",
         "claude-sonnet-4-6": "Sonnet 4.6", "claude-opus-4-5-20251101": "Opus 4.5"}
ORDER = ["Haiku 4.5", "Sonnet 4.5", "Sonnet 4.6", "Opus 4.5"]
CASE_COLOURS = {"Nom": "#2c6fa8", "Acc": "#c0392b", "Gen": "#7f8c8d"}
GREY = "#8a8a8a"


def style():
    mpl.rcParams.update({"figure.dpi": 110, "savefig.dpi": 300, "font.size": 8,
                         "axes.titlesize": 8, "axes.labelsize": 7, "xtick.labelsize": 7,
                         "ytick.labelsize": 7, "legend.fontsize": 7,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": False, "savefig.bbox": "tight"})


def letter(ax, ch):
    ax.text(-0.16, 1.06, ch, transform=ax.transAxes, fontsize=10, fontweight="bold", va="top")


def fig_dimensions(res, out):
    prof = pd.read_csv(f"{res}/repro_dimension_profile.csv") if os.path.exists(
        f"{res}/repro_dimension_profile.csv") else None
    if prof is None:
        print("skip fig_survey_dimensions (run 01_survey_analysis.py first)"); return
    # the headline gap is the PAIRED mean difference, not the difference of rounded means
    import json as _json, os as _os
    _sp = f"{res}/repro_study1_statistics.json"
    gap = (_json.load(open(_sp))["aspiration_vs_application"]["mean_diff"]
           if _os.path.exists(_sp) else None)
    names = ["Awareness &\nAvailability", "Functional\nApplication",
             "Prompting &\nAppraisal", "Aspiration\n& Vision"]
    mu, se = prof["mean"].values, (prof["sd"] / np.sqrt(prof["n"])).values
    fig, ax = plt.subplots(figsize=(4.4, 2.9))
    ax.bar(names, mu, yerr=1.96 * se, capsize=3,
           color=["#4a7ca8", "#4a7ca8", "#e08a2e", "#c0392b"], edgecolor="black", linewidth=0.4)
    ax.axhline(3, ls="--", lw=0.7, color=GREY)
    ax.text(3.48, 3.06, "scale midpoint", fontsize=6, ha="right", va="bottom", color="#555555")
    for i, (v, s) in enumerate(zip(mu, se)):
        ax.text(i, v + 1.96 * s + 0.12, f"{v:.2f}", ha="center", fontsize=6)
    ax.set_ylim(0, 5); ax.set_ylabel("Mean score (1-5)")
    ax.set_title("Ambition runs {} points ahead of practice".format(
        f"{gap:.2f}" if gap is not None else f"{mu[3]-mu[1]:.2f}"))
    fig.tight_layout(); fig.savefig(f"{out}/fig_survey_dimensions.png"); plt.close(fig)


def fig_barriers(res, out):
    prev = pd.read_csv(f"{res}/barrier_theme_prevalence.csv")
    prev = prev[~prev.iloc[:, 0].astype(str).str.startswith("T9")].sort_values("pct")
    nice = {"T1_inaccurate_output": "Inaccurate / unreliable output",
            "T2_arabic_grammar_morphology": "Weak Arabic grammar & morphology",
            "T3_literary_misattribution": "Hallucinated literary attribution",
            "T4_fabricated_references": "Fabricated / missing references",
            "T5_prompting_appraisal_skill": "Weak prompting / appraisal skill",
            "T6_lack_of_arabic_tools": "Few Arabic-supporting tools",
            "T7_institutional_resistance": "Faculty / institutional resistance",
            "T8_access_cost_connectivity": "Cost, limits or connectivity"}
    fig, ax = plt.subplots(figsize=(5.2, 3.0))
    ylab = prev["label"] if "label" in prev.columns else [nice.get(t, t) for t in prev.iloc[:, 0]]
    ax.barh(list(ylab), prev.pct,
            color="#4a7ca8", edgecolor="black", linewidth=0.4)
    for i, (v, k) in enumerate(zip(prev.pct, prev.kappa_A_vs_B)):
        ax.text(v + 1.0, i, f"{v:.1f}  (\u03ba={k:.2f})", va="center", fontsize=6)
    ax.set_xlim(0, 95); ax.set_xlabel("% of the 141 respondents (\u03ba = coder agreement)")
    ax.set_title("Generic inaccuracy dominates the reports;\nattributing failure to the student codes least reliably")
    fig.tight_layout(); fig.savefig(f"{out}/fig_survey_barriers.png"); plt.close(fig)


def fig_evaluation(res, out):
    E1 = pd.read_csv(f"{res}/results_e1_morphosyntax_items.csv")
    E1["m"] = E1.model.map(SHORT)
    cases = (E1.groupby(["m", "gold_case"]).case_ok.mean() * 100).unstack()
    tab = pd.read_csv(f"{res}/results_e2_model_summary.csv")
    tab["m"] = tab.iloc[:, 0].map(lambda s: SHORT.get(s, SHORT.get("claude-" + str(s), s)))
    e3 = pd.read_csv(f"{res}/results_e3_model_summary.csv")
    e3["m"] = e3.iloc[:, 0].map(lambda s: SHORT.get(s, SHORT.get("claude-" + str(s), s)))

    x = np.arange(len(ORDER)); w = 0.26
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.0))
    ax = axes[0]
    for j, c in enumerate(["Nom", "Acc", "Gen"]):
        ax.bar(x + (j - 1) * w, [cases.loc[m, c] for m in ORDER], w,
               color=CASE_COLOURS[c], edgecolor="black", linewidth=0.4, label=c)
    ax.set_xticks(x); ax.set_xticklabels(ORDER, rotation=20, ha="right")
    ax.set_ylabel("Case assigned correctly (%)"); ax.set_ylim(0, 105)
    ax.set_title("Accusative is weakest")
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.02),
              columnspacing=0.7, handlelength=0.8, handletextpad=0.35)

    ax = axes[1]
    stack = [("verified_as_supplied", "verified as supplied", "#2c6fa8"),
             ("real_work_wrong_identifier", "real work, wrong identifier", "#e08a2e"),
             ("no_trace_in_either_index", "no trace in either index", "#c0392b")]
    bot = np.zeros(len(ORDER))
    for col, lab, colour in stack:
        v = np.array([float(tab.loc[tab.m == m, col].iloc[0]) if (tab.m == m).any() else 0
                      for m in ORDER])
        ax.bar(ORDER, v, bottom=bot, color=colour, edgecolor="black", linewidth=0.4, label=lab)
        bot += v
    zero = [m for m in ORDER if (tab.m == m).any() and float(tab.loc[tab.m == m, "refs_supplied"].iloc[0]) == 0]
    for m in zero:
        i = ORDER.index(m)
        ax.plot([i], [0], marker="_", ms=9, color="black", lw=0)
        ax.text(i, 4, "abstained\non all 20", ha="center", va="bottom", fontsize=6)
    ax.set_xticks(x); ax.set_xticklabels(ORDER, rotation=20, ha="right")
    ax.set_ylabel("References supplied (count)"); ax.set_ylim(0, 112)
    ax.set_title("Most references are unusable as given")
    ax.legend(frameon=False, fontsize=6, loc="upper left", handlelength=0.8,
              handletextpad=0.35, borderpad=0.1)

    ax = axes[2]
    vals = [float(e3.loc[e3.m == m, "title_speculation_or_worse_pct"].iloc[0]) for m in ORDER]
    ax.bar(ORDER, vals, color="#7f8c8d", edgecolor="black", linewidth=0.4)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.7, f"{v:.1f}", ha="center", fontsize=6)
    ax.set_xticks(x); ax.set_xticklabels(ORDER, rotation=20, ha="right")
    ax.set_ylabel("Replies supplying content (%)"); ax.set_ylim(0, 30)
    ax.set_title("Opus 4.5 and Sonnet 4.5 speculate most")
    for a_, ch in zip(axes, "abc"):
        a_.margins(y=0.04); letter(a_, ch)
    fig.tight_layout(); fig.savefig(f"{out}/fig_model_evaluation.png"); plt.close(fig)


def fig_alignment(res, out):
    al = pd.read_csv(f"{res}/results_alignment.csv").sort_values("student_pct")
    lab = ["Hallucinated literary\nattribution" if "Hallucinated" in b else
           "Fabricated or missing\nreferences" if "Fabricated" in b else
           "Weak Arabic grammar\nand morphology" if "grammar" in b else
           "Inaccurate or unreliable\noutput (generic)" for b in al.breakdown]
    fig, ax = plt.subplots(figsize=(5.6, 3.0))
    for i, (_, r) in enumerate(al.iterrows()):
        ax.plot([r.measured_best, r.measured_worst], [i, i], color="#c0392b", lw=3.0,
                solid_capstyle="butt", zorder=2,
                label="measured failure rate,\nbest to worst model" if i == 0 else None)
        ax.annotate("", xy=(r.measured_best, i), xytext=(r.student_pct, i),
                    arrowprops=dict(arrowstyle="->", lw=0.7, color="#999999",
                                    shrinkA=5, shrinkB=4), zorder=1)
        ax.plot([r.student_pct], [i], "o", ms=7, color="#2c6fa8", zorder=3,
                label="students reporting it" if i == 0 else None)
    ax.set_yticks(range(len(al))); ax.set_yticklabels(lab)
    ax.set_xlabel("Percent"); ax.set_xlim(-3, 95)
    ax.set_title("Learner concern and measured failure run\n"
                 "in opposite directions")
    ax.legend(frameon=False, loc="center right", handlelength=1.2)
    fig.tight_layout(); fig.savefig(f"{out}/fig_alignment.png"); plt.close(fig)


def fig_stance(res, data, out):
    """Stance x competency strip plot. Needs the survey file for composites and the
    reconciliation file for the final stance codes."""
    import os
    dat = pd.read_csv(f"{data}/arabic_genai_competency_data.csv")
    codes = pd.read_csv(f"{res}/q4_coding_reconciliation.csv")[["participant_id", "final_code"]]
    dims = ("AW", "AP", "PC", "AS")
    comp = pd.DataFrame({d: dat[[c for c in dat.columns if c.startswith(d)]].mean(axis=1) for d in dims})
    m = dat[["participant_id"]].merge(codes, on="participant_id", how="left")
    m["overall"] = comp[list(dims)].mean(axis=1).values
    keys, labels = ["dependency", "conditional", "innovation"], ["Dependency", "Conditional", "Innovation"]
    colours = ["#c0392b", "#e08a2e", "#2c6fa8"]
    groups = [m[(m.final_code == k) & m.overall.notna()].overall.values for k in keys]
    rng = np.random.default_rng(0)
    fig, ax = plt.subplots(figsize=(4.0, 2.9))
    for i, (g, c) in enumerate(zip(groups, colours)):
        ax.plot(i + rng.uniform(-0.12, 0.12, len(g)), g, "o", ms=4, alpha=0.65,
                color=c, markeredgewidth=0)
        ax.plot([i - 0.22, i + 0.22], [np.median(g)] * 2, color="black", lw=1.6, zorder=3)
        ax.text(i, 5.02, f"n={len(g)}", ha="center", fontsize=6)
    ax.set_xticks(range(3)); ax.set_xticklabels(labels)
    ax.set_ylabel("Overall competency score (1-5)"); ax.set_ylim(1, 5.2)
    from scipy import stats as _st
    _g = [g for g in groups if len(g)]
    _F, _p = _st.f_oneway(*_g)
    _k = len(_g); _N = sum(len(g) for g in _g)
    _e2 = (_F * (_k - 1)) / (_F * (_k - 1) + (_N - _k))
    ax.set_title("Dependency framing sits lowest\n"
                 f"F({_k-1}, {_N-_k}) = {_F:.1f}, $\\eta^2$ = {_e2:.2f}".replace("0.", "."))
    fig.tight_layout(); fig.savefig(f"{out}/fig_survey_stance.png"); plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True); ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    style()
    fig_dimensions(a.results, a.out)
    fig_barriers(a.results, a.out)
    fig_stance(a.results, a.data, a.out)
    fig_evaluation(a.results, a.out)
    fig_alignment(a.results, a.out)
    print("figures written to", a.out)
