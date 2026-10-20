"""Ladder layer price construction: fixed spacing or snapped to S/R levels. Pure numeric (numba-compatible)."""
import numpy as np

def fixed_layers(P0, sg, nl, step):
    out = np.empty(nl); p = P0
    for i in range(nl):
        if i > 0: p = p * (1 - sg * step)
        out[i] = p
    return out

def snap_layers(P0, sg, nl, step, lv, ls, min_strength=40.0, window=0.4, min_gap=0.01, extra_depth=0.5, offset=0.001):
    """Layer 1 = P0. Layer i>=2: strongest level (>= min_strength) within +-window*step of the fixed target,
    order placed `offset` in front of the level (above support for long / below resistance for short).
    Constraints: gap to previous layer >= min_gap; depth <= fixed depth + extra_depth*step. Fallback: fixed target."""
    out = np.empty(nl); out[0] = P0; prev = P0
    maxd = 1 - (1 - step) ** (nl - 1) + extra_depth * step
    snapped = np.zeros(nl)
    for i in range(1, nl):
        tgt = P0 * (1 - sg * step) ** i
        best = -1; bs = -1.0; bd = 1e9
        for j in range(lv.shape[0]):
            if ls[j] < min_strength: continue
            q = lv[j] * (1 + sg * offset)
            if sg * (1 - q / prev) < min_gap: continue
            if abs(q / tgt - 1) > window * step: continue
            if sg * (1 - q / P0) > maxd: continue
            d = abs(q / tgt - 1)
            if ls[j] > bs or (ls[j] == bs and d < bd): best = j; bs = ls[j]; bd = d
        if best >= 0:
            q = lv[best] * (1 + sg * offset); snapped[i] = 1
        else:
            q = tgt
            if sg * (1 - q / prev) < min_gap: q = prev * (1 - sg * min_gap)
        out[i] = q; prev = q
    return out, snapped
