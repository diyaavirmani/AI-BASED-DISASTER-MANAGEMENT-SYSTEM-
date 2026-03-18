# SEVERITY RESOLUTION ARCHITECTURE

## Overview
The severity resolution system uses a 4-layer cascade architecture to determine 
disaster event severity from multiple data sources, ensuring robustness and 
leveraging all available information.

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  Disaster Report Processing (nlp_filter.filter_and_enrich)     │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
    ┌────────────────────────────────────────────────┐
    │  resolve_severity() ORCHESTRATOR FUNCTION     │
    │  (Priority-based layer cascade)               │
    └────────────────────────────────────────────────┘
           │          │          │          │
           ▼          ▼          ▼          ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ LAYER 1  │ │ LAYER 2  │ │ LAYER 3  │ │ LAYER 4  │
    │  GDACS   │ │SATELLITE │ │  IMAGE   │ │  TEXT    │
    │          │ │IMAGERY   │ │ ANALYSIS │ │KEYWORDS  │
    └──▲───────┘ └──▲───────┘ └──▲───────┘ └──▲───────┘
       │            │            │            │
       │            │            │            │
       └─ DisasterEvent.gdacs_alert_score
       └─ DamageAssessment.{major_damage, destroyed, total}
       └─ image_analysis_results.{severity, confidence}
       └─ CrowdsourceReport.text with SEVERITY_KEYWORDS

           ▼ (First non-None score)
    
    ┌────────────────────────────────────┐
    │  RESULT TUPLE                      │
    │  (score, source, label)            │
    └────────────────────────────────────┘
           │
           ▼
    ┌────────────────────────────────────┐
    │  format_severity_result()          │
    │  Returns {score, source, label,    │
    │           resolved}                │
    └────────────────────────────────────┘
           │
           ▼
    ┌────────────────────────────────────┐
    │  Merged into CrowdsourceReport     │
    │  Stored in database                │
    └────────────────────────────────────┘
```

## Layer Priority Cascade

The system checks layers in strict priority order. **First layer with non-None score wins:**

| Priority | Layer | Source | Quality | Fallback? |
|----------|-------|--------|---------|-----------|
| 1 (First) | GDACS | DisasterEvent.gdacs_alert_score | Official alert | No |
| 2        | Satellite | DamageAssessment pixels | Objective imagery | If no GDACS |
| 3        | Image Analysis | CLIP model classification | Community photos | If no satellite |
| 4 (Last) | Text Keywords | SEVERITY_KEYWORDS matching | Report text | If nothing else |
| 5 (None) | Unresolved | None | No data | If all layers fail |

## Data Flow Integration

```
Social Media Input
    │
    ├─► nlp_filter.filter_relevant_reports()
    │
    ├─► Text Processing
    │   └─► cleaned_text
    │
    ├─► Image Analysis  
    │   └─► image_analysis_results (from social_image_analyzer)
    │
    └─► resolve_severity(cleaned_text, image_results, event_id, db_session)
        │
        ├─ Query Layer 1: DisasterEvent.gdacs_alert_score
        ├─ Query Layer 2: DamageAssessment records  
        ├─ Process Layer 3: image_analysis_results
        └─ Check Layer 4: SEVERITY_KEYWORDS in text
        │
        └─► format_severity_result()
            │
            └─► Merge into report dictionary
                │
                └─► Store complete CrowdsourceReport
```

## Key Components

### SEVERITY_KEYWORDS (Layer 4 Foundation)
- 14 keyword/phrase → score mappings  
- Scores range 0-1 (0.05 to 1.0)
- Case-insensitive substring matching
- Multi-word phrase support (e.g., "total destruction")

### Result Dictionary Structure
```python
{
    'severity_score': float or None,      # 0-1 or None
    'severity_source': str,               # Layer source
    'severity_label': str,                # Human-readable
    'severity_resolved': bool,            # Success flag
}
```

### Severity Label Mapping
- >= 0.8 → "critical" (emergency)
- 0.6-0.8 → "severe" (urgent)
- 0.4-0.6 → "moderate" (significant)  
- 0.2-0.4 → "minor" (limited)
- < 0.2 → "minimal" (negligible)
- None → "unknown" (unresolved)

## Design Rationale

1. **Priority by Reliability**: GDACS (official) > Satellite (objective) > Image (reliable ML) > Text (subjective)

2. **Short-Circuit Evaluation**: Returns immediately on first valid score for efficiency

3. **Graceful Degradation**: Continues to next layer if one fails or has no data

4. **Comprehensive Logging**: Debug logs at each layer for troubleshooting

5. **Separation of Concerns**: Each layer is independent, testable function

6. **Database-Backed**: Leverages existing database tables for data persistence
