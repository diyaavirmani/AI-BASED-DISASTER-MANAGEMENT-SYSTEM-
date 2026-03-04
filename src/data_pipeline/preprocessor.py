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
