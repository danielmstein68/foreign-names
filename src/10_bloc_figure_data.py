"""Data for the "names do better where residents share them" figure.

For each name group, computes the fitted effect (vs a white Anglo name in the
same race) at every 1% of "share of residents who share the name's
background" from 0% to 50%, with a 95% confidence band, plus the range where
most of that group's candidates actually run (10th-90th percentile).

  Hispanic, Black, Asian: step 8's co-ethnic model (all local races).
  German: step 9's within-group model with a German-specific slope.

Output: output/fig_bloc_data.json
Run:  .venv/bin/python src/10_bloc_figure_data.py
"""

import importlib
import json

import numpy as np
import pandas as pd

from common import OUTPUT

step5 = importlib.import_module("05_regressions")
step6 = importlib.import_module("06_quadrants")
step8 = importlib.import_module("08_coethnic")
step9 = importlib.import_module("09_ancestry_bloc")

GRID = np.round(np.arange(0, 0.501, 0.01), 2)


def band(model, main, slope):
    """Effect main + s*slope at each grid point, with a clustered 95% CI."""
    names = list(model._coefnames)
    G = int(model._G[0])
    t = step5.stats.t.ppf(0.975, G - 1)
    out = []
    for s in GRID:
        w = np.array([1.0 if n == main else s if n == slope else 0.0 for n in names])
        est = float(w @ model.coef().values)
        se = float(np.sqrt(w @ model._vcov @ w))
        out.append([float(s), round(est, 3), round(est - t * se, 3), round(est + t * se, 3)])
    return out


def main() -> None:
    df = step5.load_main_sample()
    df = df[df["source"] == "local"].copy()
    df["demo_year"] = df["year"].clip(upper=2020)
    df = df.merge(step8.place_demographics().rename(columns={"year": "demo_year"}), on=["fips", "demo_year"])
    df = df.merge(step9.ancestry_shares(), on="fips")

    groups = {}
    terms = "hispanic + black + api + foreign + hispanic:pl_hisp + black:pl_black + api:pl_asian"
    m = step5.fit(f"vs ~ {terms} + incumbent + incumbent_missing + C(party2) | contest_id", df)
    for key, label, name_col, place_col, inter in [
            ("black", "Black-coded surnames", "black", "pl_black", "black:pl_black"),
            ("hispanic", "Hispanic surnames", "hispanic", "pl_hisp", "hispanic:pl_hisp"),
            ("asian", "Asian surnames", "api", "pl_asian", "api:pl_asian")]:
        where = df.loc[df[name_col] > 0.5, place_col]
        groups[key] = dict(label=label, points=band(m, name_col, inter),
                           p10=round(float(where.quantile(0.1)), 3), p90=round(float(where.quantile(0.9)), 3),
                           n=int(len(where)))

    # German: white & foreign candidates whose most likely origin is Germanic, vs white & not foreign.
    dq = step6.add_quadrants(df, "foreign")
    dq["own_group"] = dq["eth_top"].map(step9.TOP_LABEL)
    wf = dq["q1"].eq(1) & dq["own_group"].notna()
    for g in step9.WHITE_ETHNIC:
        dq[f"wf_{g}"] = (wf & dq["own_group"].eq(g)).astype(int)
        dq[f"wf_{g}_x_anc"] = dq[f"wf_{g}"] * dq[f"anc_{g}"]
    terms = " + ".join(f"wf_{g} + wf_{g}_x_anc" for g in step9.WHITE_ETHNIC)
    dq["wf_other"] = (dq["q1"].eq(1) & dq["own_group"].isna()).astype(int)
    m = step5.fit(f"vs ~ {terms} + q2 + q3 + wf_other + incumbent + incumbent_missing + C(party2) | contest_id", dq)
    where = dq.loc[dq["wf_germanic"] == 1, "anc_germanic"]
    groups["german"] = dict(label="German surnames", points=band(m, "wf_germanic", "wf_germanic_x_anc"),
                            p10=round(float(where.quantile(0.1)), 3), p90=round(float(where.quantile(0.9)), 3),
                            n=int(len(where)))

    (OUTPUT / "fig_bloc_data.json").write_text(json.dumps(groups, indent=1), encoding="utf-8")
    for k, g in groups.items():
        p0, p50 = g["points"][0], g["points"][-1]
        print(f"{k:9s} n={g['n']:5d}  0%: {p0[1]:+.2f} [{p0[2]:+.2f},{p0[3]:+.2f}]  "
              f"50%: {p50[1]:+.2f} [{p50[2]:+.2f},{p50[3]:+.2f}]  most run between {g['p10']:.0%}-{g['p90']:.0%}")


if __name__ == "__main__":
    main()
