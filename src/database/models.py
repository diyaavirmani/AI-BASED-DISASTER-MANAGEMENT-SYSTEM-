# SQLAlchemy ORM models
# This file stores database models for the disaster management system

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class ReportModel:
    """Stub for report model."""
    def __init__(self):
        logging.debug("ReportModel initialized")


class DisasterEvent:
    """Model for disaster events with GDACS alert scores.
    
    Fields:
        id: Unique event identifier
        event_name: Name of the disaster event
        gdacs_alert_score: GDACS alert severity score (0-1), None if not available
        created_at: Event creation timestamp
    """
    def __init__(self, id: str, event_name: str = "", gdacs_alert_score: Optional[float] = None):
        self.id = id
        self.event_name = event_name
        self.gdacs_alert_score = gdacs_alert_score
        self.created_at = datetime.utcnow()
        logger.debug(f"DisasterEvent initialized: {id} with score {gdacs_alert_score}")


class DamageAssessment:
    """Model for satellite imagery damage assessments.
    
    Fields:
        id: Unique assessment identifier
        event_id: Foreign key to DisasterEvent
        major_damage_pixels: Number of pixels with major damage
        destroyed_pixels: Number of pixel completely destroyed
        total_pixels: Total number of pixels in assessment
        assessment_date: When the assessment was created
    """
    def __init__(
        self,
        id: str,
        event_id: str,
        major_damage_pixels: int = 0,
        destroyed_pixels: int = 0,
        total_pixels: int = 0
    ):
        self.id = id
        self.event_id = event_id
        self.major_damage_pixels = major_damage_pixels
        self.destroyed_pixels = destroyed_pixels
        self.total_pixels = total_pixels
        self.assessment_date = datetime.utcnow()
        logger.debug(
            f"DamageAssessment initialized: event_id={event_id}, "
            f"major={major_damage_pixels}, destroyed={destroyed_pixels}, total={total_pixels}"
        )


class CrowdsourceReport:
    """Model for cleaned crowdsourced disaster reports with severity.
    
    Fields:
        id: Unique report identifier
        event_id: Foreign key to DisasterEvent
        text: Cleaned text content
        severity_score: Resolved severity score (0-1)
        severity_source: Source of severity determination (gdacs, satellite_model, image_analysis, text_keywords)
        severity_label: Human readable label (critical, severe, moderate, minor, minimal, unknown)
        severity_resolved: Whether severity was successfully determined
        created_at: When the report was created
    """
    def __init__(
        self,
        id: str,
        event_id: str,
        text: str = "",
        severity_score: Optional[float] = None,
        severity_source: str = "unresolved",
        severity_label: str = "unknown",
        severity_resolved: bool = False
    ):
        self.id = id
        self.event_id = event_id
        self.text = text
        self.severity_score = severity_score
        self.severity_source = severity_source
        self.severity_label = severity_label
        self.severity_resolved = severity_resolved
        self.created_at = datetime.utcnow()
        logger.debug(f"CrowdsourceReport initialized: {id} with severity {severity_label}")
