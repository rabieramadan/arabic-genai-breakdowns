#!/usr/bin/env python3
"""Probe 1: Arabic morphosyntactic annotation scored against UD Arabic-PADT gold.

Two stages. `build` samples the gold items from a CoNLL-U file; `score` scores raw
model returns against them. Querying models is deliberately left to `run`, which takes a
callable so the suite is not tied to any one provider's SDK.

  python 02_probe_morphosyntax.py build --conllu ../../04_data/gold/ar_padt-ud-test.conllu \
      --out-prompts ../../06_probes/probe_morphosyntax_prompts.json \
      --out-gold ../../06_probes/probe_morphosyntax_gold.json
  python 02_probe_morphosyntax.py score --raw ../../06_probes/probe_morphosyntax_raw.json \
      --gold ../../06_probes/probe_morphosyntax_gold.json --out ../../05_results
"""
import argparse, json, re, itertools
from collections import Counter
import numpy as np, pandas as pd
from scipy import stats

SEED = 20260904
CASES = ("Nom", "Acc", "Gen")
TARGET_POS = {"NOUN", "ADJ", "PROPN", "NUM", "PRON"}
UPOS_SET = "NOUN, PROPN, ADJ, VERB, AUX, PRON, DET, ADP, NUM, CCONJ, SCONJ, ADV, PART, PUNCT, X"
SYSTEM = ("You are annotating Modern Standard Arabic following Universal Dependencies conventions. "
          f"For each requested token index give its UPOS tag from exactly this set: {UPOS_SET}. "
          "Also give its grammatical case (i'rab) as exactly one of: Nom, Acc, Gen, or None if the "
          "token does not carry case. Output one line per requested index in the form index|UPOS|Case "
          "with no other text, no explanation, no markdown.")


def parse_conllu(path):
    sents, cur = [], None
    for line in open(path, encoding="utf8"):
        line = line.rstrip("\n")
        if line.startswith("# sent_id"):
            cur = {"sent_id": line.split("=", 1)[1].strip(), "toks": []}
        elif line.startswith("# text ") and cur is not None:
            cur["text"] = line.split("=", 1)[1].strip()
        elif not line.strip():
            if cur and cur["toks"]:
                sents.append(cur)
            cur = None
        elif cur is not None and not line.startswith("#"):
            p = line.split("\t")
            if "-" in p[0] or "." in p[0]:
                continue                      # skip multiword-token ranges and empty nodes
            feats = dict(x.split("=", 1) for x in p[5].split("|")) if p[5] != "_" else {}
            cur["toks"].append(dict(id=int(p[0]), form=p[1], upos=p[3], feats=feats, deprel=p[7]))
    if cur and cur["toks"]:
        sents.append(cur)
    return sents


def build(args):
    """Stratified sample: 50 targets per case class, max 3 per sentence, fixed seed."""
    rng = np.random.default_rng(SEED)
    elig = [s for s in parse_conllu(args.conllu) if 8 <= len(s["toks"]) <= 25]
    pool = {c: [] for c in CASES}
    for si, s in enumerate(elig):
        for t in s["toks"]:
            c = t["feats"].get("Case")
            if c in pool and t["upos"] in TARGET_POS and len(t["form"]) >= 2:
                pool[c].append((si, t["id"]))

    per_sent, targets = Counter(), []
    for c in CASES:
        got = 0
        for si, tid in (pool[c][i] for i in rng.permutation(len(pool[c]))):
            if got >= args.per_case:
                break
            if per_sent[si] >= 3:
                continue
            targets.append((si, tid, c)); per_sent[si] += 1; got += 1

    by_sent = {}
    for si, tid, _ in targets:
        by_sent.setdefault(si, []).append(tid)

    prompts, gold = [], {}
    for si, tids in by_sent.items():
        s = elig[si]
        toklist = "  ".join(f"{t['id']}:{t['form']}" for t in s["toks"])
        prompts.append(dict(sent_id=s["sent_id"], tids=sorted(tids),
                            prompt=f"Sentence (numbered tokens):\n{toklist}\n\n"
                                   f"Annotate these indices: {', '.join(map(str, sorted(tids)))}"))
        for tid in tids:
            t = next(x for x in s["toks"] if x["id"] == tid)
            gold[f"{s['sent_id']}|{tid}"] = dict(form=t["form"], upos=t["upos"],
                                                 case=t["feats"].get("Case"), deprel=t["deprel"])
    json.dump(prompts, open(args.out_prompts, "w"), ensure_ascii=False)
    json.dump(gold, open(args.out_gold, "w"), ensure_ascii=False)
    print(f"{len(prompts)} prompt sentences, {len(gold)} gold targets, "
          f"{dict(Counter(v['case'] for v in gold.values()))}")


def run(args, query):
    """query(prompt, system, model) -> str. Greedy decoding is the caller's responsibility."""
    prompts = json.load(open(args.prompts))
    out = {}
    for model in args.models:
        rows = []
        for p in prompts:
            txt = query(p["prompt"], SYSTEM, model) or ""
            rows.append({"sent_id": p["sent_id"], "tids": p["tids"], "raw": txt})
        out[model] = rows
        print(model, "empty returns:", sum(1 for r in rows if not r["raw"]))
    json.dump(out, open(args.out_raw, "w"), ensure_ascii=False)


def parse_pred(raw):
    pred = {}
    for line in raw.strip().split("\n"):
        m = re.match(r"\s*\**\s*(\d+)\s*\|\s*([A-Za-z]+)\s*\|\s*([A-Za-z]+)", line.strip())
        if m:
            pred[int(m.group(1))] = (m.group(2).upper(), m.group(3).capitalize())
    return pred


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    ph = k / n; d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    h = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return (round(100 * (c - h), 1), round(100 * (c + h), 1))


def score(args):
    raw = json.load(open(args.raw)); gold = json.load(open(args.gold))
    recs = []
    for model, rows in raw.items():
        for r in rows:
            pred = parse_pred(r["raw"])
            for tid in r["tids"]:
                g = gold[f"{r['sent_id']}|{tid}"]; p = pred.get(tid)
                recs.append(dict(model=model, sent_id=r["sent_id"], tid=tid, form=g["form"],
                                 gold_upos=g["upos"], gold_case=g["case"],
                                 pred_upos=p[0] if p else None, pred_case=p[1] if p else None,
                                 parsed=p is not None,
                                 upos_ok=bool(p and p[0] == g["upos"]),
                                 case_ok=bool(p and p[1] == g["case"])))
    E = pd.DataFrame(recs)
    E.to_csv(f"{args.out}/results_e1_morphosyntax_items.csv", index=False)

    rows = []
    for model, g in E.groupby("model"):
        n, ku, kc = len(g), int(g.upos_ok.sum()), int(g.case_ok.sum())
        rows.append(dict(model=model, n_targets=n, unparsed=int((~g.parsed).sum()),
                         pos_acc=round(100 * ku / n, 1), pos_ci=f"{wilson(ku, n)}",
                         case_acc=round(100 * kc / n, 1), case_ci=f"{wilson(kc, n)}",
                         both_ok=round(100 * (g.upos_ok & g.case_ok).mean(), 1)))
    pd.DataFrame(rows).sort_values("case_acc", ascending=False).to_csv(
        f"{args.out}/results_e1_model_summary.csv", index=False)

    E[E.parsed].groupby(["gold_case", "pred_case"]).size().unstack(fill_value=0).to_csv(
        f"{args.out}/results_e1_case_confusion.csv")

    piv = E.pivot_table(index=["sent_id", "tid"], columns="model", values="case_ok")
    mc = []
    for a_, b_ in itertools.combinations(piv.columns, 2):
        x = piv[[a_, b_]].dropna()
        b01 = int(((x[a_] == 1) & (x[b_] == 0)).sum()); b10 = int(((x[a_] == 0) & (x[b_] == 1)).sum())
        chi = (abs(b01 - b10) - 1) ** 2 / (b01 + b10) if (b01 + b10) else 0.0
        mc.append(dict(model_a=a_, model_b=b_, a_only=b01, b_only=b10,
                       chi2_cc=round(chi, 2), p=round(float(stats.chi2.sf(chi, 1)), 4)))
    pd.DataFrame(mc).to_csv(f"{args.out}/results_e1_mcnemar.csv", index=False)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("--conllu", required=True)
    b.add_argument("--out-prompts", required=True); b.add_argument("--out-gold", required=True)
    b.add_argument("--per-case", type=int, default=50)
    s = sub.add_parser("score"); s.add_argument("--raw", required=True)
    s.add_argument("--gold", required=True); s.add_argument("--out", default=".")
    a = ap.parse_args()
    (build if a.cmd == "build" else score)(a)
