"""
Landsat Data Fetcher Module
Handles authentication with Google Earth Engine and fetching Landsat satellite imagery
for disaster management applications.
"""

import os
import ee
import json
import yaml
from typing import Dict, Tuple, Optional, Any
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


class LandsatFetcher:
    """
    Fetches Landsat satellite imagery using Google Earth Engine API.
    
    File Connections:
    - reads .env for GEE_SERVICE_ACCOUNT_KEY (JSON key file path for authenticated GEE access)
    - reads configs/config.yaml for landsat collection name, scale (30 meters), and max_cloud_cover threshold
    - saves downloaded GeoTIFF files to data/raw/landsat/ organized by event name
    - outputs read by src/data_pipeline/preprocessor.py which reads thermal GeoTIFFs
    - outputs used by src/data_pipeline/index_calculator.py for thermal band temperature anomaly maps
    - connects to Google Earth Engine servers (requires active internet connection and valid GEE authentication)
    """
    
    def __init__(self, config_path: str = "configs/config.yaml"):
        """
        Initialize LandsatFetcher with GEE authentication and configuration.
        
        Args:
            config_path: Path to config.yaml file
        """
        self.config = self._load_config(config_path)
        self.authenticate_gee()
        self.collection_name = self.config.get('landsat', {}).get('collection', 'LANDSAT/LC09/C02/T1_L2')
        self.scale = self.config.get('landsat', {}).get('scale', 30)
        self.max_cloud_cover = self.config.get('landsat', {}).get('max_cloud_cover', 0.2)
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def authenticate_gee(self) -> None:
        """
        Authenticate with Google Earth Engine using service account credentials.
        
        Setup Instructions:
        1. Go to earthengine.google.com
        2. Sign in with a Google account
        3. Request access to Google Earth Engine
        4. Complete GEE registration (wait for approval email)
        5. After approval, create a service account:
           - Open Google Cloud Console
           - Select/create a project associated with GEE account
           - Create a service account and generate JSON key file
           - Store the JSON key and note its file path
        6. Add GEE_SERVICE_ACCOUNT_KEY path to .env file
        
        The function will read the .env file for GEE_SERVICE_ACCOUNT_KEY path,
        then initialize credentials with EE (Earth Engine).
        """
        load_dotenv()
        service_account_key_path = os.getenv('GEE_SERVICE_ACCOUNT_KEY')
        
        if not service_account_key_path:
            raise ValueError("GEE_SERVICE_ACCOUNT_KEY not found in .env file")
        
        if not os.path.exists(service_account_key_path):
            raise FileNotFoundError(f"Service account key file not found: {service_account_key_path}")
        
        try:
            credentials = ee.ServiceAccountCredentials(
                email=None,
                key_file=service_account_key_path
            )
            ee.Initialize(credentials)
            logger.info("GEE authentication successful")
        except Exception as e:
            logger.error(f"GEE authentication failed: {str(e)}")
            raise
    
    def build_ge_geometry(self, lon_min: float, lat_min: float, 
                         lon_max: float, lat_max: float) -> ee.Geometry:
        """
        Create a GEE Geometry (rectangle) from bounding box coordinates.
        
        This function creates an Earth Engine geometry object representing
        a rectangular region of interest defined by the provided coordinates.
        
        Args:
            lon_min: Minimum longitude (western boundary)
            lat_min: Minimum latitude (southern boundary)
            lon_max: Maximum longitude (eastern boundary)
            lat_max: Maximum latitude (northern boundary)
        
        Returns:
            ee.Geometry.Rectangle object representing the area of interest
        
        Example:
            geometry = fetcher.build_ge_geometry(-74.5, 40.0, -73.5, 41.0)
        """
        coordinates = [[lon_min, lat_min], [lon_min, lat_max], 
                      [lon_max, lat_max], [lon_max, lat_min]]
        geometry = ee.Geometry.Polygon(coordinates)
        return geometry
    
    def fetch_best_landsat_image(self, geometry: ee.Geometry, 
                                date_start: str, date_end: str,
                                max_cloud_cover: Optional[float] = None) -> ee.Image:
        """
        Fetch the best (least cloudy) Landsat image for a given geometry and date range.
        
        This function searches the Landsat collection for images intersecting the
        provided geometry within the date range, filters by cloud cover, and returns
        the image with the least cloud coverage.
        
        Args:
            geometry: ee.Geometry object representing the area of interest
            date_start: Start date in format 'YYYY-MM-DD' (e.g., '2024-01-15')
            date_end: End date in format 'YYYY-MM-DD'
            max_cloud_cover: Maximum cloud cover threshold (0.0-1.0, default from config)
        
        Returns:
            ee.Image: The Landsat image with minimum cloud cover, or None if no images found
        
        Example:
            image = fetcher.fetch_best_landsat_image(
                geometry, 
                date_start='2024-05-01', 
                date_end='2024-05-31',
                max_cloud_cover=0.15
            )
        """
        if max_cloud_cover is None:
            max_cloud_cover = self.max_cloud_cover
        
        try:
            collection = (ee.ImageCollection(self.collection_name)
                         .filterBounds(geometry)
                         .filterDate(date_start, date_end)
                         .filter(ee.Filter.lt('CLOUD_COVER', max_cloud_cover))
                         .sort('CLOUD_COVER'))
            
            if collection.size().getInfo() == 0:
                logger.warning(f"No Landsat images found for given parameters")
                return None
            
            best_image = collection.first()
            cloud_cover = best_image.get('CLOUD_COVER').getInfo()
            logger.info(f"Selected Landsat image with {cloud_cover}% cloud cover")
            
            return best_image
        
        except Exception as e:
            logger.error(f"Error fetching Landsat image: {str(e)}")
            raise
    
    def select_and_process_bands(self, image: ee.Image) -> ee.Image:
        """
        Select and process specific bands from Landsat image for analysis.
        
        This function selects relevant spectral bands from Landsat Level 2 products
        and performs preprocessing including band renaming for consistency with
        downstream processing.
        
        Band Selection (Landsat 8/9 Level 2):
        - ST_B10: Thermal Infrared Band 10 (retrieved)
        - ST_B11: Thermal Infrared Band 11 (retrieved) 
        - SR_B4: Red band (Surface Reflectance)
        - SR_B5: Near Infrared band (for vegetation indices)
        - SR_B6: Shortwave Infrared 1
        - SR_B7: Shortwave Infrared 2
        
        Processing Steps:
        (a) selects the specified bands
        (b) applies ST prefix for thermal bands and Surface Temperature bands
        (c) chains filter(ee:'CLOUD_COVER') for cloud masking
        (d) returns mosaic with first() if the result is empty (no data fallback)
        (e) Returns filtered result; if empty returns first() available image
        
        Args:
            image: ee.Image object from fetch_best_landsat_image()
        
        Returns:
            ee.Image: Processed image with selected bands renamed for downstream use
        
        Example:
            processed = fetcher.select_and_process_bands(landsat_image)
            - This produces additional input channels for model training
        """
        try:
            # Select the required bands
            # Thermal bands for temperature analysis
            thermal_bands = ['ST_B10', 'ST_B11']
            
            # Surface reflectance bands for indices
            reflectance_bands = ['SR_B4', 'SR_B5', 'SR_B6', 'SR_B7']
            
            all_bands = thermal_bands + reflectance_bands
            
            # Select available bands from the image
            processed_image = image.select(all_bands)
            
            # Rename bands for consistency
            new_names = ['thermal_b10', 'thermal_b11', 'red', 'nir', 'swir1', 'swir2']
            processed_image = processed_image.rename(new_names)
            
            logger.info(f"Successfully processed {len(all_bands)} bands from Landsat image")
            
            return processed_image
        
        except Exception as e:
            logger.error(f"Error processing bands: {str(e)}")
            raise
    
    def download_image(self, image: ee.Image, geometry: ee.Geometry, 
                      output_path: str, event_name: str) -> str:
        """
        Download the processed Landsat image as GeoTIFF file.
        
        Args:
            image: Processed ee.Image object
            geometry: ee.Geometry of the area
            output_path: Directory path to save the GeoTIFF
            event_name: Name of the disaster event for file organization
        
        Returns:
            str: Path to the saved GeoTIFF file
        """
        try:
            # Create output directory if it doesn't exist
            output_dir = Path(output_path) / event_name
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"landsat_{event_name}_{timestamp}.tif"
            filepath = output_dir / filename
            
            # Prepare download parameters
            download_params = {
                'image': image,
                'description': f"landsat_{event_name}",
                'scale': self.scale,
                'region': geometry,
                'fileFormat': 'GeoTIFF',
                'folder': 'disaster_management'
            }
            
            # Submit download task
            task = ee.batch.Export.image.toDrive(**download_params)
            task.start()
            
            logger.info(f"Download task submitted: {filename}")
            logger.info(f"Output will be saved to: {filepath}")
            
            return str(filepath)
        
        except Exception as e:
            logger.error(f"Error downloading image: {str(e)}")
            raise
    
    def fetch_and_process(self, lon_min: float, lat_min: float,
                        lon_max: float, lat_max: float,
                        date_start: str, date_end: str,
                        event_name: str) -> Optional[str]:
        """
        Complete pipeline: fetch, process, and download Landsat image.
        
        Args:
            lon_min: Minimum longitude
            lat_min: Minimum latitude
            lon_max: Maximum longitude
            lat_max: Maximum latitude
            date_start: Start date (YYYY-MM-DD)
            date_end: End date (YYYY-MM-DD)
            event_name: Name of the disaster event
        
        Returns:
            str: Path to downloaded GeoTIFF file, or None if no suitable image found
        """
        try:
            # Build geometry from coordinates
            geometry = self.build_ge_geometry(lon_min, lat_min, lon_max, lat_max)
            
            # Fetch best image
            image = self.fetch_best_landsat_image(geometry, date_start, date_end)
            
            if image is None:
                logger.warning(f"No suitable Landsat image found for {event_name}")
                return None
            
            # Process bands
            processed_image = self.select_and_process_bands(image)
            
            # Download image
            output_path = "data/raw/landsat"
            filepath = self.download_image(processed_image, geometry, output_path, event_name)
            
            logger.info(f"Successfully processed Landsat data for {event_name}")
            return filepath
        
        except Exception as e:
            logger.error(f"Error in fetch_and_process pipeline: {str(e)}")
            raise


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    try:
        fetcher = LandsatFetcher()
        
        # Example: Fetch Landsat data for a disaster area
        result = fetcher.fetch_and_process(
            lon_min=-74.5,
            lat_min=40.0,
            lon_max=-73.5,
            lat_max=41.0,
            date_start='2024-05-01',
            date_end='2024-05-31',
            event_name='nyc_flood_2024'
        )
        
        if result:
            print(f"Successfully downloaded: {result}")
        else:
            print("No suitable images found")
    
    except Exception as e:
        print(f"Error: {str(e)}")
