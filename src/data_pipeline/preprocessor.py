# src/data_pipeline/preprocessor.py
# KEY SECTION — the preprocess_for_inference() function
# This is what runs on LIVE satellite images from Planet/GEE

import numpy as np
import rasterio
import cv2
from scipy.ndimage import uniform_filter
from pathlib import Path


# ── These MUST match Colab exactly ───────────────────────────

def normalize_channel(ch, method='minmax'):
    """
    Normalize a 2D array.
    MUST match the normalization used during Colab training.
    Optical → minmax, SAR → zscore
    """
    ch = ch.astype(np.float32)
    if method == 'minmax':
        mn, mx = np.nanmin(ch), np.nanmax(ch)
        if mx > mn:
            return (ch - mn) / (mx - mn)
        return np.zeros_like(ch)
    elif method == 'zscore':
        mu = np.nanmean(ch)
        sigma = np.nanstd(ch)
        if sigma > 0:
            return np.clip((ch - mu) / sigma, -3, 3) / 6 + 0.5
        return np.full_like(ch, 0.5)
    return ch


def compute_ndvi(red, nir):
    d = nir + red
    return np.clip(np.where(d > 0, (nir - red) / d, 0.0), -1.0, 1.0)

def compute_ndwi(green, nir):
    d = green + nir
    return np.clip(np.where(d > 0, (green - nir) / d, 0.0), -1.0, 1.0)

def compute_nbr(nir, swir):
    d = nir + swir
    return np.clip(np.where(d > 0, (nir - swir) / d, 0.0), -1.0, 1.0)

def compute_sar_coherence(vv, vh, window=5):
    a = vv.astype(np.complex64)
    b = vh.astype(np.complex64)
    cross = uniform_filter(np.abs(a * np.conj(b)), size=window)
    pa    = uniform_filter(np.real(a * np.conj(a)), size=window)
    pb    = uniform_filter(np.real(b * np.conj(b)), size=window)
    denom = np.sqrt(pa * pb)
    coh   = np.where(denom > 0, cross / denom, 0.0)
    return np.clip(np.abs(coh), 0.0, 1.0).astype(np.float32)


def build_9channel_input(optical_array, sar_array, target_hw=512):
    """
    Converts raw optical + SAR arrays into the exact 9-channel
    input format the trained model expects.

    CHANNEL LAYOUT (must match Colab training exactly):
      ch 0: R          (optical, minmax normalized)
      ch 1: G          (optical, minmax normalized)
      ch 2: B          (optical, minmax normalized)
      ch 3: VV_SAR     (SAR, zscore normalized)
      ch 4: VH_SAR     (SAR, zscore normalized)
      ch 5: NDVI       (rescaled to [0,1])
      ch 6: NDWI       (rescaled to [0,1])
      ch 7: NBR        (rescaled to [0,1])
      ch 8: Coherence  ([0,1])

    Args:
      optical_array: (H, W, 3+) numpy array — RGB from Sentinel-2 or Planet
      sar_array:     (H, W, 2)  numpy array — VV, VH from Sentinel-1
                     Pass None if SAR unavailable — filled with zeros
      target_hw:     resize to this square size

    Returns:
      stacked: (target_hw, target_hw, 9) float32  values in [0,1]
    """

    H = target_hw

    # ── Resize optical to target_hw ───────────────────────────
    opt = optical_array.astype(np.float32)
    if opt.ndim == 2:
        opt = np.stack([opt, opt, opt], axis=-1)
    opt = opt[:, :, :3]  # Keep only RGB

    if opt.shape[0] != H or opt.shape[1] != H:
        opt = cv2.resize(opt, (H, H), interpolation=cv2.INTER_LINEAR)

    # ── Resize SAR or create zeros ────────────────────────────
    if sar_array is not None:
        sar = sar_array.astype(np.float32)
        if sar.ndim == 2:
            sar = np.stack([sar, sar], axis=-1)
        sar = sar[:, :, :2]
        if sar.shape[0] != H or sar.shape[1] != H:
            sar = np.stack([
                cv2.resize(sar[:,:,c], (H,H), interpolation=cv2.INTER_LINEAR)
                for c in range(2)
            ], axis=-1)
    else:
        # No SAR available — fill with zeros
        # Model learned to handle this from training
        sar = np.zeros((H, H, 2), dtype=np.float32)

    # ── Normalize optical (minmax per channel) ────────────────
    opt_norm = np.stack([
        normalize_channel(opt[:,:,c], 'minmax') for c in range(3)
    ], axis=-1)

    # ── Normalize SAR (zscore per channel) ───────────────────
    sar_norm = np.stack([
        normalize_channel(sar[:,:,c], 'zscore') for c in range(2)
    ], axis=-1)

    # ── Spectral indices ──────────────────────────────────────
    R, G, B = opt_norm[:,:,0], opt_norm[:,:,1], opt_norm[:,:,2]
    # Approximate NIR (same approximation as Colab training)
    NIR_approx = R * 0.4 + G * 0.3 + B * 0.3

    ndvi = (compute_ndvi(R, NIR_approx) + 1) / 2
    ndwi = (compute_ndwi(G, NIR_approx) + 1) / 2
    nbr  = (compute_nbr(NIR_approx, sar_norm[:,:,0]) + 1) / 2
    coh  = compute_sar_coherence(sar_norm[:,:,0], sar_norm[:,:,1])

    # ── Stack into 9 channels ─────────────────────────────────
    stacked = np.concatenate([
        opt_norm,                       # ch 0,1,2
        sar_norm,                       # ch 3,4
        ndvi[:,:,np.newaxis],           # ch 5
        ndwi[:,:,np.newaxis],           # ch 6
        nbr[:,:,np.newaxis],            # ch 7
        coh[:,:,np.newaxis]             # ch 8
    ], axis=-1).astype(np.float32)

    return stacked


def tile_array(array, tile_size=256, overlap=32):
    """Split array into overlapping tiles. Returns tiles + positions."""
    H, W   = array.shape[:2]
    stride = tile_size - overlap
    tiles, positions = [], []
    y = 0
    while y < H:
        ys = min(y, H - tile_size)
        ye = ys + tile_size
        x  = 0
        while x < W:
            xs = min(x, W - tile_size)
            xe = xs + tile_size
            tiles.append(array[ys:ye, xs:xe])
            positions.append((ys, ye, xs, xe))
            x += stride
        y += stride
    return tiles, positions


def stitch_tiles(tile_predictions, positions,
                  full_h, full_w, num_classes=4, overlap=32):
    """
    Reassembles tile predictions into a full damage map.
    Uses centre-only regions to avoid boundary artifacts.
    """
    margin = overlap // 2
    output = np.zeros((num_classes, full_h, full_w), dtype=np.float32)
    count  = np.zeros((full_h, full_w), dtype=np.float32)

    for pred, (ys, ye, xs, xe) in zip(tile_predictions, positions):
        # pred shape: (num_classes, tile_h, tile_w)
        cy_s = ys + margin
        cy_e = ye - margin
        cx_s = xs + margin
        cx_e = xe - margin

        output[:, cy_s:cy_e, cx_s:cx_e] += \
            pred[:, margin:-margin, margin:-margin]
        count[cy_s:cy_e, cx_s:cx_e] += 1

    # Average overlapping regions
    count = np.maximum(count, 1)
    output = output / count[np.newaxis, :, :]

    return output.argmax(axis=0).astype(np.uint8)  # (H, W) damage class map
