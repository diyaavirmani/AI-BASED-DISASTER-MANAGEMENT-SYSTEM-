# src/api/main.py — SIMPLIFIED VERSION

import torch
import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model and initialise database on startup."""
    with open("configs/config.yaml") as f:
        config = yaml.safe_load(f)

    # Initialise database (creates tables if they don't exist)
    from src.database.connection import init_db
    init_db()

    # Load trained model into memory once
    arch  = config['model']['architecture']
    ckpt  = config['paths']['active_checkpoint']
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    print(f"Loading model: {arch} from {ckpt}")

    try:
        if arch == 'unet':
            from src.models.unet import load_trained_model
        else:
            from src.models.hrnet import load_trained_model

        app.state.model  = load_trained_model(ckpt, config, device)
        app.state.device = device
        app.state.config = config
        print(f"Model loaded on {device}. API ready.")
    except Exception as e:
        app.state.model  = None
        app.state.device = device
        app.state.config = config
        print(f"⚠️ Model weight file not found at '{ckpt}'. Start system without preloaded model. Error: {e}")

    yield  # App runs here

    # Cleanup on shutdown
    print("Shutting down.")


app = FastAPI(
    title="DisasterAI API",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173",  # Vite dev server
                   "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Include route files
from src.api.routes import disasters, resources, predict
app.include_router(disasters.router, prefix="/api/disasters", tags=["disasters"])
app.include_router(resources.router, prefix="/api/resources",  tags=["resources"])
app.include_router(predict.router,   prefix="/api/predict",    tags=["predict"])


@app.get("/health")
def health():
    model_loaded = hasattr(app.state, 'model') and app.state.model is not None
    return {
        "status": "ok",
        "model_loaded": model_loaded,
        "device": str(getattr(app.state, 'device', 'cpu'))
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)