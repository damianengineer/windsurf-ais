import numpy as np

def fit_circle(xs, ys):
    """
    Algebraic circle fit (Kasa method).
    Returns (xc, yc, r, residuals)
    """
    x = np.array(xs)
    y = np.array(ys)
    A = np.c_[2*x, 2*y, np.ones_like(x)]
    b = x**2 + y**2
    c, resid, _, _ = np.linalg.lstsq(A, b, rcond=None)
    xc, yc, d = c
    r = np.sqrt(xc**2 + yc**2 + d)
    residuals = np.sqrt(np.mean((np.sqrt((x-xc)**2 + (y-yc)**2) - r)**2))
    return xc, yc, r, residuals
