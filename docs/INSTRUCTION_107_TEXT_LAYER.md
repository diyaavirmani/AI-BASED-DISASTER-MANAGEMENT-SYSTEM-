# INSTRUCTION 107: Text Keywords Layer (Layer 4)

## Overview
Layer 4 implements text-based severity resolution using SEVERITY_KEYWORDS dictionary.

## Function: resolve_from_text(cleaned_text)

### Purpose
Searches cleaned text for severity keywords, collects all matching scores,
and returns the maximum score found.

### Parameters
- `cleaned_text` (str): Preprocessed disaster report text

### Returns
- `(max_score, 'text_keywords')` if keywords found
- `(None, None)` if no keywords match

### Severity Keywords (INSTRUCTION 103)
Dictionary mapping 14 keywords/phrases to scores:
```
catastrophic (1.0), apocalyptic (1.0)
total destruction (0.95), completely destroyed (0.9)
massive (0.8), severe (0.75)
widespread (0.7)
significant (0.5), moderate (0.5)
partial (0.45)
minor (0.25), small (0.2)
slight (0.15), negligible (0.05)
```

### Matching Behavior
- Case-insensitive (text converted to lowercase)
- Exact substring matching (supports multi-word phrases)
- No stemming or fuzzy matching
- Collects scores for ALL matches
- Returns highest score (not average)

### Priority
**Lowest priority** - checked last in 4-layer cascade

### Implementation Details
- Converts text to lowercase for matching
- Iterates through SEVERITY_KEYWORDS dictionary
- Collects scores for each match found
- Returns max() if any matches exist
- Handles empty/None text gracefully

### Connection to System
- Input: cleaned_text field from CrowdsourceReport
- Output: Text-derived severity score (fallback source)
- Provides baseline severity when other layers unavailable
