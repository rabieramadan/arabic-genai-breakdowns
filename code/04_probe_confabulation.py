#!/usr/bin/env python3
"""Probe 3: confabulation on bibliographic entities verified not to exist.

  python 04_probe_confabulation.py check-absent --spec ../../06_probes/probe_attribution_spec.json \
         --out ../../06_probes/probe_e3_items.csv [--openalex-key $OPENALEX_API_KEY]
  python 04_probe_confabulation.py score --raw ../../06_probes/probe_e3_raw.json \
         --items ../../06_probes/probe_e3_items.csv --out ../../05_results

Absence rule: a constructed title is treated as absent when no record retrieved from either
index contains its distinctive subject phrase. A raw title-similarity threshold is NOT used,
because shared frame wording alone pushes Arabic titles above 0.60 against unrelated works.

Scoring uses two schemes and reports both, because whether title-based speculation following a
disclaimer counts as supplying content is a definitional choice, not a coding error:
  strict      an assertion of content with no disclaimer anywhere in the reply
  wider       any reply that supplies substantive content, disclaimer or not
"""
import argparse, difflib, json, re, time, urllib.parse, urllib.request
import pandas as pd

DISCLAIM = (r"لم أتمكن|لا أستطيع|لا يمكنني|لا أملك|لا تتوفر|لم أجد|لا أجد|غير متوفر|"
            r"لا يبدو|لست متأكد|ليس لديّ|لم أطّلع")
ASSERT = (r"تهدف الدراسة|تُظهر النتائج|تظهر النتائج|توصل|يخلص|خلصت|تخلص|يرى الباحث|"
          r"تناقش المقالة|تعرض المقالة|تبيّن الدراسة|أظهرت|تؤكد الدراسة|تقترح الدراسة|"
          r"تنطلق المقالة|تعتمد المقالة")


def norm(s):
    return re.sub(r"[^a-z0-9\u0600-\u06FF ]", " ", str(s).lower()).strip()


def get_json(url):
    try:
        with urllib.request.urlopen(url, timeout=25) as r:
            return json.loads(r.read().decode("utf8"))
    except Exception as e:
        return {"__err": type(e).__name__}


def check_absent(args):
    spec = json.load(open(args.spec))
    items = []
    for i, subj in enumerate(spec["subjects_ar"]):
        for frame in spec["title_frames_ar"]:
            items.append(dict(title=frame.format(X=subj), subject=subj))
    items = items[:args.limit]
    rows = []
    for i, it in enumerate(items):
        retrieved = []
        j = get_json("https://api.crossref.org/works?rows=3&query.bibliographic="
                     + urllib.parse.quote(it["title"]))
        retrieved += [(x.get("title") or [""])[0] for x in j.get("message", {}).get("items", [])]
        if args.openalex_key:
            j = get_json("https://api.openalex.org/works?per-page=3&search="
                         + urllib.parse.quote(it["title"]) + f"&api_key={args.openalex_key}")
            retrieved += [x.get("title") or "" for x in (j.get("results") or [])]
        best = max((difflib.SequenceMatcher(None, norm(it["title"]), norm(t)).ratio()
                    for t in retrieved), default=0.0)
        contains_subject = any(it["subject"] in (t or "") for t in retrieved)
        rows.append(dict(item_id=f"F{i+1:02d}", title=it["title"], subject=it["subject"],
                         venue=spec["journal_frames_ar"][i % len(spec["journal_frames_ar"])],
                         year=spec["years"][i % len(spec["years"])],
                         best_title_sim=round(best, 3),
                         retrieved_contains_subject=contains_subject,
                         confirmed_absent=not contains_subject))
        time.sleep(args.sleep)
    df = pd.DataFrame(rows)
    df.to_csv(args.out, index=False)
    print(f"{int(df.confirmed_absent.sum())} of {len(df)} confirmed absent; "
          f"max title similarity {df.best_title_sim.max()}")


def score(args):
    raw = json.load(open(args.raw))
    items = pd.read_csv(args.items)
    keep = items[items.confirmed_absent].item_id.tolist()
    recs = []
    for model, replies in raw.items():
        for item_id, reply in zip(keep, replies):
            reply = reply or ""
            disc, asrt = bool(re.search(DISCLAIM, reply)), bool(re.search(ASSERT, reply))
            recs.append(dict(model=model, item=item_id, reply=reply,
                             has_disclaimer=disc, has_assertion=asrt,
                             strict="confabulated" if (asrt and not disc) else
                                    ("hedged" if (asrt and disc) else "correct_disclaim")))
    E = pd.DataFrame(recs)
    E.to_csv(f"{args.out}/results_e3_confabulation_items.csv", index=False)
    print(pd.crosstab(E.model, E.strict).to_string())
    print("\nThe wider scheme requires an independent coder judging whether each reply supplies "
          "substantive content; see results_e3_independent_coding.csv for the labels used in the paper.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check-absent")
    c.add_argument("--spec", required=True); c.add_argument("--out", required=True)
    c.add_argument("--openalex-key", default=None); c.add_argument("--limit", type=int, default=40)
    c.add_argument("--sleep", type=float, default=0.05)
    s = sub.add_parser("score")
    s.add_argument("--raw", required=True); s.add_argument("--items", required=True)
    s.add_argument("--out", default=".")
    a = ap.parse_args()
    (check_absent if a.cmd == "check-absent" else score)(a)
