# INSTRUCTION 105: Satellite Imagery Layer (Layer 2)

## Overview
Layer 2 implements satellite damage assessment resolution using DamageAssessment records.

## Function: resolve_from_satellite(event_id, db_session)

### Purpose
Queries DamageAssessment table for satellite imagery analysis results and computes
an aggregate severity score from pixel-level damage metrics.

### Parameters
- `event_id` (str): Unique disaster event identifier  
- `db_session` (Any): SQLAlchemy database session for queries

### Returns
- `(computed_score, 'satellite_model')` if assessments exist
- `(None, None)` if no assessments found

### Severity Calculation
```
score = (sum of major_damage_pixels + sum of destroyed_pixels) / sum of total_pixels
```
- Aggregates across all assessments for the event
- Normalizes to 0-1 range (clamped at boundaries)
- Destroyed pixels weighted equally with major damage

### Priority
**Second priority** - checked after GDACS, before image analysis

### Implementation Details
- Queries all DamageAssessment records matching event_id
- Sums major_damage_pixels and destroyed_pixels across all records
- Divides by total_pixels for normalization
- Graceful error handling with warning logs
- Score clamped to [0.0, 1.0] range

### Connection to System
- Input: DamageAssessment records created by satellite_fetcher 
- Output: Satellite-derived severity score
