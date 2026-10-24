"""Step 6: robustness checks (trimmed list, agreed with Daniel).

Each check re-runs the main within-race model from step 5 with ONE thing
changed, and reports the three headline quantities:
  b2         foreign but white-coded (H2: ~0?)
  b1+b3      non-white penalty when the name is foreign (H1)
  b1+b2+b3   non-white & foreign vs white & Anglo

Checks:
  0. Main model (step 5), for reference
  1. Standard errors clustered by contest instead of jurisdiction (spec)
  2. 0/1 foreign score (most likely origin is not British) instead of the
     continuous probability: less sensitive to the model being unsure
  3. Open seats only (no incumbent in the race): incumbents differ from
     challengers in many ways besides their names
  4. Multi-seat local races, excluded from the main model (spec): outcome is
     seat-adjusted vote share, 100 × votes × seats / all votes in the race
     (100 = exactly the pace needed for a seat)

Output: output/07_robustness.md and output/07_robustness.csv
Run:  .venv/bin/python src/07_robustness.py
"""

import importlib

import numpy as np
import pandas as pd

from common import OUTPUT, PROCESSED, log_decision

step5 = importlib.import_module("05_regressions")

QUANTITIES = [("b2 foreign (H2)", ["foreign"]),
              ("b1+b3 (H1)", ["nonwhite", "nonwhite:foreign"]),
              ("b1+b2+b3 (combined)", ["nonwhite", "foreign", "nonwhite:foreign"])]
SAMPLES = ["Local nonpartisan", "Local partisan", "House", "Senate", "Pooled"]
ROWS = []


def run(check, sample, d, outcome="vs", cluster="jurisdiction_id", foreign="foreign"):
    """Fit the step-5 model on d with one change and store the headline quantities."""
    d = d.assign(foreign=d[foreign])
    ctrl = ("incumbent + incumbent_missing + C(party2):C(source)" if sample == "Pooled"
            else step5.controls_for(sample))
    m = step5.fit(f"{outcome} ~ {step5.NAME_TERMS} + {ctrl} | contest_id", d, cluster=cluster)
    for name, terms in QUANTITIES:
        est, lo, hi, p = step5.lincom(m, terms)
        ROWS.append(dict(check=check, sample=sample, quantity=name, estimate=est, ci_low=lo, ci_high=hi, p=p,
                         n_obs=m._N, n_contests=d["contest_id"].nunique()))


def by_sample(df, check, **kw):
    for s in SAMPLES:
        d = df if s == "Pooled" else df[df["sample"] == s]
        if d["contest_id"].nunique() >= 30:
            run(check, s, d, **kw)


def multiseat_sample() -> pd.DataFrame:
    """Contested multi-seat local races, prepared like the main sample."""
    df = pd.read_parquet(PROCESSED / "candidates_scored.parquet")
    df = df[df["multiseat"] & ~df["uncontested"] & df["fully_scored"] & (df["source"] == "local")].copy()
    df = df[df.groupby("contest_id")["contest_id"].transform("size") >= 2]
    df["sample"] = np.where(df["nonpartisan"], "Local nonpartisan", "Local partisan")
    df["seat_share"] = 100 * df["votes"] * df["seats"] / df["contest_votes"]
    df["incumbent_missing"] = df["incumbent"].isna().astype(int)
    df["incumbent"] = df["incumbent"].fillna(0)
    df["party2"] = np.where(df["nonpartisan"], "NONE", df["pid_est"].map({"D": "DEM", "R": "REP"}).fillna("UNKNOWN"))
    return df


def main() -> None:
    df = step5.load_main_sample()

    by_sample(df, "0. Main model (step 5)")
    by_sample(df, "1. SEs clustered by contest", cluster="contest_id")
    by_sample(df, "2. 0/1 foreign score", foreign="foreign_top")
    open_seat = df.groupby("contest_id")["incumbent"].transform("sum") == 0
    by_sample(df[open_seat], "3. Open seats only")
    log_decision("robustness", "Open-seat check: contests where no candidate is flagged as incumbent. For local "
                 "races, missing incumbency counts as not incumbent here.", "Simple rule; incumbency is "
                 "missing for 18% of local candidates.")

    ms = multiseat_sample()
    for s in ["Local nonpartisan", "Local partisan"]:
        run("4. Multi-seat local races (seat-adjusted share)", s, ms[ms["sample"] == s], outcome="seat_share")
    log_decision("robustness", "Multi-seat races: outcome = 100 × votes × seats / total votes in the race, with the "
                 "same within-race model.", "Plain vote share is not comparable across races with different "
                 "numbers of seats. 100 means exactly the pace needed to win a seat.")

    res = pd.DataFrame(ROWS)
    res.to_csv(OUTPUT / "07_robustness.csv", index=False)

    def cell(r):
        stars = "**" if r["p"] < 0.05 else ""
        return f"{stars}{r['estimate']:+.2f}{stars} [{r['ci_low']:+.2f}, {r['ci_high']:+.2f}]"
    res["cell"] = res.apply(cell, axis=1)
    lines = ["# Robustness checks", "",
             "Each row re-runs the step-5 within-race model with one change. Estimates are in percentage points of "
             "vote share (for check 4, of seat-adjusted share), with 95% CIs. Bold means p < 0.05. Main foreign "
             "rule throughout.", "",
             "Not run, for time (listed so nothing is hidden): full-name ethnicolr model, exact Census matches "
             "only, two-candidate races only, House without LA/CA/WA, local nonpartisan with estimated-party "
             "control.", ""]
    for name, _ in QUANTITIES:
        t = res[res["quantity"] == name].pivot_table(index="check", columns="sample", values="cell", aggfunc="first")
        t = t[[s for s in SAMPLES if s in t.columns]]
        lines += [f"## {name}", "", t.fillna("").to_markdown(), ""]
    n = res.drop_duplicates(["check", "sample"]).pivot_table(index="check", columns="sample",
                                                             values="n_contests", aggfunc="first")
    lines += ["## Number of races per check", "", n[[s for s in SAMPLES if s in n.columns]]
              .map(lambda v: f"{int(v):,}" if pd.notna(v) else "").to_markdown(), ""]
    (OUTPUT / "07_robustness.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
