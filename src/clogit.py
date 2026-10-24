"""A small conditional logit for "which candidate wins this race".

statsmodels' ConditionalLogit (0.15.0) failed to produce standard errors on
our data, so this is a direct implementation. In each race exactly one
candidate wins, and the probability that candidate i wins is

    P(i wins) = exp(x_i·b) / sum over candidates j in the race of exp(x_j·b)

Anything that is the same for everyone in the race (district, year, turnout)
cancels out of this ratio, just like a contest fixed effect.
Standard errors are clustered (sandwich formula), with the usual G/(G-1)
small-sample adjustment.
"""

import numpy as np
import pandas as pd
from scipy import optimize, stats


def _group_softmax(eta, starts):
    """Within-race probabilities exp(eta) / sum(exp(eta)), computed stably."""
    gmax = np.maximum.reduceat(eta, starts)
    sizes = np.diff(np.append(starts, len(eta)))
    e = np.exp(eta - np.repeat(gmax, sizes))
    denom = np.add.reduceat(e, starts)
    return e / np.repeat(denom, sizes), np.log(denom) + gmax


def fit_clogit(y, X: pd.DataFrame, groups, clusters):
    """Fit the model. y = 1 for the winner, 0 otherwise; exactly one 1 per group.

    Returns a DataFrame with coef, se, ci_low, ci_high, p (log-odds scale).
    """
    order = np.argsort(pd.factorize(groups)[0], kind="stable")
    y = np.asarray(y, float)[order]
    Xv = np.asarray(X, float)[order]
    g = pd.factorize(groups)[0][order]
    cl = pd.factorize(np.asarray(clusters)[order])[0]
    starts = np.flatnonzero(np.r_[True, g[1:] != g[:-1]])
    sizes = np.diff(np.append(starts, len(y)))
    if not np.all(np.add.reduceat(y, starts) == 1):
        raise ValueError("every group needs exactly one winner")

    def negll(b):
        eta = Xv @ b
        p, lse = _group_softmax(eta, starts)
        ll = (y * eta).sum() - lse.sum()
        xbar = np.add.reduceat(p[:, None] * Xv, starts)          # expected x in each race
        grad = (y[:, None] * Xv).sum(0) - xbar.sum(0)
        return -ll, -grad

    res = optimize.minimize(negll, np.zeros(Xv.shape[1]), jac=True, method="BFGS",
                            options={"gtol": 1e-8, "maxiter": 1000})
    b = res.x
    p, _ = _group_softmax(Xv @ b, starts)
    xbar = np.add.reduceat(p[:, None] * Xv, starts)
    centred = Xv - np.repeat(xbar, sizes, axis=0)
    H = (p[:, None] * centred).T @ centred                       # information matrix
    Hinv = np.linalg.inv(H)
    score_g = np.add.reduceat(y[:, None] * centred, starts)      # one score per race
    cl_g = cl[starts]
    S = pd.DataFrame(score_g).groupby(cl_g).sum().values         # summed by cluster
    G = S.shape[0]
    V = Hinv @ (S.T @ S) @ Hinv * G / (G - 1)
    se = np.sqrt(np.diag(V))
    t = stats.t.ppf(0.975, G - 1)
    return pd.DataFrame({"coef": b, "se": se, "ci_low": b - t * se, "ci_high": b + t * se,
                         "p": 2 * stats.t.sf(np.abs(b / se), G - 1),
                         # converged: the gradient is ~0 at the solution
                         "converged": np.max(np.abs(res.jac)) < 1e-3},
                        index=X.columns)
