# Satellite/ Landsat/ Sentinel API calls
#fetch sentinal1 and sentinal 2 images

#import libraries
import os
from sentinelhub.geo_utils import bbox_to_dimensions
import yaml  # Used to read and parse YAML configuration files
from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
import pathlib
import datetime
import dotenv
from sentinelhub import SHConfig, SentinelHubRequest, DataCollection, MimeType, CRS, BBox

# Load environment variables from .env (if present)
dotenv.load_dotenv()

#reading config and returns it as a dictionary
#with ensures the file is automatically closed after reading
def load_config():
    with open("configs/config.yaml","r") as file:
        config =yaml.safe_load(file)
    return config 

#Returns the parsed configuration as a dictionary
def authenticate():
    config=SHConfig()
    config.sh_client_id=os.getenv("SH_CLIENT_ID")
    config.sh_client_secret=os.getenv("SH_CLIENT_SECRET")
    
    # note: properties are sh_client_id and sh_client_secret
    if not config.sh_client_id or not config.sh_client_secret:
        raise ValueError("Sentinel Hub credentials not found in environment variables.")
    return config 
#This function defines the Area of Interest (AOI).
#BBox tells Sentinel Hub “WHERE on Earth” to look
def build_box(lat_min,lon_min,lat_max,lon_max):
    return BBox(bbox=[lon_min,lat_min,lon_max,lat_max], crs=CRS.WGS84)    #CRS.WGS84 → standard GPS coordinate system
#This function:Builds a request,Downloads data,Saves it as GeoTIFF
def fetch_sentinel2_optical(bbox, date_before, date_after, save_dir, config):
    """Download a Sentinel‑2 optical image using the Sentinel Hub API.

    Parameters
    ----------
    bbox : sentinelhub.BBox
        Bounding box to request.
    date_before : str
        ISO date string end of range (e.g. "2025-01-01").
    date_after : str
        ISO date string start of range.
    save_dir : str or pathlib.Path
        Directory where the result will be saved.
    config : SHConfig
        Authenticated Sentinel Hub configuration.
    """
    os.makedirs(save_dir, exist_ok=True)
    evalscript = """
    //VERSION=3
    function setup() {
        return {
            input: ["B02", "B03", "B04", "B08", "dataMask"],
            output: { bands: 4 }
        };
    }
    function evaluatePixel(sample) {
        return [sample.B04, sample.B03, sample.B02, sample.B08];
    }
    """
    request = SentinelHubRequest(
        evalscript=evalscript,
        input_data=[
            {
                "type": "S2L2A",
                "dataFilter": {
                    "timeRange": {"from": date_after, "to": date_before},
                },
            }
        ],
        responses=[
            {"identifier": "default", "format": {"type": MimeType.TIFF.value}}
        ],
        bbox=bbox,
        size=(512, 512),
        config=config,
    )
    data = request.get_data()
    out_path = os.path.join(save_dir, "sentinel2.tif")
    # the request usually returns a numpy array; write with rasterio if available
    try:
        import rasterio
        with rasterio.open(out_path, "w", driver="GTiff",
                           height=data[0].shape[0], width=data[0].shape[1],
                           count=data[0].shape[2], dtype=data[0].dtype) as dst:
            for i in range(data[0].shape[2]):
                dst.write(data[0][:,:,i], i+1)
    except ImportError:
        # fallback: save numpy array as .npy
        import numpy as np
        np.save(out_path + ".npy", data)
    return out_path

def fetch_sentinel1_sar(bbox,date_before,date_after,save_dir,config):
    os.makedirs(save_dir, exist_ok=True)
    evalscript = """
    //VERSION=3
    function setup() {
        return {
            input: ["VV", "VH", "dataMask"],
            output: { bands: 2 }
        };
    }
    function evaluatePixel(sample) {
        return [sample.VV, sample.VH];
    }
    """

    size = bbox_to_dimensions(bbox, resolution=10)
    request = SentinelHubRequest(
        evalscript=evalscript,
        input_data=[
            {
                "type": "S1IW",
                "dataFilter": {
                    "timeRange": {"from": date_after, "to": date_before},
                    "polarization": ["VV", "VH"]
                }
            }
        ],
        responses=[
            {"identifier": "default", "format": {"type": MimeType.TIFF.value}}
        ],
        bbox=bbox,
        size=size,
        config=config,
    )

    data = request.get_data()
    out_path = os.path.join(save_dir, "sentinel1.tif")
    try:
        import rasterio
        with rasterio.open(out_path, "w", driver="GTiff",
                           height=data[0].shape[0], width=data[0].shape[1],
                           count=data[0].shape[2], dtype=data[0].dtype) as dst:
            for i in range(data[0].shape[2]):
                dst.write(data[0][:,:,i], i+1)
    except ImportError:
        import numpy as np
        np.save(out_path + ".npy", data)
    return out_path
#optical satellites fail in clouds and ait night , so we need sar works 24*7

#calls both sentinel1 and sentinal 2 and organises outputs
def fetch_imagery(event_name, bbox,disaster_date,config):
    base_dir=f"data/{event_name}"
    optical_dir=f"{base_dir}/sentinel2"
    sar_dir=f"{base_dir}/sentinel1"
    fetch_sentinel2_optical(bbox, date_before=disaster_date, date_after=(datetime.datetime.strptime(disaster_date, "%Y-%m-%d") - datetime.timedelta(days=30)).strftime("%Y-%m-%d"), save_dir=optical_dir, config=config)
    fetch_sentinel1_sar(bbox, date_before=disaster_date, date_after=(datetime.datetime.strptime(disaster_date, "%Y-%m-%d") - datetime.timedelta(days=30)).strftime("%Y-%m-%d"), save_dir=sar_dir, config=config)
    

if __name__ == "__main__":
    config=authenticate()
    
    bbox=build_box(lat_min=37.0, lon_min=-122.5, lat_max=38.0, lon_max=-121.5)
    
    fetch_imagery(
        event_name="testcase",
        bbox=bbox,
        disaster_date='2023-02-06',
        config=config
        
    )
    
    
#this file saves output geotiff files to data/raw/sentinel1 and 2 
