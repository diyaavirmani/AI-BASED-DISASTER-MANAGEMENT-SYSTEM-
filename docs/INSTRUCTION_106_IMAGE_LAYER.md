# INSTRUCTION 106: Image Analysis Layer (Layer 3)

## Overview
Layer 3 implements social media image analysis resolution using CLIP model classifications.

## Function: resolve_from_image(image_analysis_results)

### Purpose
Processes image analysis results from social_image_analyzer.py, maps CLIP severity 
labels to numeric scores, filters by confidence threshold, and returns highest score.

### Parameters
- `image_analysis_results` (List[Dict]): List of image analysis dicts with:
  - `severity` (str): CLIP label ('catastrophic', 'severe', 'moderate', 'minor', 'none')
  - `severity_confidence` (float): Confidence score 0-1

### Returns  
- `(highest_score, 'image_analysis')` if qualifying results exist
- `(None, None)` if no results or all below threshold

### Severity Label Mapping
```
catastrophic  → 1.0
severe        → 0.75
moderate      → 0.5
minor         → 0.25
none          → 0.0
```

### Confidence Threshold
- Requires `severity_confidence > 0.6` to qualify
- Filters low-confidence predictions automatically
- Returns MAX score across all qualifying images

### Priority
**Third priority** - checked after satellite, before text keywords

### Implementation Details
- Case-insensitive label matching
- Filters results by confidence threshold
- Collects all qualifying scores
- Returns maximum score for ensemble strength
- Handles empty results gracefully

### Connection to System  
- Input: Image analysis results from social_image_analyzer.py
- Output: Image-derived severity score when images available
