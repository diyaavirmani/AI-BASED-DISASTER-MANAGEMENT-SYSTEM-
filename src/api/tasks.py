from celery import Celery
from celery.schedules import crontab
import torch
import yaml

# External modules (your pipeline)
from src.data_pipeline.satellite_fetcher import fetch_satellite_data
from src.data_pipeline.landsat_fetcher import fetch_landsat_data
from src.data_pipeline.preprocessor import preprocess_images

from src.models.unet import DamageSegmentationModel
from src.database.connection import SessionLocal
from src.database.models import SatelliteImage, DamageAssessment

from datetime import datetime


# --------------------------------------------------
# 160. CELERY APP (REDIS BROKER)
# --------------------------------------------------
celery_app = Celery(
    "disaster_tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)


# --------------------------------------------------
# LOAD CONFIG (shared)
# --------------------------------------------------
with open("configs/config.yaml", "r") as f:
    config = yaml.safe_load(f)


# --------------------------------------------------
# 161. FETCH + PROCESS SATELLITE DATA
# --------------------------------------------------
@celery_app.task
def fetch_and_process_satellite(event_name, bbox_coords, date_before, date_after):
    db = SessionLocal()

    try:
        # Step 1: Fetch imagery
        sentinel_data = fetch_satellite_data(
            event_name, bbox_coords, date_before, date_after
        )

        landsat_data = fetch_landsat_data(
            event_name, bbox_coords, date_before, date_after
        )

        # Step 2: Preprocess
        processed_path = preprocess_images(sentinel_data + landsat_data)

        # Step 3: Save records in DB
        for path in processed_path:
            image = SatelliteImage(
                event_id=None,  # You can map event_id properly
                image_type="processed",
                captured_at=datetime.utcnow(),
                file_path=path
            )
            db.add(image)

        db.commit()

        # Step 4: Trigger inference task
        run_damage_inference.delay(processed_path, event_id=None)

        return {"status": "completed"}

    except Exception as e:
        db.rollback()
        return {"status": "failed", "error": str(e)}

    finally:
        db.close()


# --------------------------------------------------
# 162. DAMAGE INFERENCE TASK
# --------------------------------------------------
@celery_app.task
def run_damage_inference(processed_tiles_path, event_id):
    db = SessionLocal()

    try:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Load model
        model = DamageSegmentationModel(config)
        checkpoint = torch.load(
            config["training"]["checkpoint_path"],
            map_location=device
        )
        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(device)
        model.eval()

        # Dummy loop (replace with actual tile loading)
        for tile_path in processed_tiles_path:
            # TODO: load tile image properly
            # tile = load_image(tile_path)

            # Fake prediction for structure
            damage_level = 2
            confidence = 0.85

            assessment = DamageAssessment(
                event_id=event_id,
                assessed_at=datetime.utcnow(),
                confidence_score=confidence,
                damage_level=damage_level
            )

            db.add(assessment)

        db.commit()

        # TODO: Send WebSocket notification (hook into main.py)
        print("📡 Inference complete — notify dashboard")

        return {"status": "inference_done"}

    except Exception as e:
        db.rollback()
        return {"status": "failed", "error": str(e)}

    finally:
        db.close()


# --------------------------------------------------
# 163. PERIODIC TASK (EVERY 6 HOURS)
# --------------------------------------------------
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Every 6 hours
    sender.add_periodic_task(
        crontab(minute=0, hour="*/6"),
        scheduled_satellite_check.s()
    )


@celery_app.task
def scheduled_satellite_check():
    """
    Check GDACS or any disaster API and trigger pipeline
    """
    print("🔄 Checking for new disasters...")

    # TODO: Replace with actual GDACS API call
    dummy_event = {
        "name": "flood_india",
        "bbox": [72.0, 18.0, 73.0, 19.0]
    }

    fetch_and_process_satellite.delay(
        dummy_event["name"],
        dummy_event["bbox"],
        "2024-01-01",
        "2024-01-10"
    )

    return {"status": "scheduled_run_triggered"}