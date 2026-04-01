from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import torch
import yaml

from src.models.unet import DamageSegmentationModel

# Routers
from src.api.routes import disasters, resources, predict


# --------------------------------------------------
# 154. CREATE APP + CORS
# --------------------------------------------------
app = FastAPI(title="DisasterAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# LOAD CONFIG
# --------------------------------------------------
with open("configs/config.yaml", "r") as f:
    config = yaml.safe_load(f)


# --------------------------------------------------
# 155. STARTUP EVENT (LOAD MODEL)
# --------------------------------------------------
@app.on_event("startup")
def load_model():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = DamageSegmentationModel(config)
    checkpoint_path = config["training"]["checkpoint_path"]

    try:
        checkpoint = torch.load(checkpoint_path, map_location=device)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(device)
        model.eval()

        app.state.model = model
        app.state.device = device
        print("✅ Model loaded successfully")

    except Exception as e:
        app.state.model = None
        print(f"❌ Model loading failed: {e}")


# --------------------------------------------------
# 156. INCLUDE ROUTERS
# --------------------------------------------------
app.include_router(disasters.router, prefix="/api/disasters", tags=["Disasters"])
app.include_router(resources.router, prefix="/api/resources", tags=["Resources"])
app.include_router(predict.router, prefix="/api/predict", tags=["Prediction"])


# --------------------------------------------------
# 157. HEALTH CHECK
# --------------------------------------------------
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "model_loaded": app.state.model is not None
    }


# --------------------------------------------------
# 158. WEBSOCKET (REAL-TIME UPDATES)
# --------------------------------------------------
@app.websocket("/ws/updates")
async def websocket_updates(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            # For now, dummy updates (replace with real data later)
            await websocket.send_json({
                "message": "Live update from DisasterAI",
                "status": "running"
            })

    except Exception:
        await websocket.close()