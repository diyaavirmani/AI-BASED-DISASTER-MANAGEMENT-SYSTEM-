"""
Determines the final severity score for a disaster report by checking 
multiple sources in priority order (4 layers).

This module uses a layered approach:
  Layer 1: GDACS alert score from database
  Layer 2: Satellite imagery damage assessment
  Layer 3: Social media image analysis  
  Layer 4: Text keyword analysis
  
The first layer with a non-None score is used. If all layers return None,
the severity is marked as unresolved.
"""

import logging
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger(__name__)

# INSTRUCTION 103: SEVERITY_KEYWORDS constant
SEVERITY_KEYWORDS: Dict[str, float] = {
    "catastrophic": 1.0,
    "apocalyptic": 1.0,
    "total destruction": 0.95,
    "completely destroyed": 0.9,
    "massive": 0.8,
    "severe": 0.75,
    "widespread": 0.7,
    "significant": 0.5,
    "moderate": 0.5,
    "partial": 0.45,
    "minor": 0.25,
    "small": 0.2,
    "slight": 0.15,
    "negligible": 0.05,
}


# INSTRUCTION 104: Layer 1 - GDACS resolution
def resolve_from_gdacs(event_id: str, db_session: Any) -> Tuple[Optional[float], Optional[str]]:
    """
    Layer 1: Query database for GDACS alert score.
    
    Attempts to get severity score from the DisasterEvent record's
    gdacs_alert_score field if it exists.
    
    Parameters
    ----------
    event_id : str
        Unique identifier for the disaster event
    db_session : Any
        SQLAlchemy database session
        
    Returns
    -------
    Tuple[Optional[float], Optional[str]]
        (score, 'gdacs') if gdacs_alert_score exists and is not None,
        (None, None) otherwise
    """
    try:
        # Query DisasterEvent table
        from src.database.models import DisasterEvent
        
        event = db_session.query(DisasterEvent).filter(
            DisasterEvent.id == event_id
        ).first()
        
        if event and hasattr(event, 'gdacs_alert_score') and event.gdacs_alert_score is not None:
            logger.info(f"Event {event_id}: Found GDACS score = {event.gdacs_alert_score}")
            return (event.gdacs_alert_score, 'gdacs')
    except Exception as e:
        logger.warning(f"Error querying GDACS for event {event_id}: {e}")
    
    return (None, None)


# INSTRUCTION 105: Layer 2 - Satellite imagery resolution
def resolve_from_satellite(event_id: str, db_session: Any) -> Tuple[Optional[float], Optional[str]]:
    """
    Layer 2: Query damage assessments from satellite imagery.
    
    Sums major_damage and destroyed pixels across all DamageAssessment
    records for this event, divides by total pixels to get a normalized score.
    
    Parameters
    ----------
    event_id : str
        Unique identifier for the disaster event
    db_session : Any
        SQLAlchemy database session
        
    Returns
    -------
    Tuple[Optional[float], Optional[str]]
        (computed_score, 'satellite_model') if assessments exist,
        (None, None) if no assessments found
    """
    try:
        from src.database.models import DamageAssessment
        
        assessments = db_session.query(DamageAssessment).filter(
            DamageAssessment.event_id == event_id
        ).all()
        
        if not assessments:
            logger.info(f"Event {event_id}: No satellite assessments found")
            return (None, None)
        
        total_major_damage = 0
        total_destroyed = 0
        total_pixels = 0
        
        for assessment in assessments:
            if hasattr(assessment, 'major_damage_pixels') and assessment.major_damage_pixels:
                total_major_damage += assessment.major_damage_pixels
            if hasattr(assessment, 'destroyed_pixels') and assessment.destroyed_pixels:
                total_destroyed += assessment.destroyed_pixels
            if hasattr(assessment, 'total_pixels') and assessment.total_pixels:
                total_pixels += assessment.total_pixels
        
        if total_pixels > 0:
            computed_score = (total_major_damage + total_destroyed) / total_pixels
            # Clamp to 0-1 range
            computed_score = min(1.0, max(0.0, computed_score))
            logger.info(f"Event {event_id}: Satellite score = {computed_score}")
            return (computed_score, 'satellite_model')
    except Exception as e:
        logger.warning(f"Error querying satellite assessments for event {event_id}: {e}")
    
    return (None, None)


# INSTRUCTION 106: Layer 3 - Social media image analysis resolution
def resolve_from_image(image_analysis_results: List[Dict[str, Any]]) -> Tuple[Optional[float], Optional[str]]:
    """
    Layer 3: Extract severity from social media image analysis.
    
    Maps CLIP severity labels to scores and filters by confidence threshold.
    Returns the highest score from qualifying results.
    
    Parameters
    ----------
    image_analysis_results : List[Dict[str, Any]]
        List of image analysis dicts from social_image_analyzer.py with fields:
        'severity' (label), 'severity_confidence' (float)
        
    Returns
    -------
    Tuple[Optional[float], Optional[str]]
        (highest_score, 'image_analysis') if any results qualify,
        (None, None) otherwise
    """
    # Severity label to score mapping
    severity_map = {
        'catastrophic': 1.0,
        'severe': 0.75,
        'moderate': 0.5,
        'minor': 0.25,
        'none': 0.0,
    }
    
    if not image_analysis_results:
        logger.info("No image analysis results provided")
        return (None, None)
    
    qualifying_scores = []
    
    for result in image_analysis_results:
        severity = result.get('severity', '').lower()
        confidence = result.get('severity_confidence', 0.0)
        
        # Filter to only results where confidence > 0.6
        if confidence > 0.6 and severity in severity_map:
            score = severity_map[severity]
            qualifying_scores.append(score)
            logger.debug(f"Image analysis: {severity} (confidence={confidence}) -> score={score}")
    
    if qualifying_scores:
        max_score = max(qualifying_scores)
        logger.info(f"Image analysis: max_score = {max_score} from {len(qualifying_scores)} images")
        return (max_score, 'image_analysis')
    
    logger.info("No qualifying image analysis results (confidence <= 0.6)")
    return (None, None)


# INSTRUCTION 107: Layer 4 - Text keyword resolution
def resolve_from_text(cleaned_text: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Layer 4: Extract severity from text using keyword matching.
    
    Searches cleaned text for keywords in SEVERITY_KEYWORDS dictionary
    and returns the highest matching score.
    
    Parameters
    ----------
    cleaned_text : str
        Cleaned/preprocessed text content
        
    Returns
    -------
    Tuple[Optional[float], Optional[str]]
        (max_score, 'text_keywords') if keywords found,
        (None, None) otherwise
    """
    if not cleaned_text:
        logger.info("No text provided for severity resolution")
        return (None, None)
    
    text_lower = cleaned_text.lower()
    matching_scores = []
    matched_keywords = []
    
    # Iterate through SEVERITY_KEYWORDS
    for keyword, score in SEVERITY_KEYWORDS.items():
        if keyword in text_lower:
            matching_scores.append(score)
            matched_keywords.append(keyword)
    
    if matching_scores:
        max_score = max(matching_scores)
        logger.info(f"Text keywords found: {matched_keywords} -> max_score = {max_score}")
        return (max_score, 'text_keywords')
    
    logger.info("No severity keywords found in text")
    return (None, None)


# INSTRUCTION 108: Main orchestrator function
def resolve_severity(
    text_result: str,
    image_results: List[Dict[str, Any]],
    event_id: str,
    db_session: Any
) -> Tuple[Optional[float], str, str]:
    """
    Main function to determine severity by checking 4 layers in priority order.
    
    Calls each layer function in order (GDACS -> Satellite -> Image -> Text).
    Returns the first (score, source) pair where score is not None.
    If ALL layers return None, returns (None, 'unresolved').
    Also generates a human-readable severity_label.
    
    Parameters
    ----------
    text_result : str
        Cleaned text content from the disaster report
    image_results : List[Dict[str, Any]]
        List of image analysis results
    event_id : str
        Unique event identifier
    db_session : Any
        SQLAlchemy database session
        
    Returns
    -------
    Tuple[Optional[float], str, str]
        (score, source, label) where:
        - score: float (0-1) or None
        - source: 'gdacs', 'satellite_model', 'image_analysis', 'text_keywords', or 'unresolved'
        - label: human-readable severity label
    """
    score = None
    source = None
    
    # Layer 1: GDACS
    logger.debug("Layer 1: Checking GDACS alert score...")
    score, source = resolve_from_gdacs(event_id, db_session)
    if score is not None:
        label = _compute_severity_label(score)
        logger.info(f"Resolved severity from Layer 1 (GDACS): {score} -> {label}")
        return (score, source, label)
    
    # Layer 2: Satellite
    logger.debug("Layer 2: Checking satellite assessments...")
    score, source = resolve_from_satellite(event_id, db_session)
    if score is not None:
        label = _compute_severity_label(score)
        logger.info(f"Resolved severity from Layer 2 (Satellite): {score} -> {label}")
        return (score, source, label)
    
    # Layer 3: Image Analysis
    logger.debug("Layer 3: Checking image analysis results...")
    score, source = resolve_from_image(image_results)
    if score is not None:
        label = _compute_severity_label(score)
        logger.info(f"Resolved severity from Layer 3 (Image): {score} -> {label}")
        return (score, source, label)
    
    # Layer 4: Text Keywords
    logger.debug("Layer 4: Checking text keywords...")
    score, source = resolve_from_text(text_result)
    if score is not None:
        label = _compute_severity_label(score)
        logger.info(f"Resolved severity from Layer 4 (Text): {score} -> {label}")
        return (score, source, label)
    
    # All layers returned None
    logger.warning(f"Event {event_id}: Unable to resolve severity from any layer")
    return (None, 'unresolved', 'unknown')


def _compute_severity_label(score: Optional[float]) -> str:
    """
    Convert numeric severity score to human-readable label.
    
    Parameters
    ----------
    score : Optional[float]
        Severity score (0-1) or None
        
    Returns
    -------
    str
        Label: 'critical', 'severe', 'moderate', 'minor', 'minimal', or 'unknown'
    """
    if score is None:
        return 'unknown'
    elif score >= 0.8:
        return 'critical'
    elif score >= 0.6:
        return 'severe'
    elif score >= 0.4:
        return 'moderate'
    elif score >= 0.2:
        return 'minor'
    else:
        return 'minimal'


# INSTRUCTION 109: Format the result for database storage
def format_severity_result(
    score: Optional[float],
    source: str,
    label: str
) -> Dict[str, Any]:
    """
    Format severity result into a clean dictionary for database storage.
    
    Parameters
    ----------
    score : Optional[float]
        Resolved severity score (0-1) or None
    source : str
        Source of the severity determination
    label : str
        Human-readable severity label
        
    Returns
    -------
    Dict[str, Any]
        Dictionary with keys:
        - severity_score: float or None
        - severity_source: str
        - severity_label: str  
        - severity_resolved: bool (False only when source is 'unresolved')
    """
    return {
        'severity_score': score,
        'severity_source': source,
        'severity_label': label,
        'severity_resolved': (source != 'unresolved'),
    }
