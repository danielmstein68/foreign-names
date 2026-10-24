"""Step 5: main regressions (approved by Daniel after the checkpoint).

Three designs, all comparing candidates who share a race or a district:

A. Spec model (every sample): candidate vote share on name scores, with
   contest fixed effects, so candidates are only compared with opponents in
   the same race.
       vote_share = b1*nonwhite + b2*foreign + b3*nonwhite*foreign
                    + incumbent (+ party) + contest FE
B. Overperformance (Senate, local partisan): the same model, but the outcome
   is vote share minus the party's presidential vote share in that state or
   county. This removes how Democratic or Republican the place is.
C. Swing (House, Senate): one row per district-election. The Democratic share
   of the two-party vote on the *difference* in name scores (Democrat minus
   Republican), with district fixed effects (within a redistricting cycle) and
   year fixed effects. The question: does the Democrats' share drop, relative
   to their usual level in that district, when their candidate's name is more
   foreign than the Republican's?

Plus: separate Hispanic/Black/Asian shares, a conditional logit on winning,
pooled models, and the exploratory Middle Eastern / Muslim-origin add-on.

How to read the hypotheses (scores run from 0 to 1):
  H2 (foreign but white-coded carries little penalty): b2 near 0.
  H1 (non-white AND foreign carries a large penalty): b1 + b3, the extra
      penalty for a fully non-white name when the name is fully foreign;
      b1 + b2 + b3 is the total gap versus a white, Anglo name.
Effects are reported in percentage points of vote share.

Standard errors are clustered by jurisdiction (city/county, House district,
state). Output: output/05_results.md and output/05_results.csv
Run:  .venv/bin/python src/05_regressions.py
"""

import warnings

import numpy as np
import pandas as pd
import pyfixest as pf
from scipy import stats

from clogit import fit_clogit
from common import DOCS, OUTPUT, PROCESSED, log_decision
from readers import read_county_president, read_state_president

warnings.filterwarnings("ignore")

NAME_TERMS = "nonwhite + foreign + nonwhite:foreign"
RESULTS = []      # one dict per reported quantity, saved to CSV
REPORT = []       # Markdown lines


# --------------------------------------------------------------------------
# Data preparation
# --------------------------------------------------------------------------

def load_main_sample() -> pd.DataFrame:
    """Contested, single-seat races; candidates with both name scores;
    contests that still have at least 2 scored candidates."""
    df = pd.read_parquet(PROCESSED / "candidates_scored.parquet")
    df = df[~df["uncontested"] & ~df["multiseat"] & df["fully_scored"]].copy()
    df = df[df.groupby("contest_id")["contest_id"].transform("size") >= 2]

    df["sample"] = np.select(
        [df["source"].eq("house"), df["source"].eq("senate"), df["nonpartisan"]],
        ["House", "Senate", "Local nonpartisan"], "Local partisan")
    df["vs"] = df["vote_share"] * 100  # percentage points

    # Local incumbency is missing for 18% of candidates: keep them, with a flag.
    df["incumbent_missing"] = df["incumbent"].isna().astype(int)
    df["incumbent"] = df["incumbent"].fillna(0)

    # Party: ballot party for House/Senate; HKS's *estimated* party for local partisan.
    est = df["pid_est"].map({"D": "DEM", "R": "REP"})
    df["party2"] = np.where(df["source"] == "local", est.fillna("UNKNOWN"), df["party"].fillna("OTHER"))
    df.loc[df["sample"] == "Local nonpartisan", "party2"] = "NONE"

    for g in ["hispanic", "black", "api"]:
        df[g] = df[f"pct{g}"] / 100

    review = pd.read_csv(DOCS / "mena_name_review.csv")
    keep = set(review.loc[review["decision"] == "keep", "surname"])
    df["mena"] = df["surname"].isin(keep).astype(int)
    df["mena_strict"] = (df["mena"].astype(bool) & (df["p_muslim"] > 0.8)).astype(int)
    return df


def presidential_baselines():
    """Party share of the presidential vote, by state-year and county-year."""
    s = read_state_president()
    s = s[s["party_simplified"].isin(["DEMOCRAT", "REPUBLICAN"])]
    state = (s.groupby(["year", "state_po", "party_simplified"])["candidatevotes"].sum()
             / s.groupby(["year", "state_po"])["totalvotes"].first()).rename("pres_share").reset_index()
    state["party2"] = state["party_simplified"].map({"DEMOCRAT": "DEM", "REPUBLICAN": "REP"})

    c = read_county_president().dropna(subset=["county_fips"])
    c["fips"] = c["county_fips"].str.zfill(5)
    # Use the TOTAL rows where a county reports them; otherwise add up the vote-mode rows.
    has_total = c.groupby(["year", "fips"])["mode"].transform(lambda m: (m == "TOTAL").any())
    c = c[~has_total | (c["mode"] == "TOTAL")]
    tot = c.groupby(["year", "fips"])["candidatevotes"].sum()
    maj = c[c["party"].isin(["DEMOCRAT", "REPUBLICAN"])]
    county = (maj.groupby(["year", "fips", "party"])["candidatevotes"].sum() / tot).rename("pres_share").reset_index()
    county["party2"] = county["party"].map({"DEMOCRAT": "DEM", "REPUBLICAN": "REP"})
    return state[["year", "state_po", "party2", "pres_share"]], county[["year", "fips", "party2", "pres_share"]]


def last_pres_year(year: pd.Series) -> pd.Series:
    """Most recent presidential election year at or before `year`."""
    return year - (year % 4)


# --------------------------------------------------------------------------
# Estimation helpers
# --------------------------------------------------------------------------

def lincom(model, terms: list[str]) -> tuple[float, float, float, float]:
    """Sum of coefficients with a clustered 95% CI: (estimate, lo, hi, p)."""
    names = list(model._coefnames)
    w = np.array([1.0 if n in terms else 0.0 for n in names])
    est = float(w @ model.coef().values)
    se = float(np.sqrt(w @ model._vcov @ w))
    dof = max(int(model._G[0]) - 1, 1) if model._is_clustered else model._N - len(names)
    t = stats.t.ppf(0.975, dof)
    p = 2 * stats.t.sf(abs(est / se), dof)
    return est, est - t * se, est + t * se, p


def record(design, sample, label, model, n_contests, extra_terms=None):
    """Store b1, b2, b3 (and H1/total combinations) from a fitted model."""
    tidy = model.tidy()
    rows = []
    wanted = {"nonwhite": "b1 non-white", "foreign": "b2 foreign (H2: ~0?)",
              "nonwhite:foreign": "b3 non-white × foreign"}
    for term in extra_terms or []:
        wanted[term] = term
    for term, name in wanted.items():
        if term in tidy.index:
            r = tidy.loc[term]
            rows.append((name, r["Estimate"], r["2.5%"], r["97.5%"], r["Pr(>|t|)"]))
    if {"nonwhite", "nonwhite:foreign"} <= set(tidy.index):
        rows.append(("b1+b3 (H1: non-white penalty when foreign)", *lincom(model, ["nonwhite", "nonwhite:foreign"])))
        rows.append(("b1+b2+b3 (non-white & foreign vs white & Anglo)",
                     *lincom(model, ["nonwhite", "foreign", "nonwhite:foreign"])))
    clusters = int(model._G[0]) if model._is_clustered else None
    for name, est, lo, hi, p in rows:
        RESULTS.append(dict(design=design, sample=sample, spec=label, quantity=name, estimate=est, ci_low=lo,
                            ci_high=hi, p=p, n_obs=model._N, n_contests=n_contests, n_clusters=clusters))


def fit(formula, data, cluster="jurisdiction_id"):
    return pf.feols(formula, data=data, vcov={"CRV1": cluster})


def controls_for(sample: str) -> str:
    if sample == "Local nonpartisan":
        return "incumbent + incumbent_missing"
    if sample == "Local partisan":
        return "incumbent + incumbent_missing + C(party2)"
    return "incumbent + C(party2)"


# --------------------------------------------------------------------------
# Designs
# --------------------------------------------------------------------------

def design_a(df):
    """Spec model: raw vote share, contest FE, per sample and pooled."""
    samples = ["Local nonpartisan", "Local partisan", "House", "Senate"]
    for s in samples:
        d = df[df["sample"] == s]
        m = fit(f"vs ~ {NAME_TERMS} + {controls_for(s)} | contest_id", d)
        record("A. Vote share (spec)", s, "main", m, d["contest_id"].nunique())

        # Separate Hispanic / Black / Asian shares instead of one non-white score.
        m = fit(f"vs ~ hispanic + black + api + foreign + hispanic:foreign + black:foreign + api:foreign"
                f" + {controls_for(s)} | contest_id", d)
        record("A. Vote share (spec)", s, "Hispanic/Black/Asian split", m, d["contest_id"].nunique(),
               extra_terms=["hispanic", "black", "api", "hispanic:foreign", "black:foreign", "api:foreign"])

        # Same split without interactions. Nearly every Hispanic or Asian surname is also "foreign",
        # so the interacted version above cannot separate the terms; this one can.
        m = fit(f"vs ~ hispanic + black + api + foreign + {controls_for(s)} | contest_id", d)
        record("A. Vote share (spec)", s, "Hispanic/Black/Asian split, no interactions", m,
               d["contest_id"].nunique(), extra_terms=["hispanic", "black", "api"])

        # Sensitivity foreign rule (German/French/Nordic count as not foreign), a headline result.
        d2 = d.assign(foreign=d["foreign_alt"])
        m = fit(f"vs ~ {NAME_TERMS} + {controls_for(s)} | contest_id", d2)
        record("A. Vote share (spec)", s, "alt foreign rule", m, d["contest_id"].nunique())

    # Pooled: party dummies are allowed to differ by source; the contest FE absorbs source itself.
    pooled_ctrl = "incumbent + incumbent_missing + C(party2):C(source)"
    for label, d in [("all sources", df), ("without Senate", df[df["sample"] != "Senate"])]:
        m = fit(f"vs ~ {NAME_TERMS} + {pooled_ctrl} | contest_id", d)
        record("A. Vote share (spec)", f"Pooled, {label}", "main", m, d["contest_id"].nunique())
        d2 = d.assign(foreign=d["foreign_alt"])
        m = fit(f"vs ~ {NAME_TERMS} + {pooled_ctrl} | contest_id", d2)
        record("A. Vote share (spec)", f"Pooled, {label}", "alt foreign rule", m, d["contest_id"].nunique())

    # Exploratory add-on: Middle Eastern / Muslim-origin names, pooled only.
    for var in ["mena", "mena_strict"]:
        m = fit(f"vs ~ {NAME_TERMS} + {var} + {pooled_ctrl} | contest_id", df)
        record("A. Vote share (spec)", "Pooled, all sources", f"+ {var} (exploratory)", m,
               df["contest_id"].nunique(), extra_terms=[var])


def design_b(df, state_pres, county_pres):
    """Overperformance vs the party's presidential share: Senate and local partisan."""
    df = df.assign(pres_year=last_pres_year(df["year"]))
    sen = df[(df["sample"] == "Senate") & df["party2"].isin(["DEM", "REP"])].merge(
        state_pres.rename(columns={"year": "pres_year", "state_po": "state"}), on=["pres_year", "state", "party2"])
    loc = df[(df["sample"] == "Local partisan") & df["party2"].isin(["DEM", "REP"]) & (df["year"] >= 2000)]
    loc = loc.assign(fips=loc["fips"].astype(str)).merge(
        county_pres.rename(columns={"year": "pres_year"}), on=["pres_year", "fips", "party2"])
    for s, d in [("Senate", sen), ("Local partisan", loc)]:
        d = d.assign(over=d["vs"] - d["pres_share"] * 100)
        d = d[d.groupby("contest_id")["contest_id"].transform("size") >= 2]
        ctrl = "incumbent" if s == "Senate" else "incumbent + incumbent_missing"
        m = fit(f"over ~ {NAME_TERMS} + {ctrl} + C(party2) | contest_id", d)
        record("B. Overperformance vs presidential vote", s, "main", m, d["contest_id"].nunique())
        m = fit(f"over ~ {NAME_TERMS} + {ctrl} + C(party2) | contest_id", d.assign(foreign=d["foreign_alt"]))
        record("B. Overperformance vs presidential vote", s, "alt foreign rule", m, d["contest_id"].nunique())
    return len(sen), len(loc)


def design_c(df):
    """Swing design: Democratic two-party share in a district over time."""
    fed = df[df["sample"].isin(["House", "Senate"]) & df["party2"].isin(["DEM", "REP"])]
    # Keep races with exactly one scored Democrat and one scored Republican.
    one_each = fed.groupby("contest_id")["party2"].transform(lambda p: (p == "DEM").sum() == 1 and (p == "REP").sum() == 1)
    fed = fed[one_each]
    cols = ["nonwhite", "foreign", "foreign_alt", "incumbent", "votes"]
    wide = fed.pivot_table(index=["contest_id", "sample", "year", "state", "jurisdiction_id"],
                           columns="party2", values=cols).reset_index()
    wide.columns = ["_".join(c).strip("_") for c in wide.columns]
    wide["dem2p"] = 100 * wide["votes_DEM"] / (wide["votes_DEM"] + wide["votes_REP"])
    for v in ["nonwhite", "foreign", "foreign_alt"]:
        wide[f"d_{v}"] = wide[f"{v}_DEM"] - wide[f"{v}_REP"]
    wide["d_nwxf"] = wide["nonwhite_DEM"] * wide["foreign_DEM"] - wide["nonwhite_REP"] * wide["foreign_REP"]
    wide["d_nwxf_alt"] = wide["nonwhite_DEM"] * wide["foreign_alt_DEM"] - wide["nonwhite_REP"] * wide["foreign_alt_REP"]
    # House districts are redrawn each decade: a district is only "the same place" within a cycle.
    cycle = np.select([wide["year"] < 1982, wide["year"] < 1992, wide["year"] < 2002, wide["year"] < 2012,
                       wide["year"] < 2022], ["1970s", "1980s", "1990s", "2000s", "2010s"], "2020s")
    wide["district_cycle"] = np.where(wide["sample"] == "House", wide["jurisdiction_id"] + "_" + cycle,
                                      wide["jurisdiction_id"])
    for s in ["House", "Senate"]:
        d = wide[wide["sample"] == s]
        for label, f, x in [("main", "d_foreign", "d_nwxf"), ("alt foreign rule", "d_foreign_alt", "d_nwxf_alt")]:
            m = fit(f"dem2p ~ d_nonwhite + {f} + {x} + incumbent_DEM + incumbent_REP | district_cycle + year", d)
            # Rename so the table reads the same as the other designs. A positive gap in the
            # Democrat's score should lower the Democratic share, so the signs match design A.
            m._coefnames = [{"d_nonwhite": "nonwhite", f: "foreign", x: "nonwhite:foreign"}.get(n, n)
                            for n in m._coefnames]
            m.tidy = (lambda mm=m, orig=m.tidy: orig().rename(
                index={"d_nonwhite": "nonwhite", f: "foreign", x: "nonwhite:foreign"}))
            record("C. Swing (Dem two-party share, district FE)", s, label, m, m._N)  # one race per row
    return len(wide)


def conditional_logit(df):
    """Secondary outcome: who wins, comparing candidates within a contest."""
    out = []
    for s in ["Local nonpartisan", "Local partisan", "House", "Senate"]:
        d = df[df["sample"] == s].copy()
        d = d[d.groupby("contest_id")["winner"].transform("sum") == 1]  # exactly one winner
        d["nonwhite_x_foreign"] = d["nonwhite"] * d["foreign"]
        X = d[["nonwhite", "foreign", "nonwhite_x_foreign", "incumbent"]].copy()
        if s == "Local nonpartisan" or s == "Local partisan":
            X["incumbent_missing"] = d["incumbent_missing"]
        if s != "Local nonpartisan":
            X = X.join(pd.get_dummies(d["party2"], prefix="party", drop_first=True, dtype=float))
        r = fit_clogit(d["winner"], X.astype(float), d["contest_id"], d["jurisdiction_id"])
        if not r["converged"].all():
            raise RuntimeError(f"conditional logit did not converge for {s}")
        for term, name in [("nonwhite", "b1 non-white"), ("foreign", "b2 foreign (H2: ~0?)"),
                           ("nonwhite_x_foreign", "b3 non-white × foreign")]:
            out.append(dict(design="D. Win (conditional logit, odds ratios)", sample=s, spec="main", quantity=name,
                            estimate=np.exp(r.loc[term, "coef"]), ci_low=np.exp(r.loc[term, "ci_low"]),
                            ci_high=np.exp(r.loc[term, "ci_high"]), p=r.loc[term, "p"], n_obs=len(d),
                            n_contests=d["contest_id"].nunique(), n_clusters=d["jurisdiction_id"].nunique()))
    RESULTS.extend(out)


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------

def fmt(row) -> str:
    stars = "**" if row["p"] < 0.05 else ""
    return f"{stars}{row['estimate']:+.2f}{stars} [{row['ci_low']:+.2f}, {row['ci_high']:+.2f}]"


def write_report(res: pd.DataFrame, n_info: dict) -> None:
    REPORT.extend(["# Main regression results", "",
                   "Generated by `src/05_regressions.py`. Estimates are in **percentage points of vote share**. "
                   "The conditional logit (D) reports **odds ratios**, where 1 means no difference.",
                   "Each cell shows the estimate and its 95% confidence interval, clustered by jurisdiction. "
                   "Bold means p < 0.05.", "",
                   "Scores run from 0 to 1, so a coefficient is the gap between a fully white (or fully Anglo) "
                   "surname and a fully non-white (or fully foreign) one. A typical gap between candidates is "
                   "much smaller, about 0.3.", ""])
    for design, g in res.groupby("design", sort=False):
        REPORT.extend([f"## {design}", ""])
        for spec, gs in g.groupby("spec", sort=False):
            table = gs.pivot_table(index="quantity", columns="sample", values="row", aggfunc="first", sort=False)
            ns = gs.groupby("sample", sort=False).agg(n_obs=("n_obs", "first"), n_contests=("n_contests", "first"),
                                                      n_clusters=("n_clusters", "first"))
            for c in ["n_obs", "n_contests", "n_clusters"]:
                table.loc[f"N: {c.split('_')[1]}"] = ns[c].map(lambda v: f"{int(v):,}" if pd.notna(v) else "")
            REPORT.extend([f"### {spec}", "", table.to_markdown(), ""])
    REPORT.extend(["## Sample notes", ""] + [f"- {k}: {v}" for k, v in n_info.items()])
    (OUTPUT / "05_results.md").write_text("\n".join(REPORT), encoding="utf-8")


def main() -> None:
    df = load_main_sample()
    state_pres, county_pres = presidential_baselines()
    log_decision("regress", "Local candidates with missing incumbency (18%) are kept, with incumbent set to 0 and "
                 "a missing-incumbency indicator added.", "Dropping them would lose many contests; the "
                 "indicator stops the fill-in from biasing the incumbency coefficient.")
    log_decision("regress", "For local partisan races, the party control is HKS's estimated party (pid_est: D/R/"
                 "unknown), because HKS does not record the ballot party.", "It is the only party information "
                 "available for local races; it is an estimate, not the label voters saw.")
    log_decision("regress", "Overperformance baseline is the party's share of the presidential vote (of all votes "
                 "cast) in the most recent presidential election in or before the race's year: state level for "
                 "Senate, county level for local partisan (2000+, 5-digit county FIPS only). Only Democrats and "
                 "Republicans enter this design.", "Matches the candidate vote-share outcome, which is also a share "
                 "of all votes.")
    log_decision("regress", "Swing design: House and Senate races with exactly one scored Democrat and one scored "
                 "Republican; Democratic two-party share on (Democrat score − Republican score), with district × "
                 "redistricting-cycle fixed effects (state for Senate), year fixed effects, and both incumbency "
                 "flags. Not run for local partisan races.", "District-cycle effects make each district its own "
                 "baseline. Local districts can't be followed reliably over time in HKS.")
    log_decision("regress", "Pooled models allow party effects to differ by source (party × source dummies).",
                 "The contest fixed effect already absorbs source.")

    design_a(df)
    n_sen, n_loc = design_b(df, state_pres, county_pres)
    n_swing = design_c(df)
    conditional_logit(df)

    res = pd.DataFrame(RESULTS)
    res["row"] = res.apply(fmt, axis=1)
    OUTPUT.mkdir(exist_ok=True)
    res.drop(columns="row").to_csv(OUTPUT / "05_results.csv", index=False)
    write_report(res, {
        "Main sample": f"{len(df):,} candidates in {df['contest_id'].nunique():,} contested single-seat races",
        "Overperformance rows matched to a presidential baseline": f"Senate {n_sen:,}, local partisan {n_loc:,}",
        "Swing design district-elections": f"{n_swing:,}",
        "Middle Eastern / Muslim-origin candidates in main sample": f"{df['mena'].sum()} (strict: {df['mena_strict'].sum()})",
    })
    print((OUTPUT / "05_results.md").read_text())


if __name__ == "__main__":
    main()
