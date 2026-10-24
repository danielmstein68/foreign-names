"""Step 3: give every candidate a whiteness score and a foreignness score.

Whiteness side (Census 2010 surname file): pctwhite, pcthispanic, pctapi,
pctblack kept separately, plus nonwhite = 1 - pctwhite/100.

Foreignness side (ethnicolr Wikipedia surname model): the probability of each
of 13 origin groups, then the scores defined in docs/foreign_coding_rule.md:
  foreign      = 1 - P(British)                         (main rule)
  foreign_alt  = 1 - P(British, Germanic, French, Nordic)  (sensitivity rule)
plus 0/1 versions based on the single most likely group.

This step uses names only. It never looks at votes or who won.

Output: data/processed/candidates_scored.parquet
Run:  .venv/bin/python src/03_score_names.py
"""

import logging

import pandas as pd
from ethnicolr import estimate_wikipedia_surname

from common import PROCESSED, RAW, log_decision
from names import match_to_census, parse_name

logging.disable(logging.INFO)  # ethnicolr is chatty

ORIGINS = ["Asian,GreaterEastAsian,EastAsian", "Asian,GreaterEastAsian,Japanese", "Asian,IndianSubContinent",
           "GreaterAfrican,Africans", "GreaterAfrican,Muslim", "GreaterEuropean,British",
           "GreaterEuropean,EastEuropean", "GreaterEuropean,Jewish", "GreaterEuropean,WestEuropean,French",
           "GreaterEuropean,WestEuropean,Germanic", "GreaterEuropean,WestEuropean,Hispanic",
           "GreaterEuropean,WestEuropean,Italian", "GreaterEuropean,WestEuropean,Nordic"]

# From docs/foreign_coding_rule.md (fixed before results were seen).
NOT_FOREIGN_MAIN = {"GreaterEuropean,British"}
NOT_FOREIGN_ALT = NOT_FOREIGN_MAIN | {"GreaterEuropean,WestEuropean,Germanic",
                                      "GreaterEuropean,WestEuropean,French",
                                      "GreaterEuropean,WestEuropean,Nordic"}


def load_census() -> pd.DataFrame:
    """Census 2010 surnames: the raw file if Daniel added one, else ethnicolr's bundled copy."""
    raw = list(RAW.glob("**/Names_2010Census.csv"))
    if raw:
        return pd.read_csv(raw[0], na_values="(S)")
    import ethnicolr
    from pathlib import Path
    bundled = Path(ethnicolr.__file__).parent / "data" / "census" / "census_2010.parquet"
    return pd.read_parquet(bundled)


def short(origin: str) -> str:
    """'GreaterEuropean,WestEuropean,Italian' -> 'p_italian' (column name)."""
    return "p_" + origin.split(",")[-1].lower()


def main() -> None:
    df = pd.read_parquet(PROCESSED / "candidates.parquet")

    # 1. Surname from the full name, same parser for every source.
    parsed = df["candidate_name"].fillna("").map(parse_name)
    df["first_name"], df["surname"] = parsed.str[0], parsed.str[1]
    # A one-letter "surname" means the name had none ("kathy l"); leave it unscored.
    df.loc[df["surname"].str.len() < 2, "surname"] = ""
    log_decision("score", "Surnames parsed from the full candidate name with src/names.py for all sources, "
                 "instead of using HKS's own lastname column.",
                 "Same rule everywhere. Where the two disagree (0.7% of local rows) ours is usually right: "
                 "HKS splits 'van Bramer' -> 'bramer', 'St Lawrence' -> 'lawrence', and has junk like 'name)'.")

    # 2. Census whiteness side.
    census = load_census()
    matched = match_to_census(df["surname"], census)
    for col in ["census_key", "census_match_rule", "pctwhite", "pcthispanic", "pctapi", "pctblack"]:
        df[col] = matched[col].values
    df["nonwhite"] = 1 - df["pctwhite"] / 100

    # 3. ethnicolr foreignness side: score each distinct surname once, then merge back.
    unique = pd.DataFrame({"surname": df["surname"].loc[df["surname"] != ""].unique()})
    scored = estimate_wikipedia_surname(unique.assign(ln=unique["surname"]), "ln")
    scored = scored.rename(columns={o: short(o) for o in ORIGINS})
    scored["surname"] = unique["surname"].values  # ethnicolr re-cases its input column
    scored["eth_abstained"] = scored["abstained"].astype(bool)
    scored["eth_top"] = scored["race"]
    keep = ["surname", "eth_top", "eth_abstained"] + [short(o) for o in ORIGINS]
    df = df.merge(scored[keep], on="surname", how="left")

    p = lambda groups: df[[short(o) for o in groups]].sum(axis=1)
    df["foreign"] = 1 - p(NOT_FOREIGN_MAIN)
    df["foreign_alt"] = 1 - p(NOT_FOREIGN_ALT)
    df["foreign_top"] = (~df["eth_top"].isin(NOT_FOREIGN_MAIN)).astype(int)
    df["foreign_top_alt"] = (~df["eth_top"].isin(NOT_FOREIGN_ALT)).astype(int)
    bad = df["eth_abstained"].fillna(True) | (df["surname"] == "")
    df.loc[bad, ["foreign", "foreign_alt", "foreign_top", "foreign_top_alt"]] = pd.NA

    df["census_matched"] = df["pctwhite"].notna()
    df["fully_scored"] = df["census_matched"] & df["foreign"].notna()
    df.to_parquet(PROCESSED / "candidates_scored.parquet", index=False)

    # Console summary (match rates only; the checkpoint script does the full report).
    print("Census match rule by source (share of candidates):")
    print(pd.crosstab(df["source"], df["census_match_rule"], normalize="index").round(3).to_string())
    print("\nethnicolr abstained:", int(df["eth_abstained"].fillna(True).sum()), "candidates")
    print("Fully scored share by source:")
    print(df.groupby("source")["fully_scored"].mean().round(3).to_string())
    print(f"\nSaved {len(df):,} rows to {PROCESSED / 'candidates_scored.parquet'}")


if __name__ == "__main__":
    main()
