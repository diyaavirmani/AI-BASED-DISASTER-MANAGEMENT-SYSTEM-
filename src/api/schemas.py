"""API request and response schemas using Pydantic.

These schemas define the shape of data for all API endpoints. They handle:
- Request validation: ensuring clients send properly typed data
- Response filtering: exposing only intended fields to clients
- Type coercion: converting strings to ints/floats when appropriate
- Documentation: FastAPI uses these to generate OpenAPI docs

Key distinction from database models (models.py):
- Database models define the schema and how data is stored
- API schemas define what clients see and send
- A database model may have internal fields; the API schema exposes only public fields
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime


# ============================================================================
# DISASTER EVENT SCHEMAS
# ============================================================================

class DisasterEventCreate(BaseModel):
    """Request schema for creating a new disaster event.
    
    Only required field is event_type. Other fields are optional with
    sensible defaults. FastAPI will reject requests missing event_type.
    """
    event_type: str = Field(..., description="Type of disaster: earthquake, flood, fire, etc.")
    name: str = Field(..., description="Human-readable event name")
    magnitude: Optional[float] = Field(None, description="Event magnitude (e.g., earthquake Richter scale)")
    start_time: Optional[datetime] = Field(None, description="When the disaster started")
    source: Optional[str] = Field(None, description="Data source (GDACS, crowdsource, etc.)")


class DisasterEventResponse(BaseModel):
    """Response schema for disaster events returned by the API.
    
    Includes all fields that clients need to know about. The from_attributes=True
    allows FastAPI to automatically convert SQLAlchemy ORM objects to this schema.
    """
    id: int = Field(..., description="Unique database ID")
    event_type: str
    name: str
    magnitude: Optional[float] = None
    start_time: Optional[datetime] = None
    source: Optional[str] = None
    status: str = Field(..., description="Current status: pending, active, resolved")
    gdacs_alert_score: Optional[float] = Field(None, description="Alert score from GDACS if applicable")
    affected_area_km2: Optional[float] = Field(None, description="Estimated affected area")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# DAMAGE ASSESSMENT SCHEMAS
# ============================================================================

class DamageAssessmentResponse(BaseModel):
    """Response schema for damage assessment results.
    
    Returned after inference on satellite imagery. Note: geometry field is
    excluded — GeoJSON geometries are handled separately in the route handler
    to avoid serialization issues with PostGIS types.
    """
    id: int
    event_id: int = Field(..., description="ID of the related disaster event")
    assessed_at: datetime
    damage_level: str = Field(..., description="Damage level: none, minor, moderate, severe, extreme")
    confidence_score: float = Field(..., description="Model confidence 0-1")
    affected_population_estimate: Optional[int] = Field(None, description="Estimated people affected")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# RESOURCE SCHEMAS
# ============================================================================

class ResourceCreate(BaseModel):
    """Request schema for adding a new resource.
    
    Clients send latitude/longitude as raw floats. The route handler converts
    these to PostGIS Point objects for storage. Never expose raw database
    geometry types in API schemas.
    """
    resource_type: str = Field(..., description="Type: shelter, water, medical, food, etc.")
    quantity: int = Field(..., description="Quantity available", ge=0)
    latitude: Optional[float] = Field(None, description="Geographic latitude", ge=-90, le=90)
    longitude: Optional[float] = Field(None, description="Geographic longitude", ge=-180, le=180)


class ResourceResponse(BaseModel):
    """Response schema for resources.
    
    Converts PostGIS Point geometry back to lat/lon floats for API clients.
    """
    id: int
    resource_type: str
    quantity: int
    status: str = Field(..., description="Current status: available, deployed, exhausted")
    last_updated: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# CROWDSOURCE REPORT SCHEMAS
# ============================================================================

class CrowdsourceReportResponse(BaseModel):
    """Response schema for crowdsourced disaster reports.
    
    Social media, SMS, and user submissions are validated and scored for
    severity. This schema exposes the processed report data.
    """
    id: int
    source: str = Field(..., description="Data source: twitter, telegram, sms, web_form, etc.")
    text: str = Field(..., description="Original report text")
    reported_at: datetime
    disaster_type: Optional[str] = Field(None, description="Detected disaster type")
    severity_score: float = Field(..., description="NLP-derived severity 0-1")
    severity_label: str = Field(..., description="Severity label: low, medium, high, critical")
    severity_resolved: bool = Field(False, description="Whether severity was manually verified")
    verified: bool = Field(False, description="Whether a human reviewed this report")
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# ZONE PREDICTION SCHEMAS
# ============================================================================

class ZonePredictionResponse(BaseModel):
    """Response schema for zone-level risk predictions.
    
    LSTM-based predictions of high-risk zones for proactive resource allocation.
    """
    id: int
    event_id: int
    zone_name: str
    risk_score: float = Field(..., description="Predicted risk 0-1")
    predicted_affected_population: Optional[int] = None
    prediction_timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# INFERENCE REQUEST/RESPONSE SCHEMAS
# ============================================================================

class PredictRequest(BaseModel):
    """Request schema for triggering damage assessment inference.
    
    Clients specify the event and which preprocessed tiles to run inference on.
    Processing is queued asynchronously and returns immediately with a task ID.
    """
    event_id: int = Field(..., description="ID of the disaster event")
    tile_paths: List[str] = Field(..., description="Paths to preprocessed satellite tiles")


class PredictResponse(BaseModel):
    """Response schema for inference requests.
    
    Returned immediately. The actual results are available via the task_id
    using a separate status endpoint.
    """
    event_id: int
    zones_detected: int = Field(..., description="Number of damage zones identified")
    processing_time_seconds: float = Field(..., description="Time to queue inference")
    task_id: str = Field(..., description="Async task ID to check status later")


# ============================================================================
# BATCH OPERATIONS
# ============================================================================

class DisasterEventListResponse(BaseModel):
    """Response schema for listing disaster events with pagination info."""
    total: int
    page: int
    limit: int
    events: List[DisasterEventResponse]


class ResourceListResponse(BaseModel):
    """Response schema for listing resources."""
    total: int
    page: int
    limit: int
    resources: List[ResourceResponse]


# ============================================================================
# ERROR RESPONSE SCHEMAS
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response format."""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Machine-readable error code")
    request_id: Optional[str] = Field(None, description="Trace ID for debugging")
