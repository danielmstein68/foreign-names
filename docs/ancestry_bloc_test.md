# Ancestry-bloc test for white ethnic names (written 2026-10-24, before any ancestry data was loaded)

## Why this test
Daniel's explanation for the Hansen penalty: every unfamiliar-sounding name loses some votes from voters who don't share it.
- Non-white groups have voting blocs that can offset this. The co-ethnic test supports that part.
- White ethnic groups (German, Scandinavian, Italian, Polish Americans) mostly don't vote as blocs, so their penalty is never offset.

**Prediction:** a name does better where more residents report the ancestry that matches it. Hansen should do better in heavily Scandinavian places than elsewhere. If white ethnics have no bloc at all, there is no such pattern.

**This is exploratory:** it was added after the main and co-ethnic results were seen.

## Data
- **Source:** Census American Community Survey 5-year 2006–2010, table B04006 ("people reporting ancestry"), divided by total population (B01003).
- **Places:** counties for county races, cities ("places") for city races.
- **Time:** one snapshot for all years. Ancestry composition changes slowly, and this is the earliest ACS 5-year release.
- **Sample:** local races only, the same main sample as step 5. School boards drop out, as before.

## Matching name groups (ethnicolr) to ancestries (ACS)
| ethnicolr group | ACS ancestries counted |
|---|---|
| British | English, British, Scottish, Scotch-Irish, Irish, Welsh, Celtic |
| Germanic | German, Austrian, Dutch, Swiss, Luxemburger, Pennsylvania German, German Russian, Alsatian |
| Nordic | Norwegian, Swedish, Danish, Finnish, Icelander, Scandinavian |
| French | French (except Basque), French Canadian, Cajun, Belgian |
| Italian | Italian, Maltese |
| EastEuropean | Polish, Czech, Czechoslovakian, Slovak, Hungarian, Russian, Ukrainian, Lithuanian, Latvian, Estonian, Croatian, Serbian, Slovene, Slavic, Romanian, Bulgarian, Greek, Macedonian, Albanian, Carpatho Rusyn, Eastern European, Yugoslavian, Soviet Union |

Not covered: Hispanic, Asian, African and Jewish origins. The ancestry table doesn't measure them well, and the co-ethnic test already covers the first three.

## Measures
- **`match`** = the sum over the 6 groups of (probability the name is from group g) × (share of residents reporting ancestry g). This is roughly "the share of residents who share this name's origin".
- **`match_nonbrit`** = the same sum over the 5 non-British groups. **`match_brit`** = the British term alone.

## Models, fixed before seeing the data
Same within-race model as step 5 (contest fixed effects, clustered by jurisdiction), local nonpartisan, local partisan and all local. The co-ethnic terms from the co-ethnic test are included, so this measures something on top of co-ethnic voting by non-white groups.

**Model 1:** `vote share = hispanic + black + api + foreign + co-ethnic interactions + match + controls + contest FE`
- **Prediction:** `match` is **positive**.

**Model 2 (the Hansen test):** the same, with `match` split into `match_nonbrit` and `match_brit`.
- **Prediction:** `match_nonbrit` is **positive**. White ethnic names do better where their ancestry group is common.

**Model 3 (intuitive version):**
- Take the "white & foreign" candidates and their most likely origin group (Germanic, Nordic, French, Italian or EastEuropean).
- Split them into thirds by the local share of residents with that ancestry.
- Compare each third with "white & not foreign" in the same race.
- **Prediction:** the penalty shrinks or disappears in the top third.

## What would count against the bloc explanation
- `match_nonbrit` near zero or negative.
- A white & foreign penalty that doesn't shrink where the matching ancestry is common. That would point to a general "unfamiliar name" effect with no offsetting bloc.
