# INSTRUCTION 104: GDACS Alert Layer (Layer 1)

## Overview
Layer 1 implements GDACS alert score resolution for disaster severity assessment.

## Function: resolve_from_gdacs(event_id, db_session)

### Purpose
Queries the DisasterEvent table for a GDACS alert score that has been previously 
fetched from external GDACS feed.

### Parameters
- `event_id` (str): Unique disaster event identifier
- `db_session` (Any): SQLAlchemy database session for queries

### Returns
- `(score, 'gdacs')` if gdacs_alert_score exists and is not None
- `(None, None)` otherwise

### Priority
**Highest priority** - checked first in 4-layer resolution cascade

### Implementation Details
- Queries DisasterEvent by event_id
- Checks for gdacs_alert_score field existence and non-None value
- Graceful error handling logs warnings but doesn't block
- Score is 0-1 normalized from GDACS API

### Connection to System
- Input: DisasterEvent records with gdacs_alert_score set by gdacs_fetcher
- Output: Severity score used for CrowdsourceReport severity_score field
