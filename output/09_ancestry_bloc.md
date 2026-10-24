# Ancestry-bloc test (exploratory)

Pre-specified in `docs/ancestry_bloc_test.md` before any ancestry data was loaded. Exploratory: added after the main results were seen. Vote share in percentage points; 95% CIs clustered by jurisdiction; bold means p < 0.05. All models include the co-ethnic terms from step 8.

## Model 1: does a name do better where more residents share its origin?

`match` is roughly the share of residents whose ancestry matches the name's origin (0-1). The bloc explanation predicts a **positive** coefficient. A coefficient of +10 means a name gains 1 point for every 10 percentage points more residents sharing its origin.

|              | Local nonpartisan     | Local partisan            | All local            |
|:-------------|:----------------------|:--------------------------|:---------------------|
| match        | +1.98 [-7.22, +11.17] | **+6.86** [+1.20, +12.52] | +4.31 [-0.82, +9.44] |
| N candidates | 34,092                | 32,875                    | 66,967               |

## Model 2: white ethnic origins vs British origin

Prediction: **match_nonbrit positive**, meaning German, Nordic, French, Italian and Eastern European names do better where their ancestry is common.

|               | Local nonpartisan     | Local partisan            | All local             |
|:--------------|:----------------------|:--------------------------|:----------------------|
| match_nonbrit | +0.28 [-9.09, +9.65]  | **+6.85** [+0.39, +13.31] | +4.54 [-0.81, +9.89]  |
| match_brit    | +4.06 [-8.39, +16.51] | +6.87 [-2.84, +16.58]     | +3.91 [-4.02, +11.84] |
| N candidates  | 34,092                | 32,875                    | 66,967                |

## Model 3: white & foreign candidates vs white & not foreign, by local share of their own ancestry

All local races. Prediction: the penalty shrinks or disappears in the high group.

|                                           | effect vs white & not foreign   |   candidates |
|:------------------------------------------|:--------------------------------|-------------:|
| low (own ancestry 0%–8% of residents)     | **-1.69** [-2.72, -0.65]        |        4,323 |
| mid (own ancestry 8%–20% of residents)    | -0.83 [-1.79, +0.13]            |        4,372 |
| high (own ancestry 20%–100% of residents) | +0.67 [-0.18, +1.53]            |        4,252 |

**Caution:** these thirds mix up origin groups (candidates per group and third below), so Model 3 alone cannot separate a bloc effect from differences between groups. See Model 4.

| own_group    |   low |   mid |   high |
|:-------------|------:|------:|-------:|
| easteuropean |   509 |   695 |    172 |
| french       |  1027 |   111 |    179 |
| germanic     |   567 |  2095 |   3311 |
| italian      |  1333 |  1129 |    493 |
| nordic       |   887 |   342 |     97 |

## Model 4: within each origin group (added after seeing Model 3)

Each white & foreign origin group gets its own baseline (its effect vs white & not foreign where nobody shares its ancestry), and the slope is estimated from how the *same* group does in places where more residents share its ancestry. Prediction: a **positive** slope.

One slope for all five groups:

|                 | estimate                   |
|:----------------|:---------------------------|
| wf_germanic     | **-2.83** [-4.16, -1.50]   |
| wf_nordic       | -1.02 [-2.60, +0.57]       |
| wf_french       | **-1.97** [-3.59, -0.35]   |
| wf_italian      | -1.37 [-2.84, +0.10]       |
| wf_easteuropean | **-3.33** [-5.01, -1.65]   |
| wf_any_x_anc    | **+10.56** [+5.93, +15.19] |

A separate slope per group:

|                 | slope on own-ancestry share   |
|:----------------|:------------------------------|
| wf_germanic     | **+9.72** [+3.69, +15.74]     |
| wf_nordic       | +11.76 [-4.84, +28.36]        |
| wf_french       | +8.99 [-7.69, +25.66]         |
| wf_italian      | **+14.05** [+0.79, +27.31]    |
| wf_easteuropean | +12.16 [-8.00, +32.32]        |
