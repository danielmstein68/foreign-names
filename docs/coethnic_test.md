# Co-ethnic voting test (written 2026-10-24, before any demographic data was loaded)

## Why this test
The main results surprised us:
- White-coded foreign names (Hansen) lose 1–2 points to a Smith in nonpartisan local races.
- Non-white foreign names (Garcia, Lee) do about as well as a Smith.

One explanation is **co-ethnic voting**. Hispanic, Black or Asian candidates may gain votes from voters of their own group and lose votes from others. If such candidates run mostly where their group is a large share of the electorate, the gain and the loss could average out to about zero. White-coded foreign names have no comparable voting bloc.

**This analysis was added after the main results were seen. It is exploratory and must be labelled that way in the write-up.**

## Data
- **Place demographics:** HKS's own historical demographics files (NHGIS decennial Census plus ACS), at the city level for city races and the county level for county races.
- **Time:** each race is matched to the nearest available year.
- **Place shares used:** Hispanic, Black, Asian and white (non-Hispanic) share of the population.
- **Sample:** local races only. HKS has no demographics for House districts, and this test is about the local results.

## Model, fixed before seeing the data
The same within-race model as step 5 (contest fixed effects, clustered by jurisdiction), on local nonpartisan and local partisan races separately and pooled:

`vote share = hispanic + black + api + foreign`
`           + hispanic × place_hispanic + black × place_black + api × place_asian`
`           + controls + contest FE`

Here, `hispanic`, `black` and `api` are the candidate's Census surname shares (0–1), and the `place_` shares are 0–1.

**What co-ethnic voting predicts:**
1. **The interactions are positive.** A Hispanic name does better the more Hispanic the place is. Same for Black and Asian.
2. **The main effects are negative.** They measure the name's effect in a place with none of that group.

**The intuitive version:** the "non-white & foreign" group's effect (vs white & not foreign, within the same race), estimated separately in places in the bottom, middle and top third of non-white population share. Co-ethnic voting predicts a penalty in the least diverse places that shrinks or reverses in the most diverse.

**The H2 side:** if Hansen's penalty also shrinks in diverse places, then something other than co-ethnic voting is going on. A general "unfamiliar name" effect would look like that.

## What would count against co-ethnic voting
- Interactions near zero or negative.
- A non-white & foreign effect that doesn't change across the three tiers.
