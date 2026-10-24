# Co-ethnic voting test (exploratory)

Pre-specified in `docs/coethnic_test.md` before any demographic data was loaded. Exploratory: added after the main results were seen. Vote share in percentage points; 95% CIs clustered by jurisdiction; bold means p < 0.05.

## Model 1: surname share × same-group share of residents

Co-ethnic voting predicts **positive** interactions (the name does better where more residents share it) and **negative** main effects (the name's effect where none do).

|                  | Local nonpartisan          | Local partisan            | All local                  |
|:-----------------|:---------------------------|:--------------------------|:---------------------------|
| hispanic         | -0.18 [-4.10, +3.75]       | **-3.63** [-6.97, -0.30]  | -1.63 [-4.37, +1.10]       |
| black            | **-7.60** [-11.05, -4.15]  | -1.95 [-6.61, +2.70]      | **-4.37** [-6.97, -1.77]   |
| api              | -1.93 [-6.33, +2.48]       | -1.05 [-6.88, +4.77]      | -1.96 [-5.44, +1.51]       |
| foreign          | **-1.69** [-2.72, -0.66]   | -0.49 [-1.39, +0.42]      | **-1.15** [-1.85, -0.44]   |
| hispanic:pl_hisp | +3.21 [-3.68, +10.11]      | **+9.37** [+0.08, +18.66] | **+5.77** [+0.53, +11.00]  |
| black:pl_black   | **+22.15** [+8.78, +35.52] | +19.74 [-19.99, +59.46]   | **+16.30** [+3.87, +28.72] |
| api:pl_asian     | +9.19 [-2.71, +21.08]      | +8.57 [-8.29, +25.42]     | +9.53 [-0.06, +19.13]      |
| N candidates     | 34,555                     | 32,875                    | 67,430                     |

### What that implies: effect of a fully Hispanic / Black / Asian surname vs a white surname, by how much of the place shares that background

|                                                 | Local nonpartisan         | Local partisan           | All local                |
|:------------------------------------------------|:--------------------------|:-------------------------|:-------------------------|
| hispanic name where hispanic = 0% of residents  | -0.18 [-4.10, +3.75]      | **-3.63** [-6.97, -0.30] | -1.63 [-4.37, +1.10]     |
| hispanic name where hispanic = 25% of residents | +0.63 [-1.93, +3.18]      | -1.29 [-3.09, +0.50]     | -0.19 [-1.98, +1.60]     |
| hispanic name where hispanic = 50% of residents | +1.43 [-0.46, +3.32]      | +1.05 [-1.43, +3.53]     | +1.25 [-0.29, +2.79]     |
| black name where black = 0% of residents        | **-7.60** [-11.05, -4.15] | -1.95 [-6.61, +2.70]     | **-4.37** [-6.97, -1.77] |
| black name where black = 25% of residents       | -2.06 [-4.32, +0.20]      | +2.98 [-3.91, +9.87]     | -0.30 [-2.49, +1.90]     |
| black name where black = 50% of residents       | +3.48 [-1.07, +8.02]      | +7.91 [-8.53, +24.36]    | +3.78 [-0.93, +8.49]     |
| api name where api = 0% of residents            | -1.93 [-6.33, +2.48]      | -1.05 [-6.88, +4.77]     | -1.96 [-5.44, +1.51]     |
| api name where api = 25% of residents           | +0.37 [-1.97, +2.71]      | +1.09 [-2.82, +4.99]     | +0.42 [-1.61, +2.45]     |
| api name where api = 50% of residents           | +2.67 [-0.38, +5.71]      | +3.23 [-2.43, +8.89]     | **+2.80** [+0.04, +5.57] |

## Model 2: the four groups vs white & not foreign, by how diverse the place is

Places split into thirds by non-white share of residents (all local races). Co-ethnic voting predicts the **non-white & foreign** row to go from negative (least diverse) toward zero or positive (most diverse).

|                                | least diverse third (non-white 2%–23%)   | middle third (non-white 23%–40%)   | most diverse third (non-white 40%–97%)   |
|:-------------------------------|:-----------------------------------------|:-----------------------------------|:-----------------------------------------|
| white & foreign                | -0.52 [-1.33, +0.28]                     | -0.47 [-1.59, +0.65]               | -0.71 [-1.98, +0.57]                     |
| non-white & not foreign        | **-1.47** [-2.46, -0.47]                 | +0.13 [-1.02, +1.28]               | +1.40 [-0.02, +2.81]                     |
| non-white & foreign            | **-2.33** [-3.98, -0.67]                 | -1.33 [-2.70, +0.03]               | +0.88 [-0.79, +2.55]                     |
| N candidates / races           | 20,942 / 9,314                           | 22,031 / 9,313                     | 24,457 / 9,314                           |
| non-white & foreign candidates | 1,273                                    | 2,190                              | 4,909                                    |
