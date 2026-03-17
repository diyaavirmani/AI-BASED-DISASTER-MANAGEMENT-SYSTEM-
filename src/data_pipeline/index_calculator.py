"""
Spectral Indices Calculator for Disaster Assessment
Computes vegetation, water, and built-up indices from satellite bands
for pre/post-disaster change detection and damage assessment.
"""

import numpy as np
import rasterio
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import logging

from src.data_pipeline.preprocessor import load_geotiff

logger = logging.getLogger(__name__)


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
    High values = buildings, urban areas
    Low values = vegetation, water
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


def compute_ndi(nir_band, swir_band):
    """
    Normalized Difference Index (NIR-SWIR)
    Formula: (NIR - SWIR) / (NIR + SWIR)
    Range: -1 to +1
    Variant of NBR, useful for detecting thermal anomalies and burn scars.
    High values = water, vegetation
    Low values = bare soil, urban areas
    """
    nir  = nir_band.astype(np.float32)
    swir = swir_band.astype(np.float32)
    
    denominator = nir + swir
    
    ndi = np.where(
        denominator != 0,
        (nir - swir) / denominator,
        0.0
    )
    
    return np.clip(ndi, -1.0, 1.0)

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
    
    Args:
        pre_bands: Dict with keys 'red', 'nir', 'green', 'swir' (2D numpy arrays)
        post_bands: Dict with keys 'red', 'nir', 'green', 'swir' (2D numpy arrays)
    
    Returns:
        Dict of all computed index arrays and their delta (change) values.
        Delta indices highlight areas affected by disaster:
        - Negative delta = loss (vegetation destroyed, water drained)
        - Positive delta = gain (new bare soil, new flooding)
    """
    
    # ── Pre-disaster indices ─────────────────────────────
    ndvi_pre = compute_ndvi(pre_bands['red'],   pre_bands['nir'])
    ndwi_pre = compute_ndwi(pre_bands['green'], pre_bands['nir'])
    nbr_pre  = compute_nbr( pre_bands['nir'],   pre_bands['swir'])
    ndbi_pre = compute_ndbi(pre_bands['swir'],  pre_bands['nir'])
    ndi_pre  = compute_ndi( pre_bands['nir'],   pre_bands['swir'])
    
    # ── Post-disaster indices ────────────────────────────
    ndvi_post = compute_ndvi(post_bands['red'],   post_bands['nir'])
    ndwi_post = compute_ndwi(post_bands['green'], post_bands['nir'])
    nbr_post  = compute_nbr( post_bands['nir'],   post_bands['swir'])
    ndbi_post = compute_ndbi(post_bands['swir'],  post_bands['nir'])
    ndi_post  = compute_ndi( post_bands['nir'],   post_bands['swir'])
    
    # ── Delta indices (change = post minus pre) ──────────
    delta_ndvi = compute_delta_index(ndvi_pre, ndvi_post)
    delta_ndwi = compute_delta_index(ndwi_pre, ndwi_post)
    delta_nbr  = compute_delta_index(nbr_pre,  nbr_post)
    delta_ndbi = compute_delta_index(ndbi_pre, ndbi_post)
    delta_ndi  = compute_delta_index(ndi_pre,  ndi_post)
    
    logger.info("Computed all spectral indices successfully")
    
    return {
        # Pre-disaster state
        "ndvi_pre":   ndvi_pre,
        "ndwi_pre":   ndwi_pre,
        "nbr_pre":    nbr_pre,
        "ndbi_pre":   ndbi_pre,
        "ndi_pre":    ndi_pre,
        
        # Post-disaster state
        "ndvi_post":  ndvi_post,
        "ndwi_post":  ndwi_post,
        "nbr_post":   nbr_post,
        "ndbi_post":  ndbi_post,
        "ndi_post":   ndi_post,
        
        # Change signals (most important for model)
        "delta_ndvi": delta_ndvi,
        "delta_ndwi": delta_ndwi,
        "delta_nbr":  delta_nbr,
        "delta_ndbi": delta_ndbi,
        "delta_ndi":  delta_ndi,
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


# convenience function for manual experimentation
def print_index_stats(index_dict):
    """Print min/max values for each computed index."""
    for name, arr in index_dict.items():
        print(f"{name}: min={arr.min():.3f}, max={arr.max():.3f}, shape={arr.shape}")


# ═══════════════════════════════════════════════════════════════════════════
# TEST: Visualize NDVI map over vegetated area
# Green forests = bright (high NDVI ~0.7), roads/buildings = dark (~negative)
# This visual check confirms the formula is correct
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    try:
        print("=" * 80)
        print("TEST: NDVI Visualization - Spectral Index Formula Validation")
        print("=" * 80)
        
        # Load the post-disaster NDVI map
        ndvi_data, ndvi_meta = load_geotiff("data/indices/turkey_eq/ndvi_post.tif")
        ndvi_2d = ndvi_data[0]  # remove band dimension → (H, W)
        
        print(f"\nNDVI Map Statistics:")
        print(f"  Shape: {ndvi_2d.shape}")
        print(f"  Min value:  {ndvi_2d.min():.3f}")
        print(f"  Max value:  {ndvi_2d.max():.3f}")
        print(f"  Mean value: {ndvi_2d.mean():.3f}")
        print(f"  Std dev:    {ndvi_2d.std():.3f}")
        
        # ─ Visual check 1: Full NDVI map
        print("\n[1/3] Plotting full NDVI map...")
        fig, ax = plt.subplots(figsize=(14, 10))
        
        # Use diverging colormap: Red=low/damaged, Green=high/healthy vegetation
        im = ax.imshow(
            ndvi_2d,
            cmap='RdYlGn',       # Red → Yellow → Green
            vmin=-0.2,
            vmax=0.8
        )
        
        cbar = plt.colorbar(im, ax=ax, label='NDVI value', fraction=0.046, pad=0.04)
        ax.set_title('NDVI Post-Disaster — Turkey Earthquake 2023\n'
                     'Green=Vegetation, Red=Built-up/Bare, Yellow=Transition',
                     fontsize=14, fontweight='bold')
        ax.set_xlabel('Column (pixels)')
        ax.set_ylabel('Row (pixels)')
        
        # Add grid for reference
        ax.grid(True, alpha=0.2, linestyle='--')
        
        plt.tight_layout()
        plt.savefig('data/processed/indices/ndvi_post_visualization.png', dpi=150)
        print("  ✓ Saved: data/processed/indices/ndvi_post_visualization.png")
        plt.show()
        
        # ─ Visual check 2: Histogram of values
        print("\n[2/3] Plotting NDVI histogram...")
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Flatten and plot histogram
        ndvi_flat = ndvi_2d.flatten()
        ax.hist(ndvi_flat, bins=100, color='green', alpha=0.7, edgecolor='black')
        ax.axvline(ndvi_2d.mean(), color='red', linestyle='--', linewidth=2, 
                   label=f'Mean: {ndvi_2d.mean():.3f}')
        ax.set_xlabel('NDVI Value')
        ax.set_ylabel('Pixel Count')
        ax.set_title('Distribution of NDVI Values\n'
                     'Healthy vegetation: 0.5-0.8 | Sparse vegetation: 0.2-0.5 | '
                     'Built-up: -0.2-0.0',
                     fontsize=12, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('data/processed/indices/ndvi_histogram.png', dpi=150)
        print("  ✓ Saved: data/processed/indices/ndvi_histogram.png")
        plt.show()
        
        # ─ Visual check 3: Zoomed view of vegetated area
        print("\n[3/3] Plotting zoomed urban vs vegetation comparison...")
        
        h, w = ndvi_2d.shape
        h_quarter, w_quarter = h // 4, w // 4
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Left: Likely vegetated area (assume top-left is greener)
        veg_crop = ndvi_2d[:h_quarter, :w_quarter]
        im1 = axes[0].imshow(veg_crop, cmap='RdYlGn', vmin=-0.2, vmax=0.8)
        axes[0].set_title(f'Vegetated Area Sample\nMean NDVI: {veg_crop.mean():.3f}',
                         fontsize=12, fontweight='bold')
        axes[0].set_xlabel('Column (pixels)')
        axes[0].set_ylabel('Row (pixels)')
        plt.colorbar(im1, ax=axes[0], label='NDVI')
        
        # Right: Likely built-up area (assume bottom-right is darker)
        urban_crop = ndvi_2d[3*h_quarter:, 3*w_quarter:]
        im2 = axes[1].imshow(urban_crop, cmap='RdYlGn', vmin=-0.2, vmax=0.8)
        axes[1].set_title(f'Urban/Built-up Area Sample\nMean NDVI: {urban_crop.mean():.3f}',
                         fontsize=12, fontweight='bold')
        axes[1].set_xlabel('Column (pixels)')
        axes[1].set_ylabel('Row (pixels)')
        plt.colorbar(im2, ax=axes[1], label='NDVI')
        
        plt.tight_layout()
        plt.savefig('data/processed/indices/ndvi_comparison.png', dpi=150)
        print("  ✓ Saved: data/processed/indices/ndvi_comparison.png")
        plt.show()
        
        # ─ Formula validation
        print("\n" + "=" * 80)
        print("FORMULA VALIDATION")
        print("=" * 80)
        print("\n✓ NDVI Formula Check:")
        print("  - High values (0.5-0.8): Dense green vegetation (FORESTS, AGRICULTURE)")
        print("  - Medium values (0.2-0.5): Sparse vegetation, grassland")
        print("  - Low/negative values (-0.2-0.0): Built-up areas, roads, bare soil, water")
        print("  - Your results: ", end="")
        
        if veg_crop.mean() > 0.3 and urban_crop.mean() < 0.2:
            print("✓ CORRECT! Vegetation is bright, urban is dark")
        else:
            print("⚠ Check if band selection or formula needs adjustment")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"\n✗ Error running TEST: {str(e)}")
        import traceback
        traceback.print_exc()
