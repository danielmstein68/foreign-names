# Foreign coding rule

**Status:** fixed on 2026-10-24, before any vote outcome was loaded or looked at. Do not edit this after results are seen. If a change is unavoidable, add a dated note below explaining why, and keep the original rule as the main specification.

## Classifier
- **Package:** ethnicolr 2.0.0, function `estimate_wikipedia_surname`.
  - It is the surname-only Wikipedia model, with 13 categories.
  - It is trained on the 2009 Ambekar et al. Wikipedia names merged with 2026 Wikidata.
- **Surname only in the main spec,** so it uses the same input as the Census whiteness score. The full-name model (`estimate_wikipedia_full_name`) is a robustness check only.
- **How labels were assigned:** in ethnicolr's Wikidata mapping, a person's country of citizenship decides their category. Checked mappings:
  - Ireland → `GreaterEuropean,British`
  - UK → `GreaterEuropean,British`
  - Poland → `GreaterEuropean,EastEuropean`
  - Greece → `GreaterEuropean,EastEuropean`
  - Portugal → `GreaterEuropean,WestEuropean,Hispanic`

## Categories and coding

| ethnicolr category | Main spec | Sensitivity spec |
|---|---|---|
| GreaterEuropean,British (incl. Irish) | not foreign | not foreign |
| GreaterEuropean,WestEuropean,Germanic | **foreign** | not foreign |
| GreaterEuropean,WestEuropean,French | **foreign** | not foreign |
| GreaterEuropean,WestEuropean,Nordic | **foreign** | not foreign |
| GreaterEuropean,WestEuropean,Italian | foreign | foreign |
| GreaterEuropean,WestEuropean,Hispanic | foreign | foreign |
| GreaterEuropean,EastEuropean (incl. Greek) | foreign | foreign |
| GreaterEuropean,Jewish | foreign | foreign |
| Asian,GreaterEastAsian,EastAsian | foreign | foreign |
| Asian,GreaterEastAsian,Japanese | foreign | foreign |
| Asian,IndianSubContinent | foreign | foreign |
| GreaterAfrican,Africans | foreign | foreign |
| GreaterAfrican,Muslim | foreign | foreign |

**Why the main spec is coded this way:** this is the default the spec sets. "Foreign" means anything outside the Anglo/British/Irish group, which is the dominant surname tradition in U.S. politics.

**Why the sensitivity spec is coded this way:** German, French and Scandinavian surnames have been common in the U.S. for 150+ years. Voters may not hear them as foreign at all.
- Italian, Hispanic and Eastern European names stay foreign. The spec names "Western/Northern European" only, and these groups arrived later or are more often perceived as ethnic.
- Hispanic counts as foreign even though ethnicolr groups it under WestEuropean.

## Score definitions
- **foreign (continuous, main):** the probability of every non-British category added up, which equals 1 − P(British). Under the sensitivity rule it is 1 − P(British + Germanic + French + Nordic).
- **foreign (binary, robustness):** 1 if the model's single most likely category is coded foreign.
- **nonwhite (continuous, main):** 1 − pctwhite/100, from the Census 2010 surname file.
  - Hispanic, API and Black shares are also kept separately for the split model.
- **High/low cells at the checkpoint:** terciles of each continuous score, computed on the pooled candidate sample. Cells are top tercile vs bottom two terciles, plus a check using the top vs bottom tercile.

## Known weaknesses (stated, not fixed)
- The model's categories reflect Wikipedia/Wikidata citizenship, not U.S. voters' perceptions.
- Black Americans with English-origin surnames (Washington, Jackson) should be coded "not foreign". That is intended: they are the "non-white but not foreign" cell.
