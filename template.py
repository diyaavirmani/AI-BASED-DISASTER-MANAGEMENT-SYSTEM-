#!/usr/bin/env python3
"""
template.py

Create a project directory structure and placeholder files matching
the repository layout shown in the project documentation.

Run from the repository root:
    python template.py

This script will NOT overwrite existing files; it will only create
missing directories/files with brief placeholder content.
"""
import os
from pathlib import Path

PROJECT_FILES = {
    "data/raw/sentinel1/.keep": "# raw sentinel1 data",
    "data/raw/sentinel2/.keep": "# raw sentinel2 data",
    "data/raw/landsat/.keep": "# raw landsat data",
    "data/raw/crowdsource/.keep": "# raw crowdsource data",
    "data/processed/datasets/.keep": "# processed datasets",
    "data/processed/indices/.keep": "# indices outputs",
    "data/processed/geojson/.keep": "# geojson files",

    "src/data_pipeline/satellite_fetcher.py": """# Satellite/ Landsat/ Sentinel API calls\n""",
    "src/data_pipeline/crowdsource_fetcher.py": """# Social media scraper\n""",
    "src/data_pipeline/preprocessor.py": """# CCD, alignment, correction\n""",
    "src/data_pipeline/index_calculator.py": """# NDVI, NDWI, NBR calculators\n""",

    "src/models/unet.py": """# U-Net architecture placeholder\n""",
    "src/models/hrnet.py": """# HRNet architecture placeholder\n""",
    "src/models/sam_prompter.py": """# SAM + RSPrompter integration placeholder\n""",
    "src/models/fusion_model.py": """# SAR + Optical fusion model placeholder\n""",
    "src/models/zone_predictor.py": """# LSTM / zone prediction model placeholder\n""",
    "src/models/resource_allocator.py": """# Routing & optimization placeholder\n""",

    "src/training/train_damage.py": """# Train damage classifier\n""",
    "src/training/train_zone.py": """# Train zone predictor\n""",
    "src/training/evaluate.py": """# Evaluation metrics & scripts\n""",
    "src/training/augmentation.py": """# Data augmentation utilities\n""",

    "src/api/main.py": """# FastAPI app entry point\nfrom fastapi import FastAPI\napp = FastAPI()\n\n@app.get('/'):\nasync def root():\n    return {'status': 'ok'}\n""",
    "src/api/routes/__init__.py": "# API routes package",
    "src/api/tasks.py": """# Celery tasks and async workers\n""",

    "src/schemas.py": """# Pydantic data models\n""",
    "src/database/models.py": """# SQLAlchemy ORM models\n""",
    "src/database/migrations/.keep": "# alembic migrations",

    "frontend/src/components/.keep": "# React components",
    "frontend/src/pages/.keep": "# React pages",
    "frontend/src/services/.keep": "# frontend API services",

    "notebooks/01_data_exploration.ipynb": "{\n \"cells\": [],\n \"metadata\": {},\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}",
    "notebooks/02_model_experiments.ipynb": "{\n \"cells\": [],\n \"metadata\": {},\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}",
    "notebooks/03_evaluation.ipynb": "{\n \"cells\": [],\n \"metadata\": {},\n \"nbformat\": 4,\n \"nbformat_minor\": 5\n}",

    "tests/.keep": "# test placeholders",
    "configs/.keep": "# config files",
    "docker/.keep": "# docker files",
    "docs/.keep": "# documentation",

    ".env": "# Environment variables (DO NOT COMMIT actual secrets)\n",
    ".gitignore": "# Ignore environment and data\n.env\ndata/raw/\n",
    "README.md": "# AI-Based Disaster Management System\n\nProject scaffold created by template.py\n",
    "requirements.txt": "# See project docs for recommended packages\n",
    "docker-compose.yml": "# docker-compose placeholder\n",
}


def ensure_parent(path: Path):
    parent = path.parent
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)


def create_project_files(base_dir: Path):
    created = []
    skipped = []
    for rel, content in PROJECT_FILES.items():
        target = base_dir / rel
        ensure_parent(target)
        if target.exists():
            skipped.append(rel)
            continue
        # write binary for ipynb-like files; use text otherwise
        mode = "wb" if rel.endswith('.ipynb') else "w"
        data = content.encode('utf-8') if mode == 'wb' else content
        with open(target, mode) as f:
            f.write(data)
        created.append(rel)
    return created, skipped


def main():
    base = Path.cwd()
    print(f"Creating project scaffold in {base}")
    created, skipped = create_project_files(base)
    print("\nCreated files:")
    for p in created:
        print(" -", p)
    if skipped:
        print('\nSkipped (already exist):')
        for p in skipped:
            print(" -", p)


if __name__ == '__main__':
    main()
