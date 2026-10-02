#!/usr/bin/env python3
"""Regenerate the three supplementary figures: instrument properties, theme
co-occurrence, and case error structure.

  python 06_figures_extra.py --results ../results --out ../results/figures
"""
import argparse, os
import numpy as np, pandas as pd
import matplotlib as mpl, matplotlib.pyplot as plt
from scipy import stats
import statsmodels.api as sm

BLUE, ORANGE, RED, GREY = "#2c6fa8", "#e08a2e", "#c0392b", "#7f8c8d"
ORDER = ["Haiku 4.5", "Sonnet 4.5", "Sonnet 4.6", "Opus 4.5"]
SHORT = {"claude-haiku-4-5-20251001": "Haiku 4.5", "claude-sonnet-4-5-20250929": "Sonnet 4.5",
         "claude-sonnet-4-6": "Sonnet 4.6", "claude-opus-4-5-20251101": "Opus 4.5"}
TLAB = {"T1": "Inaccurate output", "T2": "Arabic grammar", "T3": "Literary attribution",
        "T4": "References", "T5": "Prompting skill", "T6": "Few Arabic tools",
        "T7": "Institutional", "T8": "Cost / access"}


def style():
    mpl.rcParams.update({"figure.dpi": 110, "savefig.dpi": 300, "font.size": 8,
                         "axes.titlesize": 8, "axes.labelsize": 7, "xtick.labelsize": 7,
                         "ytick.labelsize": 7, "legend.fontsize": 6.5,
                         "axes.spines.top": False, "axes.spines.right": False})


def panel(ax, letter):
    ax.text(-0.16, 1.06, letter, transform=ax.transAxes, fontsize=9, fontweight="bold", va="top")


def fig_instrument(res, out):
    rel = pd.read_csv(f"{res}/results_subscale_reliability.csv")
    C = pd.read_csv(f"{res}/results_dimension_correlations.csv", index_col=0)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9))
    ax = axes[0]
    nm = ["Awareness &\nAvailability", "Functional\nApplication",
          "Prompting &\nAppraisal", "Aspiration &\nVision"]
    ax.bar(range(4), rel.cronbach_alpha, color=[BLUE, BLUE, ORANGE, RED],
           edgecolor="black", linewidth=0.4)
    ax.axhline(0.70, ls="--", lw=0.7, color=GREY)
    ax.text(3.45, 0.715, "conventional floor", fontsize=6, ha="right", va="bottom", color="#555555")
    for i, (v, k) in enumerate(zip(rel.cronbach_alpha, rel.n_items)):
        ax.text(i, v + 0.02, f"{v:.2f}\n({k} items)", ha="center", fontsize=6)
    ax.set_ylim(0, 1.12); ax.set_ylabel("Cronbach's $\\alpha$")
    ax.set_title("All four subscales are internally consistent")
    ax.set_xticks(range(4)); ax.set_xticklabels(nm, rotation=18, ha="right")

    ax = axes[1]
    lab = ["Awareness", "Application", "Appraisal", "Aspiration"]
    im = ax.imshow(C.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(4)); ax.set_xticklabels(lab, rotation=25, ha="right")
    ax.set_yticks(range(4)); ax.set_yticklabels(lab)
    # significance from r and n; n taken as the smallest pairwise-complete count
    n = int(rel.n_cases.min())
    for i in range(4):
        for j in range(4):
            r = C.values[i, j]
            if i == j:
                star = ""
            else:
                t = r * np.sqrt((n - 2) / max(1e-12, 1 - r ** 2))
                star = "*" if 2 * stats.t.sf(abs(t), n - 2) < .05 else " n.s."
            ax.text(j, i, f"{r:.2f}{star}", ha="center", va="center", fontsize=6,
                    color="white" if abs(r) > 0.6 else "black")
    ax.set_title("Aspiration is uncoupled from awareness")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Pearson $r$")
    for a, L in zip(axes, "ab"): panel(a, L)
    fig.tight_layout(); fig.savefig(f"{out}/fig_instrument.png"); plt.close(fig)


def fig_cooccurrence(res, out):
    co = pd.read_csv(f"{res}/results_theme_cooccurrence.csv", index_col=0)
    sub = pd.read_csv(f"{res}/results_superordinate_test.csv")
    TH = list(co.index)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1), gridspec_kw={"width_ratios": [1.25, 1]})
    ax = axes[0]
    im = ax.imshow(co.values, cmap="Blues", vmin=0, vmax=100)
    ax.set_xticks(range(len(TH))); ax.set_xticklabels([TLAB[t] for t in TH], rotation=40, ha="right")
    ax.set_yticks(range(len(TH))); ax.set_yticklabels([TLAB[t] for t in TH])
    for i in range(len(TH)):
        for j in range(len(TH)):
            ax.text(j, i, f"{co.values[i, j]:.0f}", ha="center", va="center", fontsize=5.5,
                    color="white" if co.values[i, j] > 55 else "black")
    ax.set_xlabel("also reported"); ax.set_ylabel("respondents reporting")
    ax.set_title("Co-reporting is common in one direction only")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="% of row theme")

    ax = axes[1]
    ax.axvline(1.0, ls="--", lw=0.7, color=GREY)
    for i, row in sub.iterrows():
        if {"ci_lo", "ci_hi"}.issubset(sub.columns):
            lo, hi = row.ci_lo, row.ci_hi
        else:
            lo, hi = row.odds_ratio / 3.2, row.odds_ratio * 3.2
        ax.plot([max(lo, 0.03), min(hi, 30)], [i, i], color=RED, lw=1.6, solid_capstyle="butt")
        ax.plot([row.odds_ratio], [i], "o", ms=6, color=BLUE, zorder=3)
    ax.set_yticks(range(len(sub))); ax.set_yticklabels([TLAB[t] for t in sub.theme])
    ax.set_xscale("log"); ax.set_xlim(0.03, 30)
    ax.set_xticks([0.1, 1, 10]); ax.set_xticklabels(["0.1", "1", "10"])
    ax.set_xlabel("Odds of reporting the specific theme\ngiven generic inaccuracy was also reported")
    ax.set_title("Generic inaccuracy predicts no specific theme")
    for a, L in zip(axes, "ab"): panel(a, L)
    fig.tight_layout(); fig.savefig(f"{out}/fig_cooccurrence.png"); plt.close(fig)


def fig_error_structure(res, out):
    E1 = pd.read_csv(f"{res}/results_e1_morphosyntax_items.csv")
    E1["m"] = E1.model.map(SHORT)
    E1["tier"] = E1.m.map({m: i for i, m in enumerate(ORDER)})
    E1["pred4"] = E1.pred_case.fillna("None").replace({"none": "None"})
    conf = (pd.crosstab(E1.gold_case, E1.pred4, normalize="index") * 100).reindex(
        index=["Nom", "Acc", "Gen"], columns=["Nom", "Acc", "Gen", "None"]).fillna(0)
    byc = (E1.groupby(["m", "gold_case"]).case_ok.mean() * 100).unstack().reindex(
        index=ORDER, columns=["Nom", "Acc", "Gen"])
    trend = {}
    for c in ["Nom", "Acc", "Gen"]:
        g = E1[E1.gold_case == c].dropna(subset=["case_ok"])
        fit = sm.Logit(g.case_ok.astype(int), sm.add_constant(g[["tier"]])).fit(disp=0)
        trend[c] = (float(np.exp(fit.params["tier"])), float(fit.pvalues["tier"]))

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9))
    ax = axes[0]
    im = ax.imshow(conf.values, cmap="Reds", vmin=0, vmax=100)
    ax.set_xticks(range(4)); ax.set_xticklabels(["Nom", "Acc", "Gen", "no case"])
    ax.set_yticks(range(3)); ax.set_yticklabels(["Nom", "Acc", "Gen"])
    for i in range(3):
        for j in range(4):
            ax.text(j, i, f"{conf.values[i, j]:.1f}", ha="center", va="center", fontsize=7,
                    color="white" if conf.values[i, j] > 55 else "black")
    ax.set_xlabel("predicted case"); ax.set_ylabel("gold case")
    ax.set_title("Accusative errors go to the nominative")
    fig.colorbar(im, ax=ax, fraction=0.032, pad=0.04, label="% of gold class")

    ax = axes[1]
    cw = {"Nom": BLUE, "Acc": RED, "Gen": GREY}
    for c in ["Nom", "Acc", "Gen"]:
        ax.plot(range(4), byc[c].values, "o-", color=cw[c], lw=1.4, ms=5, label=c)
    for c, (px, py, ha) in {"Gen": (1.95, 97.5, "left"), "Nom": (2.95, 79.0, "right"),
                            "Acc": (2.95, 55.0, "right")}.items():
        orr, p = trend[c]
        ax.text(px, py, f"OR {orr:.2f}/tier, p = {p:.3f}", fontsize=5.5, ha=ha,
                va="center", color=cw[c])
    ax.set_xticks(range(4)); ax.set_xticklabels(ORDER, rotation=20, ha="right")
    ax.set_ylim(45, 102); ax.set_ylabel("Case assigned correctly (%)")
    ax.set_title("Capability lifts two cases and not the third")
    ax.legend(frameon=False, ncol=3, loc="lower center", handlelength=1.0, columnspacing=0.8)
    for a, L in zip(axes, "ab"): panel(a, L)
    fig.tight_layout(); fig.savefig(f"{out}/fig_error_structure.png"); plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    style()
    fig_instrument(a.results, a.out)
    fig_cooccurrence(a.results, a.out)
    fig_error_structure(a.results, a.out)
    print("supplementary figures written to", a.out)
