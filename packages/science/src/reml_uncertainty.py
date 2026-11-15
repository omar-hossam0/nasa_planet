"""Stationary Gaussian AR(1) REML research, including refitted bootstrap-t.

Finite grid approximation, not an exact continuous optimizer. All nuisance fits
are repeated for parametric replicates. No NASA data or descriptive Sen slopes
are modified. REML t alone remains a plug-in uncertainty comparator.
"""
from functools import lru_cache
import numpy as np


@lru_cache(None)
def geometry(n):
    x = np.column_stack([np.ones(n), np.arange(n)])
    rho = np.linspace(-.5, .95, 59)
    matrices=[];inverses=[];penalty=[]
    for r in rho:
        w=np.vstack([np.sqrt(1-r*r)*x[0],x[1:]-r*x[:-1]])
        # W'W precision in the innovation-variance parameterization.
        transform=np.eye(n)
        transform[0,0]=np.sqrt(1-r*r)
        transform[np.arange(1,n),np.arange(n-1)]=-r
        g=w.T@w
        matrices.append(w.T@transform);inverses.append(np.linalg.inv(g))
        penalty.append(-np.log(1-r*r)+np.linalg.slogdet(g)[1])
    return rho,np.array(matrices),np.array(inverses),np.array(penalty)


def fit_reml(values):
    """Rows are complete annual records; profile out beta and innovation scale."""
    y=np.asarray(values,dtype=float)
    if y.ndim!=2 or y.shape[1] not in (20,24) or not np.isfinite(y).all():
        raise ValueError('Requires complete 20/24-position records; no imputation')
    n=y.shape[1];rho,a,inv,penalty=geometry(n)
    g=np.einsum('rkn,bn->rbk',a,y,optimize=True)
    beta=np.einsum('rkl,rbl->rbk',inv,g,optimize=True)
    # Exact innovation quadratic form, without constructing a 3-D residual cube.
    yy=(y*y).sum(1);prev=(y[:,:-1]**2).sum(1);cross=(y[:,1:]*y[:,:-1]).sum(1)
    q=yy[None,:]+rho[:,None]**2*(prev-y[:,0]**2)[None,:]-2*rho[:,None]*cross[None,:]
    sse=q-np.sum(g*beta,axis=2)
    if np.any(sse<=0):
        # Exact constant/linear input has no empirical innovation uncertainty.
        if np.any(np.min(sse,axis=0)<=1e-12):raise ValueError('Degenerate residual record')
        raise FloatingPointError('Invalid residual quadratic')
    objective=(n-2)*np.log(sse/(n-2))+penalty[:,None]
    idx=np.argmin(objective,axis=0);col=np.arange(len(y))
    slope=beta[idx,col,1]
    se=np.sqrt(sse[idx,col]/(n-2)*inv[idx,1,1])
    return {'slope':slope,'se':se,'rho':rho[idx], 'boundary':(idx==0)|(idx==len(rho)-1)}


def simulate_ar(normals,rho):
    out=np.array(normals,copy=True);out[:,0]=normals[:,0]/np.sqrt(1-rho*rho)
    for i in range(1,out.shape[1]):out[:,i]=rho*out[:,i-1]+normals[:,i]
    return out


def refitted_t_errors(rho,n,replicates,seed):
    noise=simulate_ar(np.random.default_rng(seed).normal(size=(replicates,n)),rho)
    fit=fit_reml(noise)
    return fit['slope']/fit['se'],float(fit['boundary'].mean())
