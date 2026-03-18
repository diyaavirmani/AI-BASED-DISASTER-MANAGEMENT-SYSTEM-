# INSTRUCTION 108 & 109: Main Orchestrator and Formatting

## Overview
Instructions 108-109 implement the main `resolve_severity()` orchestrator function
and the `format_severity_result()` formatting function.

## Function: resolve_severity(text_result, image_results, event_id, db_session)

### Purpose (INSTRUCTION 108)
Main orchestrator that calls all 4 layers in priority order and returns results from
the first layer that produces a non-None score. Also computes human-readable label.

### Parameters
- `text_result` (str): Cleaned text content
- `image_results` (List[Dict]): Image analysis results  
- `event_id` (str): Unique event identifier
- `db_session` (Any): Database session

### Returns
- `(score, source, label)` tuple where:
  - `score`: float 0-1 (or None for unresolved)
  - `source`: 'gdacs', 'satellite_model', 'image_analysis', 'text_keywords', or 'unresolved'
  - `label`: 'critical', 'severe', 'moderate', 'minor', 'minimal', or 'unknown'

### Layer Priority (Cascade Order)
1. **GDACS** - resolve_from_gdacs()
2. **Satellite** - resolve_from_satellite()
3. **Image Analysis** - resolve_from_image()
4. **Text Keywords** - resolve_from_text()

### Severity Label Mapping
```
score >= 0.8      → 'critical'
0.6 - 0.8         → 'severe'  
0.4 - 0.6         → 'moderate'
0.2 - 0.4         → 'minor'
< 0.2             → 'minimal'
None              → 'unknown'
```

### Implementation Details
- Calls layers in order 1→4
- Returns on first non-None score (short-circuit)
- If all layers return None, returns (None, 'unresolved', 'unknown')
- Comprehensive debug logging at each layer
- Handles exceptions gracefully

---

## Function: format_severity_result(score, source, label)

### Purpose (INSTRUCTION 109)
Formats severity determination into clean dictionary structure for database storage.

### Parameters
- `score` (Optional[float]): Severity score 0-1 or None
- `source` (str): Source identifier string
- `label` (str): Human-readable label

### Returns
Dictionary with keys:
```python
{
    'severity_score': float or None,
    'severity_source': str,
    'severity_label': str,
    'severity_resolved': bool  # False only when source is 'unresolved'
}
```

### Examples
```python
# Resolved from GDACS
format_severity_result(0.85, 'gdacs', 'critical')
# returns {'severity_score': 0.85, 'severity_source': 'gdacs', 
#          'severity_label': 'critical', 'severity_resolved': True}

# Unresolved
format_severity_result(None, 'unresolved', 'unknown')  
# returns {'severity_score': None, 'severity_source': 'unresolved',
#          'severity_label': 'unknown', 'severity_resolved': False}
```

### Usage
Output dict is merged directly into CrowdsourceReport document before storage:
```python
severity_dict = format_severity_result(score, source, label)
report.update(severity_dict)  # Adds all 4 fields to report
```
