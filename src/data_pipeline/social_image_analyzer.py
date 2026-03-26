"""Social media image analysis utilities.

Downloads and analyzes images attached to social media posts.
Runs vision AI to classify disaster type and severity from photos.
Extracts GPS from metadata and runs OCR on visible text.
"""

from email.mime import image

import requests
import io
from PIL import Image

def download_image(image_url: str) -> Image.Image:
    try:
        response=requests.get(
            url=image_url,
            timeout=10,
            stream=True
        )
        response.raise_for_status()
        
        image_bytes=io.BytesIO(response.content)
        image=Image.open(image_bytes)
        
        return image
    
    except Exception as e:
        return None

from PIL.ExifTags import TAGS,GPSTAGS

def extract_gps_from_image(image: Image.Image) -> dict:
    try:
        exif=image._getexif()
        if not exif:
            return None
        
        gps_info=None
        
        for tag, value in exif.items():
            decoded=TAGS.get(tag,tag)
            if decoded=="GPSInfo":
                gps_info=value
        if not gps_info:
            return None

        def convert_to_degrees(value):

            d = value[0][0] / value[0][1]
            m = value[1][0] / value[1][1]
            s = value[2][0] / value[2][1]

            return d + (m / 60.0) + (s / 3600.0)
        lat = convert_to_degrees(gps_info[2])
        lat_ref = gps_info[1]

        lon = convert_to_degrees(gps_info[4])
        lon_ref = gps_info[3]

        if lat_ref == "S":
            lat = -lat

        if lon_ref == "W":
            lon = -lon

        return (lat, lon)

    except:
        return None
