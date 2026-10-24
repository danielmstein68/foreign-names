"""Hand review of surnames flagged as "Muslim" origin by ethnicolr.

ethnicolr's "GreaterAfrican,Muslim" group is a region of origin, not a religion,
and it misfires on some names (Moneymaker, Altmire, Mabry...). Every surname
with P(Muslim) > 0.65 was reviewed by Claude on 2026-10-24, BEFORE any vote
results were looked at; Daniel delegated this review. Names are struck if they
are clearly of another origin, or if the origin is unclear (precision over
recall). Arab Christian, Armenian and African-American Muslim names are kept:
voters cannot read religion off a surname either.

Running this file writes docs/mena_name_review.csv, the auditable record.
"""

import pandas as pd

from common import DOCS, PROCESSED

THRESHOLD = 0.65
STRICT_THRESHOLD = 0.8

# Clearly another origin (English, German, Italian, Greek, Hispanic, Polish,
# Hindu Indian, Hawaiian/Samoan, Akan, Native American...).
NOT_MENA = {
    "MONEYMAKER", "RAMLOGAN", "ANWILER", "CONSTANTINOPLE", "SULIBURK", "MOEPONO", "MARTINEZ-ALIRE",
    "SALESMAN", "ANANTATMULA", "HUTHMAN", "SIGAFOOSE", "SINAGRA", "BATMAN", "ISENHOUR", "SUMEREL",
    "BOUNARROTI", "CHALIFOUR", "SINAPI", "KESARWANI", "ZEDIKER", "GAGHAGEN", "ORAZEM", "SITOMER",
    "CHRISTIANA", "SILIPENA", "YENSEN", "MAOUNIS", "DILENA", "RINIKER", "LINCECUM", "NALVEN",
    "DELEHANTY", "DANTONA", "DESMUKES", "WASIK", "DIFILIPPO", "MABRY", "EMRY", "JAKMIDES", "SUNIGA",
    "SEDITA", "JULIANA", "LATURNER", "SHAFTO", "ICENHOUR", "OSNAYA", "AFISVALU", "TECUMSEH", "ALTMIRE",
    "SUASTEGUI", "GHANTA", "MOUSTIS", "SORSABAL", "ERTEL", "SHADEGG", "TOPRANI", "AKHIL", "SARKODIEH",
    "KURT", "SERIBUTRA", "KEITAZULU", "SETEPENRE", "YEGER", "WINUK", "KUWIK",
}

# Origin unclear from the surname alone.
UNCLEAR = {
    "MIRLISENA", "ERET", "YANIZ", "BOZAR", "DEDI", "SERIAN", "KERPANI", "SUBAK", "SUARA", "UNGAB",
    "YURDIN", "TOLKAN", "BARYAB", "KONIZ", "OSLAN", "SELEN", "DENESHA", "UNTAL", "LESTITIAN", "YASMINE",
    "BABADLIR", "YALKUT", "CHOULAGH", "BOUDI", "BILICIH", "SIADEK", "BASTUK", "ASTAFAN",
}


def main() -> None:
    df = pd.read_parquet(PROCESSED / "candidates_scored.parquet", columns=["surname", "p_muslim"])
    flagged = (df[df["p_muslim"] > THRESHOLD].groupby("surname")
               .agg(candidates=("surname", "size"), p_muslim=("p_muslim", "first"))
               .sort_values("p_muslim", ascending=False).reset_index())
    flagged["decision"] = "keep"
    flagged.loc[flagged["surname"].isin(UNCLEAR), "decision"] = "strike: unclear origin"
    flagged.loc[flagged["surname"].isin(NOT_MENA), "decision"] = "strike: other origin"
    flagged.round(3).to_csv(DOCS / "mena_name_review.csv", index=False)
    print(flagged["decision"].value_counts().to_string())
    unknown = (NOT_MENA | UNCLEAR) - set(flagged["surname"])
    if unknown:
        print("Warning, struck names not in the flagged list:", sorted(unknown))


if __name__ == "__main__":
    main()
