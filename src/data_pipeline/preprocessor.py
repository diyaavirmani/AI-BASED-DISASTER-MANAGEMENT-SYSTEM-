# CCD, alignment, correction
#align correct and tile satellite images
#this file read the raw data that we fetched from 

"""
 a normal image is pixels. A satellite image is also pixels — but it also knows where on Earth each pixel is. Rasterio is the library that reads these special images
    
    
    """

import rasterio
import numpy as np
from pathlib import Path
from rasterio.warp import calculate_default_transform, reproject, Resampling
from scipy.ndimage import uniform_filter
import yaml
from src.data_pipeline.index_calculator import compute_all_indices

def load_geotiff(filepath):
    with rasterio.open(filepath) as dataset:
        array=dataset.read()
        """
dataset.read() with no arguments, rasterio reads ALL bands and returns them as a single numpy array. The shape is always (bands, height, width). So a Sentinel-2 image with 13 bands covering a 512×512 pixel area returns an array of shape (13, 512, 512).
        """
        metadata={
            "transform":dataset.transform, #the affine transformation that maps pixel coordinates to geographic coordinates
            "crs":dataset.crs, #the coordinate reference system (CRS) of the image, which defines how the geographic coordinates are represented
            "shape":dataset.shape,#the dimensions of the image in pixels (height, width)
            "dtype":dataset.dtypes[0],#the data type of the pixel values (e.g., uint16, float32)
            "count":dataset.count,#the number of bands in the image
            "bounds":dataset.bounds # It represents how much of that specific wavelength of light bounced back from the Earth's surface into the satellite's sensor at that location.
            
        }
        return array, metadata
    

"""_summary_
 Rasterio opens GeoTIFFs and preserves both pieces together.-the actual pixel data and the geographical metadata
 Each number in this array is a Digital Number (DN) 
  It represents how much of that specific wavelength of light bounced back from the Earth's surface into the satellite's sensor at that location.
 
    """
    
def reproject_to_common_crs(src_array,src_meta,target_crs):
    src_crs=src_meta["crs"]
    src_transform=src_meta["transform"]
    bands, height, width=src_array.shape
    
    new_transform, new_width, new_height=calculate_default_transform(
        src_crs,
        target_crs, 
        width,
        height, 
        *rasterio.transform.array_bounds(height,width,src_transform))
    reprojected=np.zeros((bands,new_height,new_width),dtype=src_meta["dtype"])
    
    for i in range(bands):
        reproject(
            source=src_array[i],
            destination=reprojected[i],
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=new_transform,
            dst_crs=target_crs,
            resampling=Resampling.bilinear
            
            
        )
    
    new_meta=src_meta.copy()
    new_meta.update({
        "crs":target_crs,
        "transform":new_transform,
        "width":new_width,  
        "height":new_height
    })
    
    return reprojected, new_meta
    """
    Reprojection mathematically re-expresses every pixel's location in a new coordinate system. After reprojection, pixel (100, 200) in your Sentinel-1 SAR image and pixel (100, 200) in your Sentinel-2 optical image both represent the exact same 10×10 metre square of ground in Turkey.
    When you save your damage zones to PostGIS and display them on your Leaflet/Mapbox dashboard, the coordinates must be in WGS84. So you reproject everything to WGS84 early in the pipeline and keep it consistent throughout.
    """
    
def coregister_images (before_array, before_meta, after_array, after_meta):
    ref_transform=before_meta["transform"]
    ref_crs=before_meta["crs"]
    ref_shape=(before_meta["height"], before_meta["width"])
    
    bands=after_array.shape[0]
    
    aligned_after=np.zeros(
        (bands, ref_shape[0], ref_shape[1]),
        dtype=after_meta["dtype"]
    )
    
    for i in range(bands):
        reproject(
            source=after_array[i],
            destination=aligned_after[i],
            src_transform=after_meta["transform"],
            src_crs=after_meta["crs"],
            dst_transform=ref_transform,
            dst_crs=ref_crs,
            resampling=Resampling.bilinear
        )
        
    aligned_meta=after_meta.copy()
    aligned_meta.update({
        "transform":ref_transform,
        "crs":ref_crs,
        "width":ref_shape[1],
        "height":ref_shape[0]
    })
    
    return aligned_after, aligned_meta,before_array, before_meta

    """
     Co-regis tration solves a different, subtler problem: even after both images are in WGS84, they might still not align at the pixel level.  
     handleing the false positives
    """
    
def compute_coherence(sar_before, sar_after, window_Size=5):
    before = sar_before.astype(np.complex64)
    after = sar_after.astype(np.complex64)

    # product of complex numbers: before * conj(after)
    cross = before * np.conj(after)

    power_before = before * np.conj(before)
    power_after = after * np.conj(after)

    avg_cross = uniform_filter(np.abs(cross), size=window_Size)
    avg_power_before = uniform_filter(power_before, size=window_Size)
    avg_power_after = uniform_filter(power_after, size=window_Size)

    denominator = np.sqrt(avg_power_before * avg_power_after)

    coherence = np.where(
        denominator > 0,
        avg_cross / denominator,
        0
    )

    coherence = np.clip(coherence, 0, 1)

    return coherence.astype(np.float32)

def normalize_image(array, method="minmax"):
    """Normalize a multi-band image array.

    Args:
        array (np.ndarray): shape (bands, h, w)
        method (str): "minmax" or "zscore"

    Returns:
        np.ndarray: normalized data same shape
    """
    array = array.astype(np.float32)
    normalized = np.zeros_like(array)

    if method == "minmax":
        for i in range(array.shape[0]):
            band = array[i]
            min_val = np.min(band)
            max_val = np.max(band)

            if max_val - min_val == 0:
                normalized[i] = 0.0
            else:
                normalized[i] = (band - min_val) / (max_val - min_val)
    elif method == "zscore":
        for i in range(array.shape[0]):
            band = array[i]
            mean = np.nanmean(band)
            std = np.nanstd(band)

            if std == 0:
                normalized[i] = 0.0
            else:
                normalized[i] = (band - mean) / std
    else:
        raise ValueError(f"Unknown normalization method: {method}")
    # summary comment removed; not part of function
def tile_image(array, tile_size=256, overlap=32):
    bands, height, width = array.shape
    stride = tile_size - overlap
    tiles = []
    positions = []
    y = 0

    while y < height:
        y_start = min(y, height - tile_size)
        y_end = y_start + tile_size

        x = 0
        while x < width:
            x_start = min(x, width - tile_size)
            x_end = x_start + tile_size

            tile = array[:, y_start:y_end, x_start:x_end]
            tiles.append(tile)
            positions.append((y_start, y_end, x_start, x_end))

            x += stride

        y += stride
    # return after loops
    return tiles, positions

def stitch_tiles(tiles, positions, full_height, full_width, overlap=32):
    """Reconstruct full image from tiles with overlaps."""
    margin = overlap // 2
    output = np.zeros((full_height, full_width), dtype=np.float32)
    count = np.zeros((full_height, full_width), dtype=np.float32)

    for tile, pos in zip(tiles, positions):
        y_start, y_end, x_start, x_end = pos
        y_s = y_start + margin
        y_e = y_end - margin
        x_s = x_start + margin
        x_e = x_end - margin

        output[y_s:y_e, x_s:x_e] += tile[margin:-margin, margin:-margin]
        count[y_s:y_e, x_s:x_e] += 1

    # Average overlapping regions
    output = np.where(count > 0, output / count, 0)
    return output

    """load raw images-> reproject to common CRS-> coregister before and after images-> compute coherence-> normalize-> tile for model input
    
    """


def preprocess_event(event_name, config_path="configs/config.yaml"):
    
    # ── Step 1: Load config ──────────────────────────────
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    raw_dir       = Path(config["paths"]["raw_data_dir"])
    processed_dir = Path(config["paths"]["processed_data_dir"])
    tile_size     = config["sentinel"]["tile_size"]
    overlap       = config["sentinel"]["overlap"]
    
    event_raw  = raw_dir / event_name
    event_out  = processed_dir / event_name
    event_out.mkdir(parents=True, exist_ok=True)
    
    print(f"[1/7] Starting preprocessing for event: {event_name}")
    
    # ── Step 2: Load raw images ──────────────────────────
    s2_before_path = event_raw / "sentinel2_before.tif"
    s2_after_path  = event_raw / "sentinel2_after.tif"
    s1_before_path = event_raw / "sentinel1_before.tif"
    s1_after_path  = event_raw / "sentinel1_after.tif"
    
    s2_before, s2_before_meta = load_geotiff(s2_before_path)
    s2_after,  s2_after_meta  = load_geotiff(s2_after_path)
    s1_before, s1_before_meta = load_geotiff(s1_before_path)
    s1_after,  s1_after_meta  = load_geotiff(s1_after_path)
    
    print(f"[2/7] Loaded raw images.")
    print(f"      S2 before shape: {s2_before.shape}")
    print(f"      S1 before shape: {s1_before.shape}")
    
    # ── Step 3: Reproject everything to WGS84 ───────────
    s2_before, s2_before_meta = reproject_to_common_crs(s2_before, s2_before_meta)
    s2_after,  s2_after_meta  = reproject_to_common_crs(s2_after,  s2_after_meta)
    s1_before, s1_before_meta = reproject_to_common_crs(s1_before, s1_before_meta)
    s1_after,  s1_after_meta  = reproject_to_common_crs(s1_after,  s1_after_meta)
    
    print("[3/7] Reprojected all images to WGS84.")
    
    # ── Step 4: Co-register — align after to before ─────
    s2_before, s2_before_meta, s2_after, s2_after_meta = coregister_images(
        s2_before, s2_after, s2_before_meta, s2_after_meta
    )
    s1_before, s1_before_meta, s1_after, s1_after_meta = coregister_images(
        s1_before, s1_after, s1_before_meta, s1_after_meta
    )
    
    print("[4/7] Co-registered before/after image pairs.")
    
    # ── Step 5: Compute SAR coherence ───────────────────
    # Use VV band (index 0) for coherence computation
    coherence_before = compute_coherence(
        s1_before[0], s1_before[0],   # before vs before = baseline
        window_size=5
    )
    coherence_after = compute_coherence(
        s1_before[0], s1_after[0],    # before vs after = actual change
        window_size=5
    )
    coherence_delta = coherence_after - coherence_before
    
    print("[5/7] Computed SAR coherence maps.")
    
    # ── Step 6: Compute spectral indices ────────────────
    band_dict_before = {
        "red":   s2_before[3],   # Band 4 = Red
        "nir":   s2_before[7],   # Band 8 = NIR
        "green": s2_before[2],   # Band 3 = Green
        "swir":  s2_before[11],  # Band 12 = SWIR2
    }
    band_dict_after = {
        "red":   s2_after[3],
        "nir":   s2_after[7],
        "green": s2_after[2],
        "swir":  s2_after[11],
    }
    
    indices = compute_all_indices(band_dict_before, band_dict_after)
    
    print("[6/7] Computed spectral indices (NDVI, NDWI, NBR, deltas).")
    
    # ── Step 7: Stack all channels into one array ────────
    # Shape: (22, H, W)
    full_array = np.concatenate([
        s2_after,                                          # 6 optical bands
        s1_after,                                          # 4 SAR bands (VV, VH x2)
        np.stack([                                         # 5 indices
            indices["ndvi_post"],
            indices["ndwi_post"],
            indices["nbr_post"],
            indices["delta_ndvi"],
            indices["delta_nbr"]
        ]),
        np.stack([                                         # 3 CCD bands
            coherence_before,
            coherence_after,
            coherence_delta
        ]),
    ], axis=0)
    
    print(f"      Stacked array shape: {full_array.shape}")  
    # Expected: (18, H, W) — remaining 4 channels added later
    
    # ── Step 8: Normalize ────────────────────────────────
    # Use minmax for optical + indices, zscore for SAR
    optical_normalized = normalize_image(full_array[:6],   method='minmax')
    sar_normalized     = normalize_image(full_array[6:10], method='zscore')
    indices_normalized = normalize_image(full_array[10:],  method='minmax')
    
    normalized_array = np.concatenate([
        optical_normalized,
        sar_normalized,
        indices_normalized
    ], axis=0)
    
    print("[7/7] Normalized all channels.")
    
    # ── Step 9: Tile and save ────────────────────────────
    tiles, positions = tile_image(
        normalized_array,
        tile_size=tile_size,
        overlap=overlap
    )
    
    tiles_dir = event_out / "tiles"
    tiles_dir.mkdir(exist_ok=True)
    
    for idx, (tile, pos) in enumerate(zip(tiles, positions)):
        tile_path = tiles_dir / f"tile_{idx:04d}.npy"
        np.save(tile_path, tile)
    
    # Save positions so you can stitch results back later
    positions_path = event_out / "tile_positions.npy"
    np.save(positions_path, positions)
    
    print(f"Preprocessing complete.")
    print(f"Saved {len(tiles)} tiles to: {tiles_dir}")
    
    return tiles_dir, positions_path
