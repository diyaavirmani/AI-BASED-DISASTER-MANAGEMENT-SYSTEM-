# NDVI, NDWI, NBR calculators
import numpy as np

def compute_ndvi(red_band, nir_band):
    """
    Normalized Difference Vegetation Index
    Formula: (NIR - Red) / (NIR + Red)
    Range: -1 to +1
    """
    red = red_band.astype(np.float32)
    nir = nir_band.astype(np.float32)
    
    denominator = nir + red
    
    ndvi = np.where(
        denominator != 0,
        (nir - red) / denominator,
        0.0
    )
    
    return np.clip(ndvi, -1.0, 1.0)


def compute_ndwi(green_band, nir_band):
    """
    Normalized Difference Water Index
    Formula: (Green - NIR) / (Green + NIR)
    Range: -1 to +1
    """
    green = green_band.astype(np.float32)
    nir   = nir_band.astype(np.float32)
    
    denominator = green + nir
    
    ndwi = np.where(
        denominator != 0,
        (green - nir) / denominator,
        0.0
    )
    
    return np.clip(ndwi, -1.0, 1.0)


def compute_nbr(nir_band, swir_band):
    """
    Normalized Burn Ratio
    Formula: (NIR - SWIR) / (NIR + SWIR)
    Range: -1 to +1
    """
    nir  = nir_band.astype(np.float32)
    swir = swir_band.astype(np.float32)
    
    denominator = nir + swir
    
    nbr = np.where(
        denominator != 0,
        (nir - swir) / denominator,
        0.0
    )
    
    return np.clip(nbr, -1.0, 1.0)


def compute_ndbi(swir_band, nir_band):
    """
    Normalized Difference Built-up Index
    Formula: (SWIR - NIR) / (SWIR + NIR)
    Range: -1 to +1
    """
    swir = swir_band.astype(np.float32)
    nir  = nir_band.astype(np.float32)
    
    denominator = swir + nir
    
    ndbi = np.where(
        denominator != 0,
        (swir - nir) / denominator,
        0.0
    )
    
    return np.clip(ndbi, -1.0, 1.0)