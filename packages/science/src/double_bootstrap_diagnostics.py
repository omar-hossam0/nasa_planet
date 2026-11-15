"""Parameterized diagnostic copies; original candidate/evidence stay frozen."""
import numpy as np


def geometry(n, spec):
    low, high, step = spec
    rho = np.arange(low, high + step/100, step)
    if rho[-1] < high-1e-10:
        rho = np.r_[rho, high]
    rho[-1] = high
    x = np.column_stack([np.ones(n), np.arange(n)])
    a=[];inv=[];penalty=[]
    for r in rho:
        transform=np.eye(n)
        transform[0,0]=np.sqrt(1-r*r)
        transform[np.arange(1,n),np.arange(n-1)]=-r
        w=transform@x;g=w.T@w
        a.append(w.T@transform);inv.append(np.linalg.inv(g))
        penalty.append(-np.log(1-r*r)+np.linalg.slogdet(g)[1])
    return rho,np.array(a),np.array(inv),np.array(penalty)


def fit(y, geo):
    y=np.asarray(y,dtype=float)
    if y.ndim!=2 or not np.isfinite(y).all():raise ValueError('Complete rows required')
    rho,a,inv,penalty=geo;n=y.shape[1]
    g=np.einsum('rkn,bn->rbk',a,y,optimize=True)
    beta=np.einsum('rkl,rbl->rbk',inv,g,optimize=True)
    q=(y*y).sum(1)[None,:]+rho[:,None]**2*((y[:,:-1]**2).sum(1)-y[:,0]**2)[None,:]-2*rho[:,None]*(y[:,1:]*y[:,:-1]).sum(1)[None,:]
    sse=q-(g*beta).sum(2)
    if np.any(sse<=0):raise ValueError('Degenerate residual fit')
    objective=(n-2)*np.log(sse/(n-2))+penalty[:,None]
    index=np.argmin(objective,axis=0);cols=np.arange(len(y))
    return {'slope':beta[index,cols,1], 'se':np.sqrt(sse[index,cols]/(n-2)*inv[index,1,1]),
            'index':index,'rho':rho[index],'boundary':(index==0)|(index==len(rho)-1)}


def probabilities(stat, indices, inner, outer):
    out=np.empty(len(stat))
    for j in np.unique(indices):
        mask=indices==j
        raw=(1+len(inner[j])-np.searchsorted(inner[j],abs(stat[mask]),side='left'))/(len(inner[j])+1)
        out[mask]=(1+np.searchsorted(outer[j],raw,side='right'))/(len(outer[j])+1)
    return out


def build_cache(n, spec, seed, inner_count=1999, outer_count=999):
    from .reml_uncertainty import simulate_ar
    geo=geometry(n,spec);rho=geo[0];inner=[];outer=[];critical=[];inverted=[]
    for r in rho:
        rng=np.random.default_rng(np.random.SeedSequence([seed,301,n,int(round((r+1)*1e6))]))
        f=fit(simulate_ar(rng.normal(size=(inner_count,n)),r),geo)
        inner.append(np.sort(abs(f['slope']/f['se'])))
    for j,r in enumerate(rho):
        rng=np.random.default_rng(np.random.SeedSequence([seed,902,n,int(round((r+1)*1e6))]))
        f=fit(simulate_ar(rng.normal(size=(outer_count,n)),r),geo)
        stat=abs(f['slope']/f['se']);p=np.empty(len(stat))
        for k in np.unique(f['index']):
            mask=f['index']==k;p[mask]=(1+inner_count-np.searchsorted(inner[k],stat[mask],side='left'))/(inner_count+1)
        outer.append(np.sort(p))
        cut=outer[j][int(np.floor(.05*(len(p)+1)))-1]
        critical.append(float(np.quantile(inner[j],1-cut,method='higher')))
        raw=(1+inner_count-np.arange(inner_count))/(inner_count+1)
        cal=(1+np.searchsorted(outer[j],raw,side='right'))/(outer_count+1)
        rejected=np.flatnonzero(cal<=.05)
        inverted.append(float(inner[j][rejected[0]]) if len(rejected) else float('inf'))
    return geo,inner,outer,np.array(critical),np.array(inverted)
