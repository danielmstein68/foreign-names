"""Exploratory: ancestry-bloc test, as pre-specified in docs/ancestry_bloc_test.md.

Daniel's hypothesis: white ethnic names (Hansen, Wagner) pay an "unfamiliar
name" penalty that, unlike for non-white groups, no voting bloc offsets.
Prediction: a name does better where more residents report the ancestry
that matches it.

Ancestry: ACS 5-year 2006-2010, table B04006 (people reporting each ancestry),
divided by total population, for counties (county races) and places (city
races). Local races only, with the co-ethnic terms from step 8 included.

Output: output/09_ancestry_bloc.md
Run:  .venv/bin/python src/09_ancestry_bloc.py
"""

import importlib

import pandas as pd

from common import OUTPUT, RAW, log_decision

step5 = importlib.import_module("05_regressions")
step6 = importlib.import_module("06_quadrants")
step8 = importlib.import_module("08_coethnic")

# ethnicolr group -> ACS B04006 variable numbers (see docs/ancestry_bloc_test.md).
ANCESTRY = {
    "british": [23, 36, 49, 66, 67, 93, 28],
    "germanic": [42, 19, 34, 90, 54, 60, 43, 4],
    "nordic": [59, 89, 33, 39, 47, 65],
    "french": [40, 41, 25, 21],
    "italian": [51, 56],
    "easteuropean": [61, 31, 32, 70, 46, 64, 92, 53, 52, 37, 29, 68, 71, 69, 63, 24, 44, 55, 3, 27, 35, 107, 72],
}
WHITE_ETHNIC = ["germanic", "nordic", "french", "italian", "easteuropean"]
TOP_LABEL = {"GreaterEuropean,WestEuropean,Germanic": "germanic", "GreaterEuropean,WestEuropean,Nordic": "nordic",
             "GreaterEuropean,WestEuropean,French": "french", "GreaterEuropean,WestEuropean,Italian": "italian",
             "GreaterEuropean,EastEuropean": "easteuropean"}


def ancestry_shares() -> pd.DataFrame:
    """Share of residents reporting each ancestry group, by county and by city."""
    out = []
    for geo, idcols in [("county", ["state", "county"]), ("place", ["state", "place"])]:
        a = pd.read_csv(RAW / "acs" / f"ancestry_{geo}.csv", dtype={c: str for c in idcols})
        fips = a[idcols[0]].str.zfill(2) + a[idcols[1]].str.zfill(3 if geo == "county" else 5)
        pop = a["B01003_001E"].where(a["B01003_001E"] > 0)
        shares = pd.DataFrame({f"anc_{g}": a[[f"B04006_{i:03d}E" for i in nums]].sum(axis=1) / pop
                               for g, nums in ANCESTRY.items()})
        out.append(shares.assign(fips=fips.values))
    out = pd.concat(out)
    anc_cols = [c for c in out.columns if c.startswith("anc_")]
    out[anc_cols] = out[anc_cols].clip(upper=1)  # multiple ancestries can push a group just above 100%
    return out


def cell(r):
    stars = "**" if r[3] < 0.05 else ""
    return f"{stars}{r[0]:+.2f}{stars} [{r[1]:+.2f}, {r[2]:+.2f}]"


def main() -> None:
    df = step5.load_main_sample()
    df = df[df["source"] == "local"].copy()
    df["demo_year"] = df["year"].clip(upper=2020)
    df = df.merge(step8.place_demographics().rename(columns={"year": "demo_year"}), on=["fips", "demo_year"])
    df = df.merge(ancestry_shares(), on="fips", how="inner")
    log_decision("ancestry", f"Matched {len(df):,} local candidates to ACS 2006-2010 ancestry shares (one snapshot "
                 "for all years).", "Follows docs/ancestry_bloc_test.md.")

    p = {g: df[f"p_{g}"] for g in ["british", "germanic", "nordic", "french", "italian", "easteuropean"]}
    df["match_brit"] = p["british"] * df["anc_british"]
    df["match_nonbrit"] = sum(p[g] * df[f"anc_{g}"] for g in WHITE_ETHNIC)
    df["match"] = df["match_brit"] + df["match_nonbrit"]

    base = ("hispanic + black + api + foreign + hispanic:pl_hisp + black:pl_black + api:pl_asian")
    samples = {"Local nonpartisan": df[df["sample"] == "Local nonpartisan"],
               "Local partisan": df[df["sample"] == "Local partisan"], "All local": df}
    rows1, rows2 = {}, {}
    for s, d in samples.items():
        ctrl = "incumbent + incumbent_missing" + ("" if s == "Local nonpartisan" else " + C(party2)")
        t = step5.fit(f"vs ~ {base} + match + {ctrl} | contest_id", d).tidy()
        rows1[s] = [cell(t.loc["match", ["Estimate", "2.5%", "97.5%", "Pr(>|t|)"]].values), f"{len(d):,}"]
        t = step5.fit(f"vs ~ {base} + match_nonbrit + match_brit + {ctrl} | contest_id", d).tidy()
        rows2[s] = [cell(t.loc[v, ["Estimate", "2.5%", "97.5%", "Pr(>|t|)"]].values)
                    for v in ["match_nonbrit", "match_brit"]] + [f"{len(d):,}"]

    # Model 3: white & foreign candidates split by the local share of their own ancestry group.
    dq = step6.add_quadrants(df, "foreign")
    dq["own_group"] = dq["eth_top"].map(TOP_LABEL)
    dq["own_anc"] = float("nan")
    for g in WHITE_ETHNIC:
        dq.loc[dq["own_group"] == g, "own_anc"] = dq[f"anc_{g}"]
    wf = dq["q1"].eq(1) & dq["own_group"].notna()
    cuts = dq.loc[wf, "own_anc"].quantile([1 / 3, 2 / 3]).values
    tier = pd.cut(dq["own_anc"], [-0.01, cuts[0], cuts[1], 1.01], labels=["low", "mid", "high"])
    for t_ in ["low", "mid", "high"]:
        dq[f"wf_{t_}"] = (wf & tier.eq(t_)).astype(int)
    # White & foreign candidates whose top group isn't one of the five (e.g. Jewish) get their own dummy.
    dq["wf_other"] = (dq["q1"].eq(1) & dq["own_group"].isna()).astype(int)
    m = step5.fit("vs ~ wf_low + wf_mid + wf_high + wf_other + q2 + q3 + incumbent + incumbent_missing"
                  " + C(party2) | contest_id", dq)
    t = m.tidy()
    rows3 = {f"{lab} (own ancestry {lo:.0%}–{hi:.0%} of residents)": [
        cell(t.loc[f"wf_{lab}", ["Estimate", "2.5%", "97.5%", "Pr(>|t|)"]].values),
        f"{int(dq[f'wf_{lab}'].sum()):,}"]
        for lab, lo, hi in [("low", 0, cuts[0]), ("mid", cuts[0], cuts[1]), ("high", cuts[1], 1)]}

    # Model 4 (added after seeing Model 3): Model 3's thirds mix up origin groups (the high third is mostly
    # German names, the low third mostly French/Italian/Nordic), so compare each group only with itself:
    # a separate white & foreign dummy per origin group, plus one slope on the share of residents sharing it.
    comp = pd.crosstab(dq.loc[wf, "own_group"], tier[wf])
    group_terms = []
    for g in WHITE_ETHNIC:
        dq[f"wf_{g}"] = (wf & dq["own_group"].eq(g)).astype(int)
        dq[f"wf_{g}_x_anc"] = dq[f"wf_{g}"] * dq["own_anc"].fillna(0)
        group_terms.append(f"wf_{g}")
    dq["wf_any_x_anc"] = sum(dq[f"wf_{g}_x_anc"] for g in WHITE_ETHNIC)
    ctrl4 = "q2 + q3 + wf_other + incumbent + incumbent_missing + C(party2) | contest_id"
    t = step5.fit(f"vs ~ {' + '.join(group_terms)} + wf_any_x_anc + {ctrl4}", dq).tidy()
    rows4 = {v: cell(t.loc[v, ["Estimate", "2.5%", "97.5%", "Pr(>|t|)"]].values)
             for v in group_terms + ["wf_any_x_anc"]}
    t = step5.fit(f"vs ~ {' + '.join(group_terms)} + {' + '.join(g + '_x_anc' for g in group_terms)} + {ctrl4}",
                  dq).tidy()
    rows4b = {g: cell(t.loc[f"{g}_x_anc", ["Estimate", "2.5%", "97.5%", "Pr(>|t|)"]].values) for g in group_terms}
    log_decision("ancestry", "Added Model 4 after seeing Model 3: within-origin-group comparison (separate "
                 "white & foreign dummy per group + slope on own-ancestry share).", "Model 3's thirds were "
                 "dominated by different origin groups (high = mostly German), so it could not separate a bloc "
                 "effect from group differences.")

    lines = ["# Ancestry-bloc test (exploratory)", "",
             "Pre-specified in `docs/ancestry_bloc_test.md` before any ancestry data was loaded. Exploratory: added "
             "after the main results were seen. Vote share in percentage points; 95% CIs clustered by "
             "jurisdiction; bold means p < 0.05. All models include the co-ethnic terms from step 8.", "",
             "## Model 1: does a name do better where more residents share its origin?", "",
             "`match` is roughly the share of residents whose ancestry matches the name's origin (0-1). The bloc "
             "explanation predicts a **positive** coefficient. A coefficient of +10 means a name gains 1 point for "
             "every 10 percentage points more residents sharing its origin.", "",
             pd.DataFrame(rows1, index=["match", "N candidates"]).to_markdown(), "",
             "## Model 2: white ethnic origins vs British origin", "",
             "Prediction: **match_nonbrit positive**, meaning German, Nordic, French, Italian and Eastern European "
             "names do better where their ancestry is common.", "",
             pd.DataFrame(rows2, index=["match_nonbrit", "match_brit", "N candidates"]).to_markdown(), "",
             "## Model 3: white & foreign candidates vs white & not foreign, by local share of their own ancestry",
             "", "All local races. Prediction: the penalty shrinks or disappears in the high group.", "",
             pd.DataFrame(rows3, index=["effect vs white & not foreign", "candidates"]).T.to_markdown(), "",
             "**Caution:** these thirds mix up origin groups (candidates per group and third below), so Model 3 "
             "alone cannot separate a bloc effect from differences between groups. See Model 4.", "",
             comp.to_markdown(), "",
             "## Model 4: within each origin group (added after seeing Model 3)", "",
             "Each white & foreign origin group gets its own baseline (its effect vs white & not foreign where "
             "nobody shares its ancestry), and the slope is estimated from how the *same* group does in places "
             "where more residents share its ancestry. Prediction: a **positive** slope.", "",
             "One slope for all five groups:", "",
             pd.Series(rows4, name="estimate").to_frame().to_markdown(), "",
             "A separate slope per group:", "",
             pd.Series(rows4b, name="slope on own-ancestry share").to_frame().to_markdown(), ""]
    (OUTPUT / "09_ancestry_bloc.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
