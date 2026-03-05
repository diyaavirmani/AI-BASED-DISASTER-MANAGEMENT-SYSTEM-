# NDVI, NDWI, NBR calculators
import numpy as np
    
import rasterio
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

from src.data_pipeline.preprocessor import load_geotiff


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

def compute_delta_index(pre_index, post_index):
    """
    Computes change between pre and post disaster index.
    Negative values = loss (vegetation gone, water gone)
    Positive values = gain (new water = flooding, new bare soil)
    """
    pre  = pre_index.astype(np.float32)
    post = post_index.astype(np.float32)
    
    delta = post - pre
    
    # Delta inherits the range of the parent index
    # NDVI delta: -2 to +2 (difference of two -1 to +1 values)
    # Clip to meaningful range
    return np.clip(delta, -2.0, 2.0)

def compute_all_indices(pre_bands, post_bands):
    """
    Computes all spectral indices for pre and post disaster.
    
    pre_bands and post_bands are dicts:
    {
        'red':   2D numpy array,
        'nir':   2D numpy array,
        'green': 2D numpy array,
        'swir':  2D numpy array
    }
    
    Returns a dict of all computed index arrays.
    """
    
    # ── Pre-disaster indices ─────────────────────────────
    ndvi_pre = compute_ndvi(pre_bands['red'],   pre_bands['nir'])
    ndwi_pre = compute_ndwi(pre_bands['green'], pre_bands['nir'])
    nbr_pre  = compute_nbr( pre_bands['nir'],   pre_bands['swir'])
    ndbi_pre = compute_ndbi(pre_bands['swir'],  pre_bands['nir'])
    
    # ── Post-disaster indices ────────────────────────────
    ndvi_post = compute_ndvi(post_bands['red'],   post_bands['nir'])
    ndwi_post = compute_ndwi(post_bands['green'], post_bands['nir'])
    nbr_post  = compute_nbr( post_bands['nir'],   post_bands['swir'])
    ndbi_post = compute_ndbi(post_bands['swir'],  post_bands['nir'])
    
    # ── Delta indices (change = post minus pre) ──────────
    delta_ndvi = compute_delta_index(ndvi_pre, ndvi_post)
    delta_ndwi = compute_delta_index(ndwi_pre, ndwi_post)
    delta_nbr  = compute_delta_index(nbr_pre,  nbr_post)
    delta_ndbi = compute_delta_index(ndbi_pre, ndbi_post)
    
    return {
        # Pre-disaster state
        "ndvi_pre":   ndvi_pre,
        "ndwi_pre":   ndwi_pre,
        "nbr_pre":    nbr_pre,
        "ndbi_pre":   ndbi_pre,
        
        # Post-disaster state
        "ndvi_post":  ndvi_post,
        "ndwi_post":  ndwi_post,
        "nbr_post":   nbr_post,
        "ndbi_post":  ndbi_post,
        
        # Change signals (most important for model)
        "delta_ndvi": delta_ndvi,
        "delta_ndwi": delta_ndwi,
        "delta_nbr":  delta_nbr,
        "delta_ndbi": delta_ndbi,
    }
    


def save_index_as_geotiff(index_array, reference_meta, output_path):
    """
    Saves a computed index as a GeoTIFF file.
    Reuses spatial metadata from the original satellite image
    so the index map is georeferenced — it knows where on 
    Earth it is.
    """
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Build metadata for the output file
    # Start from reference and update for our single-band float output
    out_meta = reference_meta.copy()
    out_meta.update({
        "driver": "GTiff",      # file format
        "dtype":  "float32",    # our index values are float
        "count":  1,            # single band (one index)
        "compress": "lzw"       # compression — reduces file size ~3x
    })
    
    # Ensure array is float32 and 2D
    index_array = index_array.astype(np.float32)
    
    # Rasterio expects (bands, height, width) shape
    # Our index is (height, width) — add band dimension
    if index_array.ndim == 2:
        index_array = index_array[np.newaxis, :, :]  
        # Shape becomes (1, height, width)
    
    with rasterio.open(output_path, 'w', **out_meta) as dst:
        dst.write(index_array)
    
    print(f"Saved: {output_path} | Shape: {index_array.shape} | "
          f"Range: [{index_array.min():.3f}, {index_array.max():.3f}]")
    
    return output_path



ndvi, _ = load_geotiff("data/indices/turkey_eq/ndvi_post.tif")
ndvi_2d = ndvi[0]  # remove band dimension → (H, W)

# Use a diverging colormap: red=low/damaged, green=healthy
plt.figure(figsize=(12, 8))
plt.imshow(
    ndvi_2d,
    cmap='RdYlGn',       # Red → Yellow → Green
    vmin=-0.2,
    vmax=0.8
)
plt.colorbar(label='NDVI value')
plt.title('NDVI Post-Disaster — Turkey Earthquake 2023')
plt.show()
