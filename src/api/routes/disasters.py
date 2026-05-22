"""Disaster event routes.

All API endpoints for managing disaster events:
- Creating new events
- Retrieving event details and damage maps
- Listing active disasters
- Getting aggregate statistics

GeoJSON conversion is handled here for damage maps because PostGIS
geometry objects cannot be directly serialized to JSON.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.database.connection import get_db
from src.database.models import DisasterEvent, DamageAssessment
from src.api.schemas import (
    DisasterEventCreate,
    DisasterEventResponse,
    DamageAssessmentResponse,
    DisasterEventListResponse,
)

router = APIRouter(tags=["disasters"], prefix="/api/disasters")


# ============================================================================
# LIST DISASTERS
# ============================================================================

@router.get("/", response_model=DisasterEventListResponse)
def list_active_disasters(
    skip: int = Query(0, ge=0, description="Number of events to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max events to return"),
    status: Optional[str] = Query(None, description="Filter by status: active, resolved, pending"),
    db: Session = Depends(get_db),
):
    """List disaster events with optional filtering and pagination.
    
    Returns active disasters by default. Can filter by status and paginate results.
    
    Query Parameters:
    - skip: Number of results to skip (default 0)
    - limit: Max results (default 20, max 100)
    - status: Filter by status (active, resolved, pending)
    
    Returns:
        DisasterEventListResponse with total count and paginated events
    """
    query = db.query(DisasterEvent)
    
    # Filter by status if provided
    if status:
        query = query.filter_by(status=status)
    else:
        # Default: only show active events
        query = query.filter_by(status="active")
    
    # Get total count before pagination
    total = query.count()
    
    # Apply pagination
    events = query.offset(skip).limit(limit).all()
    
    return DisasterEventListResponse(
        total=total,
        page=skip // limit + 1,
        limit=limit,
        events=[DisasterEventResponse.model_validate(e) for e in events],
    )


# ============================================================================
# GET SINGLE DISASTER
# ============================================================================

@router.get("/{event_id}", response_model=DisasterEventResponse)
def get_disaster(
    event_id: int,
    db: Session = Depends(get_db),
):
    """Get details of a specific disaster event by ID.
    
    Path Parameters:
    - event_id: The disaster event ID
    
    Returns:
        DisasterEventResponse with all event details
        
    Raises:
        HTTPException 404: If event not found
    """
    event = db.query(DisasterEvent).filter_by(id=event_id).first()
    
    if not event:
        raise HTTPException(
            status_code=404,
            detail=f"Disaster event with ID {event_id} not found",
        )
    
    return DisasterEventResponse.model_validate(event)


# ============================================================================
# CREATE DISASTER
# ============================================================================

@router.post("/", response_model=DisasterEventResponse, status_code=201)
def create_disaster(
    event_data: DisasterEventCreate,
    db: Session = Depends(get_db),
):
    """Create a new disaster event.
    
    Request Body:
        DisasterEventCreate with event_type, name, and optional fields
    
    Returns:
        DisasterEventResponse for the created event with auto-generated ID
        
    Status Code:
        201 Created — event successfully created
    """
    # Create new DisasterEvent ORM object
    db_event = DisasterEvent(
        event_type=event_data.event_type,
        name=event_data.name,
        magnitude=event_data.magnitude,
        start_time=event_data.start_time,
        source=event_data.source,
        status="pending",  # New events start as pending
    )
    
    # Add to session and commit
    db.add(db_event)
    db.commit()
    
    # Refresh to get auto-generated fields (id, created_at, etc.)
    db.refresh(db_event)
    
    return DisasterEventResponse.model_validate(db_event)


# ============================================================================
# DAMAGE MAP (GeoJSON)
# ============================================================================

@router.get("/{event_id}/damage-map")
def get_damage_map(
    event_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get damage assessment results as a GeoJSON FeatureCollection.
    
    Converts all damage zone geometries and properties to GeoJSON format
    suitable for mapping libraries (Leaflet, Mapbox, etc.).
    
    Path Parameters:
    - event_id: The disaster event ID
    
    Returns:
        GeoJSON FeatureCollection with damage zones as features
        Each feature includes damage_level, confidence_score, affected_population
        
    Raises:
        HTTPException 404: If event not found
    """
    # Verify event exists
    event = db.query(DisasterEvent).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(
            status_code=404,
            detail=f"Disaster event with ID {event_id} not found",
        )
    
    # Get all damage assessments for this event
    assessments = db.query(DamageAssessment).filter_by(event_id=event_id).all()
    
    # Convert to GeoJSON FeatureCollection
    features = []
    for assessment in assessments:
        if not assessment.damage_zones_geojson:
            continue
        
        try:
            import json
            geojson_data = json.loads(assessment.damage_zones_geojson)
            if geojson_data and "features" in geojson_data:
                for feature in geojson_data["features"]:
                    if "properties" not in feature:
                        feature["properties"] = {}
                    feature["properties"].update({
                        "id": assessment.id,
                        "damage_level": assessment.damage_level,
                        "confidence_score": float(assessment.confidence_score or assessment.confidence or 0.85),
                        "affected_population_estimate": assessment.affected_population_estimate,
                        "assessed_at": assessment.assessed_at.isoformat(),
                    })
                    features.append(feature)
        except Exception as e:
            print(f"Warning: Could not parse GeoJSON for assessment {assessment.id}: {e}")
            continue
    
    # Return FeatureCollection
    return {
        "type": "FeatureCollection",
        "features": features,
        "event_id": event_id,
        "event_name": event.name,
        "total_zones": len(features),
    }


# ============================================================================
# EVENT SUMMARY (AGGREGATE STATISTICS)
# ============================================================================

@router.get("/{event_id}/summary")
def get_event_summary(
    event_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get aggregate damage statistics for a disaster event.
    
    Returns summary statistics: zone counts by damage level, total affected
    population, and assessment timing.
    
    Path Parameters:
    - event_id: The disaster event ID
    
    Returns:
        Dictionary with aggregate statistics
        
    Raises:
        HTTPException 404: If event not found
    """
    # Verify event exists
    event = db.query(DisasterEvent).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(
            status_code=404,
            detail=f"Disaster event with ID {event_id} not found",
        )
    
    # Get all assessments for this event
    assessments = db.query(DamageAssessment).filter_by(event_id=event_id).all()
    
    # Count zones by damage level
    damage_counts = {
        "none": 0,
        "minor": 0,
        "moderate": 0,
        "severe": 0,
        "extreme": 0,
    }
    
    total_affected = 0
    avg_confidence = 0.0
    latest_assessment = None
    
    for assessment in assessments:
        # Count by damage level (support integer, string, or map representation)
        level = assessment.damage_level
        if isinstance(level, int):
            # map: 0->none, 1->minor, 2->moderate, 3->severe
            level_map = {0: "none", 1: "minor", 2: "moderate", 3: "severe"}
            level_str = level_map.get(level, "none")
        elif isinstance(level, str):
            level_str = level.lower()
        else:
            level_str = "none"

        if level_str in damage_counts:
            damage_counts[level_str] += 1
        
        # Sum affected population
        if assessment.affected_population_estimate:
            total_affected += assessment.affected_population_estimate
        
        # Average confidence
        conf = assessment.confidence_score or assessment.confidence or 0.85
        avg_confidence += float(conf)
        
        # Track latest assessment
        if not latest_assessment or assessment.assessed_at > latest_assessment:
            latest_assessment = assessment.assessed_at
    
    # Calculate average confidence
    if assessments:
        avg_confidence /= len(assessments)
    
    return {
        "event_id": event_id,
        "event_name": event.name,
        "event_type": event.event_type,
        "status": event.status,
        "total_zones_assessed": len(assessments),
        "damage_breakdown": damage_counts,
        "total_affected_population": total_affected,
        "average_confidence_score": round(avg_confidence, 3),
        "latest_assessment_time": latest_assessment.isoformat() if latest_assessment else None,
        "event_created_at": event.created_at.isoformat() if event.created_at else None,
    }


# ============================================================================
# UPDATE EVENT STATUS
# ============================================================================

@router.patch("/{event_id}/status")
def update_event_status(
    event_id: int,
    new_status: str = Query(..., description="New status: pending, active, resolved"),
    db: Session = Depends(get_db),
) -> DisasterEventResponse:
    """Update the status of a disaster event.
    
    Path Parameters:
    - event_id: The disaster event ID
    
    Query Parameters:
    - new_status: One of pending, active, resolved
    
    Returns:
        Updated DisasterEventResponse
        
    Raises:
        HTTPException 404: If event not found
        HTTPException 422: If status is invalid
    """
    # Validate status
    valid_statuses = {"pending", "active", "resolved"}
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{new_status}'. Must be one of: {', '.join(valid_statuses)}",
        )
    
    # Get event
    event = db.query(DisasterEvent).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(
            status_code=404,
            detail=f"Disaster event with ID {event_id} not found",
        )
    
    # Update status
    event.status = new_status
    db.commit()
    db.refresh(event)
    
    return DisasterEventResponse.model_validate(event)
