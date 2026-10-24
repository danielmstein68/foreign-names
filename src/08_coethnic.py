"""Exploratory: co-ethnic voting test, as pre-specified in docs/coethnic_test.md.

Question: does a Hispanic / Black / Asian surname do better where more of the
local population shares that background? If so, a penalty among other voters
and a boost among co-ethnic voters could average out to "no effect", which
would explain why Garcia-type names showed no penalty on average.

Local races only. Place demographics are HKS's yearly city (7-digit place FIPS)
and county (5-digit county FIPS) files; school board districts have no
readable demographics and drop out.

Output: output/08_coethnic.md and output/08_coethnic.csv
Run:  .venv/bin/python src/08_coethnic.py
"""

import importlib

import numpy as np
import pandas as pd
import pyreadr

from common import OUTPUT, RAW, log_decision

step5 = importlib.import_module("05_regressions")
step6 = importlib.import_module("06_quadrants")

RESULTS = []


def place_demographics() -> pd.DataFrame:
    """One row per place (city or county) and year: population shares, 0-1."""
    rename = {"percent_white": "pl_white", "percent_black": "pl_black",
              "percent_hispanic": "pl_hisp", "percent_asian_american": "pl_asian"}
    co = list(pyreadr.read_r(RAW / "hks" / "counties_historical_demographics.rds").values())[0]
    ci = list(pyreadr.read_r(RAW / "hks" / "cities_historical_demographics.rds").values())[0]
    co = co.rename(columns={"county_fips": "fips", **rename})
    ci = ci.rename(columns={"place_fips": "fips", **rename})
    both = pd.concat([co, ci])[["fips", "year", *rename.values()]]
    both["year"] = both["year"].astype(int)
    return both


def cell(est, lo, hi, p):
    stars = "**" if p < 0.05 else ""
    return f"{stars}{est:+.2f}{stars} [{lo:+.2f}, {hi:+.2f}]"


def main() -> None:
    df = step5.load_main_sample()
    df = df[df["source"] == "local"].copy()
    demo = place_demographics()
    df["demo_year"] = df["year"].clip(upper=2020)
    df = df.merge(demo.rename(columns={"year": "demo_year"}), on=["fips", "demo_year"], how="inner")
    df["pl_nonwhite"] = 1 - df["pl_white"]
    log_decision("coethnic", f"Matched {len(df):,} local candidates to place demographics (city for city/mayor "
                 "races, county for county races; 2021 races use 2020 figures). School board races drop out: "
                 "HKS's school-district file could not be read (text-encoding error).",
                 "Follows docs/coethnic_test.md; school boards are about 4% of local races.")

    samples = {"Local nonpartisan": df[df["sample"] == "Local nonpartisan"],
               "Local partisan": df[df["sample"] == "Local partisan"], "All local": df}
    lines = ["# Co-ethnic voting test (exploratory)", "",
             "Pre-specified in `docs/coethnic_test.md` before any demographic data was loaded. Exploratory: added "
             "after the main results were seen. Vote share in percentage points; 95% CIs clustered by "
             "jurisdiction; bold means p < 0.05.", ""]

    # ---- Model 1: name share × same-group population share ----------------
    terms = ["hispanic", "black", "api", "foreign", "hispanic:pl_hisp", "black:pl_black", "api:pl_asian"]
    t1, effects = {}, {}
    for s, d in samples.items():
        ctrl = "incumbent + incumbent_missing" + (" + C(party2)" if s != "Local nonpartisan" else "")
        if s == "All local":
            ctrl = "incumbent + incumbent_missing + C(party2)"
        m = step5.fit(f"vs ~ {' + '.join(terms)} + {ctrl} | contest_id", d)
        tidy = m.tidy()
        t1[s] = [cell(*tidy.loc[t, ["Estimate", "2.5%", "97.5%", "Pr(>|t|)"]]) for t in terms]
        # Implied effect of a fully Hispanic/Black/Asian surname where that group is 0%, 25%, 50% of residents.
        # The combination is computed by hand: b_name + share × b_interaction.
        for g, inter in [("hispanic", "hispanic:pl_hisp"), ("black", "black:pl_black"), ("api", "api:pl_asian")]:
            names = list(m._coefnames)
            for share in (0.0, 0.25, 0.5):
                w = np.array([1.0 if n == g else share if n == inter else 0.0 for n in names])
                est = float(w @ m.coef().values)
                se = float(np.sqrt(w @ m._vcov @ w))
                tcrit = step5.stats.t.ppf(0.975, int(m._G[0]) - 1)
                p = 2 * step5.stats.t.sf(abs(est / se), int(m._G[0]) - 1)
                effects.setdefault(s, {})[f"{g} name where {g} = {share:.0%} of residents"] = \
                    cell(est, est - tcrit * se, est + tcrit * se, p)
                RESULTS.append(dict(model="implied effect", sample=s, group=g, place_share=share, estimate=est,
                                    ci_low=est - tcrit * se, ci_high=est + tcrit * se, p=p, n=m._N))
    t1_df = pd.DataFrame(t1, index=terms)
    t1_df.loc["N candidates"] = [f"{len(d):,}" for d in samples.values()]
    lines += ["## Model 1: surname share × same-group share of residents", "",
              "Co-ethnic voting predicts **positive** interactions (the name does better where more residents "
              "share it) and **negative** main effects (the name's effect where none do).", "",
              t1_df.to_markdown(), "",
              "### What that implies: effect of a fully Hispanic / Black / Asian surname vs a white surname, "
              "by how much of the place shares that background", "",
              pd.DataFrame(effects).to_markdown(), ""]

    # ---- Model 2: the four groups, by how diverse the place is -------------
    dq = step6.add_quadrants(df, "foreign")
    races = dq.drop_duplicates("contest_id")
    cuts = races["pl_nonwhite"].quantile([1 / 3, 2 / 3]).values
    dq["tier"] = pd.cut(dq["pl_nonwhite"], [-0.01, cuts[0], cuts[1], 1.01],
                        labels=["least diverse third", "middle third", "most diverse third"])
    t2 = {}
    for tier in dq["tier"].cat.categories:
        d = dq[dq["tier"] == tier]
        m = step5.fit("vs ~ q1 + q2 + q3 + incumbent + incumbent_missing + C(party2) | contest_id", d)
        tidy = m.tidy()
        t2[f"{tier} (non-white {d['pl_nonwhite'].min():.0%}–{d['pl_nonwhite'].max():.0%})"] = \
            [cell(*tidy.loc[q, ["Estimate", "2.5%", "97.5%", "Pr(>|t|)"]]) for q in ["q1", "q2", "q3"]] + \
            [f"{m._N:,} / {d['contest_id'].nunique():,}", f"{int(d['q3'].sum()):,}"]
    t2_df = pd.DataFrame(t2, index=step6.GROUPS + ["N candidates / races", "non-white & foreign candidates"])
    lines += ["## Model 2: the four groups vs white & not foreign, by how diverse the place is", "",
              "Places split into thirds by non-white share of residents (all local races). Co-ethnic voting "
              "predicts the **non-white & foreign** row to go from negative (least diverse) toward zero or "
              "positive (most diverse).", "", t2_df.to_markdown(), ""]

    pd.DataFrame(RESULTS).to_csv(OUTPUT / "08_coethnic.csv", index=False)
    (OUTPUT / "08_coethnic.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
