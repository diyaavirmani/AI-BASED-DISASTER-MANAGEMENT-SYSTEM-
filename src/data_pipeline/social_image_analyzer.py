import requests
import io
import torch
import pytesseract

from PIL import Image, ImageEnhance
from PIL.ExifTags import TAGS

from transformers import CLIPProcessor, CLIPModel


class SocialImageAnalyzer:

    def __init__(self):

        # Load CLIP once (downloads on first run)
        self.processor = CLIPProcessor.from_pretrained(
            "openai/clip-vit-base-patch32"
        )

        self.model = CLIPModel.from_pretrained(
            "openai/clip-vit-base-patch32"
        )

    # --------------------------------------------------
    # Download image from URL
    # --------------------------------------------------

    def download_image(self, url):

        try:

            response = requests.get(
                url,
                timeout=10,
                stream=True
            )

            response.raise_for_status()

            image_bytes = io.BytesIO(response.content)

            image = Image.open(image_bytes).convert("RGB")

            return image

        except Exception:

            return None

    # --------------------------------------------------
    # Extract EXIF GPS
    # --------------------------------------------------

    def extract_exif_gps(self, image):

        try:

            exif = image._getexif()

            if not exif:
                return None

            gps_info = None

            for tag, value in exif.items():

                decoded = TAGS.get(tag, tag)

                if decoded == "GPSInfo":
                    gps_info = value

            if not gps_info:
                return None

            def convert_to_degrees(value):

                d = value[0][0] / value[0][1]
                m = value[1][0] / value[1][1]
                s = value[2][0] / value[2][1]

                return d + m / 60 + s / 3600

            lat = convert_to_degrees(gps_info[2])
            lat_ref = gps_info[1]

            lon = convert_to_degrees(gps_info[4])
            lon_ref = gps_info[3]

            if lat_ref == "S":
                lat = -lat

            if lon_ref == "W":
                lon = -lon

            return (lat, lon)

        except Exception:

            return None

    # --------------------------------------------------
    # OCR
    # --------------------------------------------------

    def run_ocr(self, image):

        try:

            gray = image.convert("L")

            enhancer = ImageEnhance.Contrast(gray)

            enhanced = enhancer.enhance(2.0)

            text = pytesseract.image_to_string(enhanced)

            return text.strip()

        except Exception:

            return ""

    # --------------------------------------------------
    # Disaster classification (CLIP)
    # --------------------------------------------------

    def classify_disaster_image(self, image):

        labels = [
            "earthquake collapsed buildings and rubble",
            "flood with water covering streets and homes",
            "wildfire burning forest and smoke",
            "cyclone storm wind damage",
            "normal scene no disaster visible"
        ]

        inputs = self.processor(
            text=labels,
            images=image,
            return_tensors="pt",
            padding=True
        )

        outputs = self.model(**inputs)

        logits = outputs.logits_per_image

        probs = torch.softmax(logits, dim=1)

        idx = probs.argmax().item()

        return labels[idx], probs[0][idx].item()

    # --------------------------------------------------
    # Severity classification (CLIP)
    # --------------------------------------------------

    def estimate_visual_severity(self, image):

        labels = [
            "catastrophic total destruction everything destroyed",
            "severe widespread major damage",
            "moderate damage partial destruction",
            "minor damage small impact",
            "no visible damage normal"
        ]

        inputs = self.processor(
            text=labels,
            images=image,
            return_tensors="pt",
            padding=True
        )

        outputs = self.model(**inputs)

        logits = outputs.logits_per_image

        probs = torch.softmax(logits, dim=1)

        idx = probs.argmax().item()

        return labels[idx], probs[0][idx].item()

    # --------------------------------------------------
    # Analyze single image URL
    # --------------------------------------------------

    def analyze_social_image(self, image_url):

        image = self.download_image(image_url)

        if image is None:

            return {
                "image_url": image_url,
                "analysis_successful": False
            }

        gps = self.extract_exif_gps(image)

        ocr_text = self.run_ocr(image)

        disaster_label, disaster_score = \
            self.classify_disaster_image(image)

        severity_label, severity_score = \
            self.estimate_visual_severity(image)

        return {

            "image_url": image_url,

            "disaster_type": disaster_label,
            "disaster_confidence": disaster_score,

            "severity_label": severity_label,
            "severity_confidence": severity_score,

            "ocr_text": ocr_text,

            "gps_coordinates": gps,

            "analysis_successful": True
        }

    # --------------------------------------------------
    # Analyze all images in a post
    # --------------------------------------------------

    def analyze_post_images(self, post_dict):

        if "image_urls" not in post_dict:
            return []

        urls = post_dict["image_urls"]

        if not urls:
            return []

        results = []

        for url in urls:

            analysis = self.analyze_social_image(url)

            if analysis and analysis["analysis_successful"]:
                results.append(analysis)

        return results