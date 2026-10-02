#!/usr/bin/env python3
"""Probe 2: reference generation, verified against Crossref and OpenAlex.

  python 03_probe_citations.py verify --raw ../../06_probes/probe_citation_raw.json \
         --out ../../05_results [--openalex-key $OPENALEX_API_KEY] [--email you@inst.edu]

A reference is classified as:
  verified_as_supplied        DOI resolves in Crossref AND the returned title matches (>= 0.60)
  real_work_wrong_identifier  no valid Crossref match, but OpenAlex holds a title match (>= 0.60)
  no_trace_in_either_index    neither index returns a matching record
"""
import argparse, difflib, json, re, time, urllib.parse, urllib.request
import numpy as np, pandas as pd

THRESHOLD = 0.60
FIELD_WORDS = {"عنوان", "العنوان", "مجلة", "المجلة", "المؤلف", "مؤلف", "سنة", "السنة",
               "doi", "title", "author", "journal", "year"}
SYSTEM_AR = ("أنت مساعد بحثي. اذكر مراجع علمية حقيقية ومحكَّمة فقط. "
             "لكل مرجع اكتب سطرًا واحدًا بهذا الشكل بالضبط، مفصولًا بعلامة |:\n"
             "المؤلف | العنوان | المجلة | السنة | DOI\n"
             "يجب أن يكون لكل مرجع معرِّف DOI حقيقي. إذا لم تكن متأكدًا من وجود مرجع، فلا تذكره. "
             "لا تكتب أي نص آخر ولا مقدمات ولا شرحًا.")


def parse_refs(text):
    """Strict parser. Rejects field-name header rows and explanatory prose, which a naive
    split on '|' otherwise turns into phantom references."""
    out = []
    for line in text.split("\n"):
        parts = [x.strip() for x in line.split("|")]
        if len(parts) < 5:
            continue
        author, title, venue, year, doi = parts[:5]
        if title.lower() in FIELD_WORDS or venue.lower() in FIELD_WORDS:
            continue
        if not re.search(r"\b(1[89]|20)\d{2}\b", year):
            continue
        if len(title) < 10 or len(author) > 120:
            continue
        out.append(dict(author=author, title=title, venue=venue, year=year, doi=doi))
    return out


def norm_doi(d):
    d = (str(d).strip().strip(".,;)")
         .replace("https://doi.org/", "").replace("http://dx.doi.org/", "")
         .replace("doi:", "").strip())
    return d if re.match(r"^10\.\d{4,9}/\S+$", d) else None


def norm_title(s):
    return re.sub(r"[^a-z0-9\u0600-\u06FF ]", " ", str(s).lower()).strip()


def sim(a, b):
    return difflib.SequenceMatcher(None, norm_title(a), norm_title(b)).ratio()


def get_json(url, timeout=25):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf8"))
    except Exception as e:
        return {"__err": type(e).__name__}


def verify(args):
    refs = []
    raw = json.load(open(args.raw))
    for model, rows in raw.items():
        for r in rows:
            for ref in parse_refs(r["raw"]):
                refs.append(dict(model=model, topic=r["topic"], **ref))
    R = pd.DataFrame(refs)
    if R.empty:
        raise SystemExit("no parseable references found")

    recs = []
    for _, r in R.iterrows():
        d = norm_doi(r.doi)
        cr_status, cr_sim, cr_title = "malformed_or_absent_doi", np.nan, None
        if d:
            url = f"https://api.crossref.org/works/{urllib.parse.quote(d)}"
            if args.email:
                url += "?mailto=" + urllib.parse.quote(args.email)
            j = get_json(url)
            if "message" in j:
                cr_title = (j["message"].get("title") or [""])[0]
                cr_sim = round(sim(r.title, cr_title), 3)
                cr_status = "verified" if cr_sim >= THRESHOLD else "resolves_to_different_work"
            else:
                cr_status = "doi_does_not_resolve"

        oa_sim, oa_route = np.nan, None
        if args.openalex_key:
            if d:
                j = get_json(f"https://api.openalex.org/works/doi:{urllib.parse.quote(d)}"
                             f"?api_key={args.openalex_key}")
                if "__err" not in j and j.get("id"):
                    oa_sim, oa_route = round(sim(r.title, j.get("title") or ""), 3), "doi"
            if oa_route is None:
                j = get_json("https://api.openalex.org/works?per-page=3&search="
                             + urllib.parse.quote(str(r.title)[:200])
                             + f"&api_key={args.openalex_key}")
                best = max((sim(r.title, it.get("title") or "") for it in (j.get("results") or [])),
                           default=0.0)
                oa_sim, oa_route = round(best, 3), "title"

        oa_ok = bool(oa_sim == oa_sim and oa_sim >= THRESHOLD)
        cls = ("verified_as_supplied" if cr_status == "verified"
               else "real_work_wrong_identifier" if oa_ok
               else "no_trace_in_either_index")
        recs.append(dict(status=cr_status, sim=cr_sim, cr_title=cr_title,
                         oa_sim=oa_sim, oa_route=oa_route, oa_verified=oa_ok,
                         verification_class=cls))
        time.sleep(args.sleep)

    V = pd.concat([R.reset_index(drop=True), pd.DataFrame(recs)], axis=1)
    V.to_csv(f"{args.out}/results_e2_citation_items.csv", index=False)

    # abstention behaviour must be reported before any error rate
    rt = []
    for model, rows in raw.items():
        for r in rows:
            n = len(parse_refs(r["raw"]))
            declined = bool(re.search(r"لا أستطيع|لا يمكنني|لا أملك|لست متأكد|أعتذر|cannot|unable",
                                      r["raw"])) and n == 0
            rt.append(dict(model=model, n_refs=n,
                           response_type="refers" if n else ("abstains" if declined else "other/empty")))
    RT = pd.DataFrame(rt)

    tab = pd.crosstab(V.model, V.verification_class)
    for c in ("verified_as_supplied", "real_work_wrong_identifier", "no_trace_in_either_index"):
        if c not in tab:
            tab[c] = 0
    tab = tab[["verified_as_supplied", "real_work_wrong_identifier", "no_trace_in_either_index"]]
    tab["refs_supplied"] = tab.sum(axis=1)
    tab["verified_pct"] = (100 * tab.verified_as_supplied / tab.refs_supplied).round(1)
    tab["no_trace_pct"] = (100 * tab.no_trace_in_either_index / tab.refs_supplied).round(1)
    for m in RT.model.unique():
        if m not in tab.index:
            tab.loc[m] = [0, 0, 0, 0, np.nan, np.nan]
    tab["topics_answered"] = [int(((RT.model == m) & (RT.n_refs > 0)).sum()) for m in tab.index]
    tab["topics_abstained"] = [int(((RT.model == m) & (RT.response_type == "abstains")).sum()) for m in tab.index]
    tab["topics_other_or_empty"] = [int(((RT.model == m) & (RT.response_type == "other/empty")).sum()) for m in tab.index]
    tab["topics_total"] = tab.topics_answered + tab.topics_abstained + tab.topics_other_or_empty
    tab.reset_index().to_csv(f"{args.out}/results_e2_model_summary.csv", index=False)
    print(tab.to_string())
    n = len(V); k = int((V.verification_class == "verified_as_supplied").sum())
    nt = int((V.verification_class == "no_trace_in_either_index").sum())
    print(f"\npooled n={n}: verified {k} ({100*k/n:.1f}%), no trace {nt} ({100*nt/n:.1f}%)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--raw", required=True); v.add_argument("--out", default=".")
    v.add_argument("--openalex-key", default=None); v.add_argument("--email", default=None)
    v.add_argument("--sleep", type=float, default=0.05)
    verify(ap.parse_args())
