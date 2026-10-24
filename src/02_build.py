"""Step 2: build one candidate-level table from all three election sources.

Output: data/processed/candidates.parquet, one row per candidate per contest,
with the same columns for every source:

  source        'local', 'house' or 'senate'
  office        e.g. 'Mayor', 'US House'
  year, state   year of the election, two-letter state code
  jurisdiction_id  the place that recurs over time (city/county, House district,
                   state); used to cluster standard errors
  contest_id    one race; candidates are compared within it
  candidate_name, last_name_raw, first_name_raw
  party         ballot party, 'DEM' / 'REP' / 'OTHER' (NA for local races,
                which HKS does not record)
  pid_est       HKS's *estimated* party of local candidates ('D' / 'R')
  nonpartisan   True if no party label on the ballot (see decision log)
  incumbent     1 / 0 (NA when unknown)
  votes, contest_votes, vote_share
  seats, n_candidates, winner
  uncontested, multiseat   flags; nothing is dropped here, step 4 drops them

Run:  .venv/bin/python src/02_build.py
"""

import pandas as pd

from common import PROCESSED, log_decision
from names import parse_name
from readers import read_hks, read_mit_house, read_mit_senate

# Rows that are vote totals, not people.
PLACEHOLDER = (r"^(OTHER|OTHERS|ALL OTHERS|OTHER WRITE-INS|MISCELLANEOUS|INDEPENDENT|PRO-LIFE"
               r"|BLANK.*|SCATTER.*|VOID.*|UNDER ?VOTES?|OVER ?VOTES?|NONE OF THESE CANDIDATES)$")

DEM_LABELS = {"DEMOCRAT", "DEMOCRATIC-FARMER-LABOR", "DEMOCRATIC-FARM-LABOR",
              "DEMOCRATIC-NONPARTISAN LEAGUE", "DEMOCRATIC-NPL"}
REP_LABELS = {"REPUBLICAN", "INDEPENDENT-REPUBLICAN"}

# HKS has no nonpartisan flag, so we classify by office type (agreed with Daniel).
NONPARTISAN_OFFICES = {"City Council", "Mayor", "School Board"}


def simple_party(label) -> str:
    """Collapse a ballot party label to DEM / REP / OTHER."""
    if pd.isna(label):
        return "OTHER"
    label = str(label).upper()
    if label in DEM_LABELS:
        return "DEM"
    if label in REP_LABELS:
        return "REP"
    return "OTHER"


def collapse_fusion(df: pd.DataFrame) -> pd.DataFrame:
    """Combine a candidate's votes across party lines (fusion tickets, e.g. NY).

    A candidate counts as DEM (or REP) if any of their lines is that party;
    if somehow both, the line with more votes wins.
    """
    df = df.assign(party=df["party_raw"].map(simple_party))
    df = df.sort_values("votes", ascending=False)
    major = df[df["party"] != "OTHER"].groupby(["contest_id", "candidate_name"])["party"].first()
    out = (df.groupby(["contest_id", "candidate_name"], as_index=False)
             .agg(votes=("votes", "sum"), **{c: (c, "first") for c in
                  ["source", "office", "year", "state", "jurisdiction_id", "special", "party"]}))
    out["party"] = out.set_index(["contest_id", "candidate_name"]).index.map(major).fillna("OTHER")
    return out


REDISTRICTING_YEARS = {1982, 1992, 2002, 2012, 2022}


def infer_incumbency(df: pd.DataFrame, lookback: int) -> pd.Series:
    """Flag a candidate as incumbent if they won this seat within the previous
    `lookback` years. Names are written differently across years (WILLIAM L
    "BILL" DICKINSON vs BILL DICKINSON), so we match in two ways:

    Rule A: same first name + surname, and won the same district. In
            redistricting years district numbers change, so any district in
            the same state counts.
    Rule B (catches nicknames): same surname + same party, same district.

    An earlier, looser version (surname + first initial anywhere in the state)
    produced false matches such as challenger John T. Anderson being matched
    to incumbent John B. Anderson; we check the result by counting
    incumbents per contest.
    """
    parsed = df["candidate_name"].map(parse_name)
    first, last = parsed.str[0], parsed.str[1]
    winners = df.assign(first=first, last=last)[df["winner"] == 1]

    # Sets of (who, where, year) that won, for fast lookup.
    won_district = set(zip(winners["first"], winners["last"], winners["jurisdiction_id"], winners["year"]))
    won_state = set(zip(winners["first"], winners["last"], winners["state"], winners["year"]))
    won_party = set(zip(winners["last"], winners["party"], winners["jurisdiction_id"], winners["year"]))

    def check(f, l, juris, state, party, y):
        for prev in range(y - lookback, y):
            if (f, l, juris, prev) in won_district:
                return 1
            if y in REDISTRICTING_YEARS and (f, l, state, prev) in won_state:
                return 1
            if party != "OTHER" and (l, party, juris, prev) in won_party:
                return 1
        return 0

    rows = zip(first, last, df["jurisdiction_id"], df["state"], df["party"], df["year"])
    return pd.Series([check(*r) for r in rows], index=df.index)


def add_contest_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Vote share, number of candidates, uncontested and multi-seat flags."""
    g = df.groupby("contest_id")
    df["contest_votes"] = g["votes"].transform("sum")
    df["vote_share"] = df["votes"] / df["contest_votes"]
    df["n_candidates"] = g["votes"].transform("size")
    df["uncontested"] = df["n_candidates"] <= df["seats"]
    df["multiseat"] = df["seats"] > 1
    return df


def build_house() -> pd.DataFrame:
    h = read_mit_house()
    n0 = len(h)
    keep = (h["stage"] == "GEN") & ~h["special"].fillna(False) & ~h["runoff"].fillna(False)
    log_decision("build/house", f"Kept regular general elections only: dropped {(~keep).sum():,} of {n0:,} rows "
                 "(primaries, runoffs, specials).", "Spec covers general elections; specials have unusual timing and turnout.")
    h = h[keep]
    wi = h["writein"].fillna(False)
    ph = h["candidate"].isna() | h["candidate"].str.upper().str.match(PLACEHOLDER)
    log_decision("build/house", f"Dropped {wi.sum():,} write-in rows and {(ph & ~wi).sum():,} placeholder rows "
                 "(OTHER, BLANK, SCATTERING, OVER/UNDERVOTES...). They are excluded from contest vote totals too.",
                 "Spec: exclude write-ins as MIT marks them; placeholders are not candidates.")
    h = h[~wi & ~ph]
    h = pd.DataFrame({
        "source": "house", "office": "US House", "year": h["year"].astype(int), "state": h["state_po"],
        "jurisdiction_id": "house_" + h["state_po"] + "_" + h["district"].astype(str),
        "contest_id": "house_" + h["year"].astype(str) + "_" + h["state_po"] + "_" + h["district"].astype(str),
        "candidate_name": h["candidate"], "party_raw": h["party"], "votes": h["candidatevotes"].astype(float),
        "special": False,
    })
    n_before = len(h)
    h = collapse_fusion(h)
    log_decision("build/house", f"Combined fusion-ticket lines: {n_before:,} rows -> {len(h):,} candidates.",
                 "Spec outcome is candidate vote share, so a candidate's votes on all party lines are summed.")
    return h


def build_senate() -> pd.DataFrame:
    s = read_mit_senate()
    n0 = len(s)
    keep = s["stage"].str.lower() == "gen"
    log_decision("build/senate", f"Kept general elections (stage 'gen'/'GEN'), dropped {(~keep).sum():,} of {n0:,} rows "
                 "(primaries, runoffs). Senate special elections are KEPT (as separate contests) and flagged.",
                 "Senate specials are mostly held on the November general-election ballot, unlike House specials.")
    s = s[keep]
    ph = s["candidate"].isna() | s["candidate"].str.upper().str.match(PLACEHOLDER)
    wi = s["writein"].astype(bool)
    log_decision("build/senate", f"Dropped {wi.sum():,} write-in rows and {(ph & ~wi).sum():,} placeholder rows.",
                 "Same rule as House.")
    s = s[~wi & ~ph]
    special_tag = s["special"].map({True: "special", False: "regular"})
    s = pd.DataFrame({
        "source": "senate", "office": "US Senate", "year": s["year"].astype(int), "state": s["state_po"],
        "jurisdiction_id": "senate_" + s["state_po"],
        "contest_id": "senate_" + s["year"].astype(str) + "_" + s["state_po"] + "_" + special_tag,
        "candidate_name": s["candidate"], "party_raw": s["party_detailed"], "votes": s["candidatevotes"].astype(float),
        "special": s["special"].astype(bool),
    })
    return collapse_fusion(s)


def finish_federal(df: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """Shared steps for House and Senate: seats, winners, incumbency."""
    df["seats"] = 1
    df = add_contest_columns(df)
    df["winner"] = (df["votes"] == df.groupby("contest_id")["votes"].transform("max")).astype(int)
    df["incumbent"] = infer_incumbency(df, lookback)
    parsed = df["candidate_name"].map(parse_name)
    df["first_name_raw"], df["last_name_raw"] = parsed.str[0], parsed.str[1]
    df["nonpartisan"] = False
    df["pid_est"] = pd.NA
    return df


def build_local() -> pd.DataFrame:
    d = read_hks()
    log_decision("build/local", f"Office types {sorted(NONPARTISAN_OFFICES)} coded nonpartisan; County Legislature, "
                 "County Executive, Sheriff and Prosecutor coded partisan.",
                 "HKS has no ballot-type flag (checked readme). Office type is the agreed proxy; it is wrong "
                 "for some states (e.g. partisan city elections in some places), stated as a limitation.")
    log_decision("build/local", "Vote share recomputed as votes / sum of votes in the contest, not taken from "
                 "HKS's vote_share column.", "HKS vote_share does not always sum to 1 within a contest.")
    return pd.DataFrame({
        "source": "local", "office": d["office_consolidated"], "year": d["year"], "state": d["state_abb"],
        "jurisdiction_id": "local_" + d["state_abb"] + "_" + d["fips"].astype(str),
        "contest_id": "local_" + d["contest"],
        "candidate_name": d["full_name"], "first_name_raw": d["firstname"], "last_name_raw": d["lastname"],
        "party": pd.NA, "pid_est": d["pid_est"],
        "nonpartisan": d["office_consolidated"].isin(NONPARTISAN_OFFICES),
        "incumbent": d["incumbent"], "votes": d["votes"], "seats": d["n_winners"],
        "winner": (d["winner"] == "win").astype(int), "special": False,
        "fips": d["fips"], "month": d["month"],
    }).pipe(add_contest_columns)


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    house = finish_federal(build_house(), lookback=2)
    senate = finish_federal(build_senate(), lookback=6)
    log_decision("build/federal", "Incumbency inferred: a candidate is the incumbent if they won the same seat in the "
                 "previous House election (2 years) or within the previous 6 years for Senate. Match on first name + "
                 "surname in the same district (any district in the state in redistricting years), or on surname + "
                 "party in the same district (for nickname changes). A looser first-initial rule was tried first and "
                 "rejected: it produced false matches (e.g. challenger John T. Anderson vs incumbent John B. Anderson).",
                 "MIT files have no incumbency flag; spec says infer it and say so. Misses appointed senators "
                 "and members first elected in a special election.")
    local = build_local()
    cols = ["source", "office", "year", "state", "jurisdiction_id", "contest_id", "candidate_name",
            "first_name_raw", "last_name_raw", "party", "pid_est", "nonpartisan", "incumbent", "votes",
            "contest_votes", "vote_share", "seats", "n_candidates", "winner", "uncontested", "multiseat",
            "special", "fips", "month"]
    out = pd.concat([df.reindex(columns=cols) for df in (local, house, senate)], ignore_index=True)
    out.to_parquet(PROCESSED / "candidates.parquet", index=False)

    # Short summary for the console.
    print("\nCandidates and contests by source:")
    print(out.groupby("source").agg(candidates=("contest_id", "size"), contests=("contest_id", "nunique"),
                                    uncontested=("uncontested", "sum"), multiseat=("multiseat", "sum")).to_string())
    fed = out[out["source"] != "local"]
    inc = fed[~fed["uncontested"]].groupby(["source", "contest_id"])["incumbent"].sum()
    print("\nIncumbents per contested federal race (check: should be mostly 0 or 1):")
    print(inc.groupby("source").value_counts().unstack(fill_value=0).to_string())
    print(f"\nSaved {len(out):,} rows to {PROCESSED / 'candidates.parquet'}")


if __name__ == "__main__":
    main()
