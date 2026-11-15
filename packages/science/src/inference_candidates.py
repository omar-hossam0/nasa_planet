"""Two isolated research candidates; no NASA selection or release promotion."""
import numpy as np
from scipy.stats import norm, rankdata, t as student
from .trend_estimation import annual_elapsed_years


def validate(y, years):
    x = annual_elapsed_years(years)
    y = np.asarray(y, dtype=float)
    if y.ndim != 1 or y.shape != x.shape or np.isinf(y).any():
        raise ValueError("Invalid annual inputs")
    if len(y) < 20 or not np.isfinite(y).all() or not np.all(np.diff(x) == 1):
        return None
    return x, y


def adjusted_mk(y, years):
    data = validate(y, years)
    if data is None:
        return {"status":"insufficient_data", "p":None, "interval":None}
    x, y = data
    n = len(y)
    i, j = np.triu_indices(n, 1)
    pairs = np.sort((y[j]-y[i])/(x[j]-x[i]))
    slope = float(np.median(pairs))
    s = float(np.sign(y[j]-y[i]).sum())
    counts = np.unique(y, return_counts=True)[1]
    variance = (n*(n-1)*(2*n+5)-np.sum(counts*(counts-1)*(2*counts+5)))/18
    if variance == 0:
        return {"status":"no_variation", "slope":slope, "p":None, "interval":None}
    ranks = rankdata(y-slope*x)
    ranks -= ranks.mean()
    denominator = ranks @ ranks
    correction = 0.
    for lag in range(1, n//4+1):
        rho = float(ranks[lag:] @ ranks[:-lag] / denominator) if denominator else 0.
        if abs(rho) > 1.959963984540054/np.sqrt(n):
            correction += (n-lag)*(n-lag-1)*(n-lag-2)*rho
    factor = max(1., 1 + 2*correction/(n*(n-1)*(n-2)))
    variance *= factor
    z = (s-np.sign(s))/np.sqrt(variance)
    width = norm.ppf(.975)*np.sqrt(variance)
    lo = int(np.clip(np.floor((len(pairs)-width)/2), 0, len(pairs)-1))
    hi = int(np.clip(np.ceil((len(pairs)+width)/2), 0, len(pairs)-1))
    return {"status":"candidate", "slope":slope, "p":float(2*norm.sf(abs(z))),
            "interval":[float(pairs[lo]),float(pairs[hi])], "variance_factor":factor,
            "estimand":"Sen pairwise median", "release":False}


def gls_fixed_rho(y, x, rho):
    design = np.column_stack([np.ones(len(x)), x])
    scale = np.sqrt(1-rho*rho)
    a = np.vstack([scale*design[0], design[1:]-rho*design[:-1]])
    b = np.r_[scale*y[0], y[1:]-rho*y[:-1]]
    beta = np.linalg.lstsq(a,b,rcond=None)[0]
    residual = b-a@beta
    return beta, residual, np.linalg.inv(a.T@a)


def ar1_regression(y, years):
    data = validate(y, years)
    if data is None:
        return {"status":"insufficient_data", "p":None, "interval":None}
    x,y = data
    if np.ptp(y)==0:
        return {"status":"no_variation", "p":None, "interval":None}
    rho = 0.
    converged = False
    for iteration in range(50):
        beta, _, _ = gls_fixed_rho(y,x,rho)
        residual = y-beta[0]-beta[1]*x
        denominator = residual[:-1]@residual[:-1]
        new = float(np.clip(residual[1:]@residual[:-1]/denominator,-.95,.95)) if denominator else 0.
        if abs(new-rho)<1e-7:
            rho=new
            converged=True
            break
        rho=new
    beta,residual,cov = gls_fixed_rho(y,x,rho)
    df = len(y)-3
    se = float(np.sqrt((residual@residual)/df*cov[1,1]))
    if se <= np.finfo(float).eps:
        return {"status":"no_residual_variation", "p":None,"interval":None}
    critical = student.ppf(.975,df)
    return {"status":"candidate" if converged else "nonconverged", "slope":float(beta[1]),
            "p":float(2*student.sf(abs(beta[1]/se),df)),
            "interval":[float(beta[1]-critical*se),float(beta[1]+critical*se)],
            "rho":rho,"iterations":iteration+1,"estimand":"linear conditional-mean regression coefficient",
            "release":False}
