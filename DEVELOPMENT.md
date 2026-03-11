# Development Guide

This document outlines the development workflow, setup, and contribution guidelines for the AI-Based Disaster Management System.

---

## Environment Setup

1. **Create Virtual Environment**
   ```bash
   python -m venv dm
   source dm/Scripts/activate  # Windows: dm\Scripts\Activate.ps1
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run API Server**
   ```bash
   uvicorn src.api.main:app --reload
   ```
   The API will be available at `http://localhost:8000`. OpenAPI docs at `http://localhost:8000/docs`.

---

## Project Structure

```
src/
├── api/                      # FastAPI application and routes
│   ├── main.py              # Entry point
│   ├── routes/              # Individual route modules
│   └── tasks.py             # Celery async tasks
├── data_pipeline/           # Data collection and processing
│   ├── satellite_fetcher.py # Landsat/Sentinel data
│   ├── crowdsource_fetcher.py # Social media data
│   ├── preprocessor.py      # Image alignment and correction
│   ├── index_calculator.py  # NDVI, NDWI, NBR indices
│   └── severity_resolver.py # Severity score aggregation
├── models/                  # ML models
│   ├── unet.py             # Damage segmentation
│   ├── hrnet.py            # Alternative segmentation
│   ├── fusion_model.py     # SAR + Optical fusion
│   ├── zone_predictor.py   # Zone prediction
│   └── resource_allocator.py # Resource optimization
├── training/               # Training scripts
│   ├── train_damage.py     # Damage classifier training
│   ├── train_zone.py       # Zone predictor training
│   ├── evaluate.py         # Evaluation metrics
│   └── augmentation.py     # Data augmentation
└── database/               # Database models and migrations
    ├── models.py           # SQLAlchemy ORM
    └── migrations/         # Alembic version control

data/
├── raw/                     # Raw data (Sentinel, Landsat, Crowdsource)
└── processed/              # Processed datasets and outputs

tests/                       # Unit tests
```

---

## Running Tests

```bash
pytest tests/
pytest tests/test_severity_resolver.py -v  # Single test file
```

---

## Docker Setup

Run services locally with Docker Compose:

```bash
docker-compose up
```

This starts:
- **web**: FastAPI application server
- **redis**: Message broker for Celery

---

## Deployment Notes

- Production deployments should use PostgreSQL + PostGIS for geospatial queries.
- Celery workers handle long-running satellite data processing tasks.
- Sentinel Hub and Google Earth Engine credentials should be provided via environment variables.

---

## Contributing

1. Create a feature branch: `git checkout -b your-feature`
2. Make changes with clear commit messages.
3. Add tests for new functionality.
4. Ensure all tests pass: `pytest`
5. Push and create a pull request.

---
