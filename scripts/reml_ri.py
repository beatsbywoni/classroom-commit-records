#!/usr/bin/env python3
"""Random-intercept linear mixed model by REML, vectorized over groups (independent of statsmodels).

Model: y = X b + u_g + e,  u_g ~ N(0, s_u^2),  e ~ N(0, s^2).  With gamma = s_u^2 / s^2, the covariance of group g
is s^2 (I + gamma 11'), whose inverse is (I - c_g 11') / s^2 with c_g = gamma / (1 + n_g gamma). All quantities
needed by REML reduce to per-group sums, so one likelihood evaluation costs O(n p^2).

Profiled REML log-likelihood (s^2 profiled out):
  l(gamma) = -0.5 [ (n-p)(log 2 pi + log s2hat + 1) + sum_g log(1 + n_g gamma) + log det(X' W X) ]
with W = s^2 V^{-1} and s2hat = r' W r / (n - p). gamma is optimized over [0, inf) on the log scale with a bounded
Brent search, and the boundary gamma = 0 is checked explicitly. Standard errors of b are
s2hat * (X' W X)^{-1} evaluated at gamma-hat (the usual REML plug-in covariance).
"""
import numpy as np
from scipy.optimize import minimize_scalar

def _group_sums(codes, G, A):
    out = np.zeros((G,) + A.shape[1:]); np.add.at(out, codes, A); return out

def fit(y, X, groups, log_gamma_bounds=(-12.0, 12.0)):
    y = np.asarray(y, float); X = np.asarray(X, float)
    codes = np.unique(np.asarray(groups), return_inverse=True)[1]
    G = codes.max() + 1; n, p = X.shape
    ng = np.bincount(codes, minlength=G).astype(float)
    Sx = _group_sums(codes, G, X); Sy = _group_sums(codes, G, y)
    XtX = X.T @ X; Xty = X.T @ y; yty = y @ y
    def parts(gamma):
        c = gamma / (1.0 + ng * gamma)
        XWX = XtX - (Sx * c[:, None]).T @ Sx
        XWy = Xty - (Sx * c[:, None]).T @ Sy
        yWy = yty - np.sum(c * Sy * Sy)
        b = np.linalg.solve(XWX, XWy)
        rWr = yWy - b @ XWy
        s2 = rWr / (n - p)
        sign, logdet = np.linalg.slogdet(XWX)
        ll = -0.5 * ((n - p) * (np.log(2 * np.pi) + np.log(s2) + 1.0) + np.sum(np.log1p(ng * gamma)) + logdet)
        return ll, b, s2, XWX
    obj = lambda lg: -parts(np.exp(lg))[0]
    res = minimize_scalar(obj, bounds=log_gamma_bounds, method="bounded", options={"xatol": 1e-9, "maxiter": 500})
    g_hat = float(np.exp(res.x)); ll_hat = -float(res.fun)
    ll0 = parts(0.0)[0]
    if ll0 >= ll_hat: g_hat, ll_hat = 0.0, ll0
    ll, b, s2, XWX = parts(g_hat)
    cov = s2 * np.linalg.inv(XWX)
    return {"beta": b, "se": np.sqrt(np.diag(cov)), "cov": cov, "sigma2": float(s2), "sigma2_u": float(g_hat * s2), "gamma": g_hat, "llf": float(ll), "n": n, "groups": int(G)}

def design(df, label_cols, num_covs=("log_commits", "n_authors_human"), factors=("lang_family",), levels=None):
    """Intercept, label columns, numeric covariates, treatment-coded factors. `levels` maps factor -> ordered levels
    (first = reference); columns for levels absent from `df` are dropped so that X keeps full column rank."""
    cols = [np.ones(len(df))]; names = ["Intercept"]
    for c in label_cols: cols.append(df[c].to_numpy(float)); names.append(c)
    for c in num_covs: cols.append(df[c].to_numpy(float)); names.append(c)
    for fac in factors:
        lv = (levels or {}).get(fac) or sorted(df[fac].astype(str).unique())
        f = df[fac].astype(str).to_numpy()
        for l in lv[1:]:
            col = (f == l).astype(float)
            if col.sum() > 0 and col.sum() < len(col): cols.append(col); names.append(f"{fac}[{l}]")
    return np.column_stack(cols), names
