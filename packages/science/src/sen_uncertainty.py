"""Sen-centered research pivots; no claim of finite-sample validity by default."""
import numpy as np
from .trend_estimation import sen_slopes


def sen_pivot(y):
    y=np.asarray(y,dtype=float)
    if y.ndim!=2 or y.shape[1]<3 or not np.isfinite(y).all():
        raise ValueError('Requires complete equally spaced records')
    x=np.arange(y.shape[1],dtype=float)
    slope=sen_slopes(y.T,x)['slope']
    residual=y-slope[:,None]*x
    scale=np.median(abs(residual-np.median(residual,axis=1)[:,None]),axis=1)
    if np.any(scale<=1e-12):raise ValueError('Degenerate residual scale')
    return slope,scale


def calibrated_sen(y,grid,distributions,rho_hat=None):
    slope,scale=sen_pivot(y);stat=abs(slope/scale)
    p=np.stack([(1+len(d)-np.searchsorted(d,stat,side='left'))/(len(d)+1) for d in distributions])
    critical=np.array([np.quantile(d,.95,method='higher') for d in distributions])
    if rho_hat is None:
        probability=p.max(axis=0);q=np.full(len(y),critical.max())
    else:
        idx=np.argmin(abs(np.asarray(grid)[:,None]-np.asarray(rho_hat)[None,:]),axis=0)
        probability=p[idx,np.arange(len(y))];q=critical[idx]
    return {'slope':slope,'scale':scale,'p':probability,'radius':q*scale}


def subsampling_sen(y,fraction):
    slope,_=sen_pivot(y);n=y.shape[1];b=int(np.floor(fraction*n))
    if b<3 or b>=n:raise ValueError('Invalid subsample size')
    block_slopes=np.stack([sen_slopes(y[:,start:start+b].T,np.arange(b))['slope'] for start in range(n-b+1)],axis=1)
    # Fixed-year slope convergence rate n^(3/2), not the sample-mean sqrt(n).
    errors=(block_slopes-slope[:,None])*(b/n)**1.5
    radius=np.quantile(abs(errors),.95,axis=1,method='higher')
    p=(abs(errors)>=abs(slope[:,None])).mean(axis=1)
    return {'slope':slope,'p':p,'radius':radius,'blocks':n-b+1,'block_size':b}
