"""How do the four whiteness × foreignness groups perform?

Uses the same 2 × 2 groups as the checkpoint: top tercile on non-white and/or
foreign vs the rest, with cut-offs computed on the pooled main sample. Each group is
compared with "white & not foreign" (Smith, Miller...) using the same
within-race model as step 5 (contest fixed effects, clustered by jurisdiction),
plus the House swing design.

Also shows raw averages per group, which are NOT a fair comparison (groups run
in different kinds of races) and are only there for intuition.

Output: output/06_quadrants.md
Run:  .venv/bin/python src/06_quadrants.py
"""

import importlib

import numpy as np
import pandas as pd

from common import OUTPUT, PROCESSED

step5 = importlib.import_module("05_regressions")

GROUPS = ["white & foreign", "non-white & not foreign", "non-white & foreign"]
BASE = "white & not foreign"


def add_quadrants(df: pd.DataFrame, foreign_col: str) -> pd.DataFrame:
    """Top-tercile cut-offs computed exactly as in the checkpoint
    (main sample, fully scored, before requiring 2 scored candidates per race)."""
    ref = pd.read_parquet(PROCESSED / "candidates_scored.parquet")
    ref = ref[~ref["uncontested"] & ~ref["multiseat"] & ref["fully_scored"]]
    nw_hi = df["nonwhite"] > ref["nonwhite"].quantile(2 / 3)
    if set(df[foreign_col].dropna().unique()) <= {0, 1}:
        fo_hi = df[foreign_col] == 1  # already a yes/no score
    else:
        fo_hi = df[foreign_col] > ref[foreign_col].quantile(2 / 3)
    q = np.select([~nw_hi & ~fo_hi, ~nw_hi & fo_hi, nw_hi & ~fo_hi], [BASE, GROUPS[0], GROUPS[1]], GROUPS[2])
    out = df.assign(quadrant=q)
    for i, g in enumerate(GROUPS):
        out[f"q{i + 1}"] = (out["quadrant"] == g).astype(int)
    return out


def row(model, term):
    t = model.tidy().loc[term]
    stars = "**" if t["Pr(>|t|)"] < 0.05 else ""
    return f"{stars}{t['Estimate']:+.2f}{stars} [{t['2.5%']:+.2f}, {t['97.5%']:+.2f}]"


def main() -> None:
    base = step5.load_main_sample()
    lines = ["# Four groups: whiteness × foreignness", "",
             "Each cell is the difference in **vote share (percentage points)** compared with candidates who are "
             "**white & not foreign** (Smith, Miller) in the same race, with a 95% CI clustered by jurisdiction. "
             "Bold means p < 0.05.",
             "Groups: top tercile vs the rest on each score, same cut-offs as the checkpoint. Controls are as in "
             "step 5 (incumbency, plus party in partisan races).", ""]

    for rule, col, label in [("main", "foreign", "Main foreign rule (German/French/Nordic count as foreign)"),
                             ("alt", "foreign_top_alt", "Sensitivity rule (German/French/Nordic count as not foreign); "
                              "foreign = most likely origin is outside British/German/French/Nordic. Top-tercile "
                              "cut-offs don't work for this rule: they put Johnson, Brown and Miller in the foreign "
                              "groups")]:
        df = add_quadrants(base, col)
        table, ns = {}, {}
        samples = ["Local nonpartisan", "Local partisan", "House", "Senate"]
        for s in samples + ["Pooled"]:
            d = df if s == "Pooled" else df[df["sample"] == s]
            ctrl = ("incumbent + incumbent_missing + C(party2):C(source)" if s == "Pooled"
                    else step5.controls_for(s))
            m = step5.fit(f"vs ~ q1 + q2 + q3 + {ctrl} | contest_id", d)
            table[s] = [row(m, f"q{i + 1}") for i in range(3)]
            ns[s] = f"{m._N:,} / {d['contest_id'].nunique():,}"

        # House swing: Democratic two-party share on the Democrat's group minus the Republican's group.
        fed = df[(df["sample"] == "House") & df["party2"].isin(["DEM", "REP"])]
        ok = fed.groupby("contest_id")["party2"].transform(lambda p: (p == "DEM").sum() == 1 and (p == "REP").sum() == 1)
        fed = fed[ok]
        wide = fed.pivot_table(index=["contest_id", "year", "jurisdiction_id"], columns="party2",
                               values=["q1", "q2", "q3", "incumbent", "votes"]).reset_index()
        wide.columns = ["_".join(c).strip("_") for c in wide.columns]
        wide["dem2p"] = 100 * wide["votes_DEM"] / (wide["votes_DEM"] + wide["votes_REP"])
        for i in (1, 2, 3):
            wide[f"d{i}"] = wide[f"q{i}_DEM"] - wide[f"q{i}_REP"]
        cycle = (wide["year"] - 2).floordiv(10).astype(str)  # 1982-1990 -> 198, etc.
        wide["district_cycle"] = wide["jurisdiction_id"] + "_" + cycle
        m = step5.fit("dem2p ~ d1 + d2 + d3 + incumbent_DEM + incumbent_REP | district_cycle + year", wide)
        table["House swing"] = [row(m, f"d{i}") for i in (1, 2, 3)]
        ns["House swing"] = f"{m._N:,} district-elections"

        t = pd.DataFrame(table, index=GROUPS)
        t.loc["N (candidates / races)"] = pd.Series(ns)
        counts = df.groupby(["sample", "quadrant"]).size().unstack()[[BASE] + GROUPS]
        raw = df.groupby("quadrant").agg(avg_vote_share=("vs", "mean"), win_rate=("winner", "mean"),
                                         candidates=("vs", "size")).loc[[BASE] + GROUPS]
        examples = {g: ", ".join(df.loc[df["quadrant"] == g, "surname"].value_counts().head(8).index)
                    for g in [BASE] + GROUPS}
        lines += [f"## {label}", "", "### Within-race comparison (the fair one)", "", t.to_markdown(), "",
                  "### Candidates per group", "", counts.to_markdown(), "",
                  "### Raw averages (NOT a fair comparison; different groups run in different races)", "",
                  raw.round(3).to_markdown(), "",
                  "### Most common surnames per group", ""]
        lines += [f"- **{g}:** {e}" for g, e in examples.items()] + [""]

    (OUTPUT / "06_quadrants.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
