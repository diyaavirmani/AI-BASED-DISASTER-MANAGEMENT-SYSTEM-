# src/api/routes/predict.py — SIMPLIFIED VERSION
# No Celery. Uses FastAPI BackgroundTasks for inference.
# Good enough for <10 concurrent users.

import time
import json
import torch
import numpy as np
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime

from src.database.connection import get_db, SessionLocal
from src.database.models import DamageAssessment, DisasterEvent
from src.data_pipeline.preprocessor import build_9channel_input, tile_array, stitch_tiles

router = APIRouter(tags=["predict"], prefix="/api/predict")

# Simple in-memory task tracker
# For a single-server deployment this is fine
# Replace with Redis if you ever run multiple server instances
TASK_STATUS = {}


class PredictRequest(BaseModel):
    event_id: int
    optical_path: str
    sar_path: str = None  # Optional — model handles missing SAR gracefully


class PredictResponse(BaseModel):
    event_id: int
    task_id: str
    status: str
    message: str


def run_inference_background(task_id: str, event_id: int,
                              optical_path: str, sar_path: str,
                              model, device, config):
    """
    Runs inside FastAPI BackgroundTasks.
    No Celery needed — runs in the same process after the response is sent.
    Limitation: if server restarts mid-task, task is lost.
    Acceptable for demo/early deployment.
    """
    try:
        TASK_STATUS[task_id] = {"state": "RUNNING", "progress": 0}

        if model is None:
            raise ValueError("No machine learning model weights are loaded. Please place weights in checks and configure configs/config.yaml.")

        import rasterio
        import cv2

        # Load raw images
        with rasterio.open(optical_path) as src:
            optical = src.read().transpose(1, 2, 0)
            geo_transform = src.transform
            crs = src.crs

        sar = None
        if sar_path:
            with rasterio.open(sar_path) as src:
                sar = src.read().transpose(1, 2, 0)

        # Build 9-channel input
        target_hw = config.get('preprocessing', {}).get('target_hw', 512)
        tile_size  = config.get('model', {}).get('tile_size', 256)

        stacked = build_9channel_input(optical, sar, target_hw=target_hw)
        full_h, full_w = stacked.shape[:2]
        TASK_STATUS[task_id]["progress"] = 20

        # Tile
        tiles, positions = tile_array(stacked, tile_size=tile_size, overlap=32)
        tile_predictions  = []

        model.eval()
        batch_size = 4  # Small batch — no GPU needed for demo

        with torch.no_grad():
            for i in range(0, len(tiles), batch_size):
                batch = tiles[i:i+batch_size]
                batch_tensor = torch.stack([
                    torch.from_numpy(t.transpose(2,0,1)).float()
                    for t in batch
                ]).to(device)
                logits = model(batch_tensor)
                probs  = torch.softmax(logits, dim=1)
                tile_predictions.extend([probs[j].cpu().numpy() for j in range(len(batch))])

                # Update progress
                progress = 20 + int((i / len(tiles)) * 60)
                TASK_STATUS[task_id]["progress"] = min(90, progress)

        # Stitch
        damage_map = stitch_tiles(tile_predictions, positions,
                                   full_h, full_w, num_classes=4, overlap=32)

        # Compute summary stats
        total = damage_map.size
        stats = {
            "pct_no_damage":  float((damage_map == 0).sum() / total * 100),
            "pct_minor":      float((damage_map == 1).sum() / total * 100),
            "pct_major":      float((damage_map == 2).sum() / total * 100),
            "pct_destroyed":  float((damage_map == 3).sum() / total * 100),
        }

        # Convert to simple GeoJSON
        geojson = damage_map_to_simple_geojson(damage_map, geo_transform)

        # Save to database
        db = SessionLocal()
        try:
            assessment = DamageAssessment(
                event_id             = event_id,
                assessed_at          = datetime.utcnow(),
                damage_level         = int(damage_map.max()),
                confidence           = 0.85,
                confidence_score     = 0.85,
                damage_zones_geojson = json.dumps(geojson),
                total_pixels_assessed = total,
                **stats
            )
            db.add(assessment)
            db.commit()
        finally:
            db.close()

        TASK_STATUS[task_id] = {
            "state": "SUCCESS",
            "progress": 100,
            "result": {
                "event_id": event_id,
                "zones_detected": len(geojson.get("features", [])),
                "stats": stats
            }
        }

    except Exception as e:
        TASK_STATUS[task_id] = {"state": "FAILED", "error": str(e), "progress": 100}
        print(f"Inference task {task_id} failed: {e}")


def damage_map_to_simple_geojson(damage_map, transform):
    """Converts pixel damage map to GeoJSON without PostGIS."""
    import cv2
    features = []

    for damage_class in [1, 2, 3]:
        mask     = (damage_map == damage_class).astype(np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            if cv2.contourArea(contour) < 10:
                continue
            coords = []
            for point in contour.squeeze():
                if point.ndim == 1:
                    lon, lat = transform * (int(point[0]), int(point[1]))
                    coords.append([lon, lat])
            if len(coords) >= 3:
                coords.append(coords[0])
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": [coords]},
                    "properties": {
                        "damage_level": int(damage_class),
                        "damage_label": ["no_damage","minor","major","destroyed"][damage_class]
                    }
                })

    return {"type": "FeatureCollection", "features": features}


@router.post("/", response_model=PredictResponse)
def trigger_inference(request: PredictRequest,
                       background_tasks: BackgroundTasks,
                       req: Request,
                       db=Depends(get_db)):

    event = db.query(DisasterEvent).filter_by(id=request.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    task_id = f"task_{request.event_id}_{int(time.time())}"
    TASK_STATUS[task_id] = {"state": "PENDING", "progress": 0}

    background_tasks.add_task(
        run_inference_background,
        task_id      = task_id,
        event_id     = request.event_id,
        optical_path = request.optical_path,
        sar_path     = request.sar_path,
        model        = getattr(req.app.state, 'model', None),
        device       = getattr(req.app.state, 'device', torch.device('cpu')),
        config       = getattr(req.app.state, 'config', {})
    )

    return PredictResponse(
        event_id = request.event_id,
        task_id  = task_id,
        status   = "PENDING",
        message  = "Inference queued as background task"
    )


@router.get("/status/{task_id}")
def get_task_status(task_id: str):
    status = TASK_STATUS.get(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    return status


@router.get("/results/{event_id}")
def get_results(event_id: int, db=Depends(get_db)):
    assessment = db.query(DamageAssessment)\
                   .filter_by(event_id=event_id)\
                   .order_by(DamageAssessment.assessed_at.desc())\
                   .first()
    if not assessment:
        raise HTTPException(status_code=404, detail="No assessment found")

    return {
        "event_id":    event_id,
        "assessed_at": assessment.assessed_at,
        "damage_level": assessment.damage_level,
        "stats": {
            "pct_no_damage": assessment.pct_no_damage,
            "pct_minor":     assessment.pct_minor,
            "pct_major":     assessment.pct_major,
            "pct_destroyed": assessment.pct_destroyed,
        },
        "damage_zones": json.loads(assessment.damage_zones_geojson or "{}")
    }


async def progress_generator(task_id: str) -> AsyncGenerator[str, None]:
    """Async generator for Server-Sent Events progress stream."""
    max_duration = 3600  # 1 hour limit
    start_time = time.time()
    
    while time.time() - start_time < max_duration:
        status = TASK_STATUS.get(task_id)
        if not status:
            yield f"data: {json.dumps({'state': 'PENDING', 'progress_percent': 0})}\n\n"
            await asyncio.sleep(1.5)
            continue
        
        state = status.get("state", "PENDING")
        progress = status.get("progress", 0)
        
        event_data = {
            "state": state,
            "progress_percent": progress,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if "error" in status:
            event_data["error"] = status["error"]
        if "result" in status:
            event_data["result"] = status["result"]

        yield f"data: {json.dumps(event_data)}\n\n"
        
        if state in ["SUCCESS", "FAILED"]:
            break
            
        await asyncio.sleep(1.5)


@router.get("/stream/{task_id}")
async def stream_progress(task_id: str):
    """Stream live inference progress via Server-Sent Events."""
    import asyncio
    return StreamingResponse(
        progress_generator(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
