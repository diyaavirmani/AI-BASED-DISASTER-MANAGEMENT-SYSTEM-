"""Resource management and allocation routes.

Endpoints for:
- Listing and creating resources
- Optimal allocation recommendations via Dijkstra routing
- Tracking resource deployments
- Computing allocation algorithms
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from src.database.connection import get_db
from src.database.models import Resource, ResourceDeployment, DamageAssessment
from src.api.schemas import ResourceCreate, ResourceResponse, ResourceListResponse
from src.models.resource_allocator import (
    allocate_resources,
    AllocationRecommendation,
)

router = APIRouter(tags=["resources"], prefix="/api/resources")


# ============================================================================
# LIST RESOURCES
# ============================================================================

@router.get("/", response_model=ResourceListResponse)
def list_resources(
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    status: Optional[str] = Query(None, description="Filter by status: available, deployed, exhausted"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all resources with optional filtering.
    
    Query Parameters:
    - resource_type: Filter by type (shelter, water, medical, food, etc.)
    - status: Filter by deployment status (available, deployed, exhausted)
    - skip: Number of results to skip
    - limit: Max results to return
    
    Returns:
        ResourceListResponse with total count and paginated resources
    """
    query = db.query(Resource)
    
    # Apply filters
    if resource_type:
        query = query.filter_by(resource_type=resource_type)
    if status:
        query = query.filter_by(status=status)
    
    total = query.count()
    resources = query.offset(skip).limit(limit).all()
    
    return ResourceListResponse(
        total=total,
        page=skip // limit + 1,
        limit=limit,
        resources=[ResourceResponse.model_validate(r) for r in resources],
    )


# ============================================================================
# CREATE RESOURCE
# ============================================================================

@router.post("/", response_model=ResourceResponse, status_code=201)
def create_resource(
    data: ResourceCreate,
    db: Session = Depends(get_db),
):
    """Create a new resource.
    
    Request Body:
        ResourceCreate with resource_type, quantity, and optional location
    
    Returns:
        ResourceResponse for the created resource
        
    Status Code:
        201 Created
    """
    # Create Resource ORM object
    db_resource = Resource(
        resource_type=data.resource_type,
        quantity=data.quantity,
        status="available",
        latitude=data.latitude,
        longitude=data.longitude,
    )
    
    db.add(db_resource)
    db.commit()
    db.refresh(db_resource)
    
    return ResourceResponse.model_validate(db_resource)


# ============================================================================
# GET ALLOCATION RECOMMENDATIONS
# ============================================================================

@router.get("/allocate/{event_id}")
def get_allocation_recommendations(
    event_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get optimal resource allocation recommendations for a disaster event.
    
    Uses priority scoring and Dijkstra routing to recommend which resources
    should be deployed to which damaged zones and in what order.
    
    Path Parameters:
    - event_id: The disaster event ID
    
    Returns:
        Dictionary with ranked allocation recommendations
        Each includes zone details, recommended resources, route, and priority
        
    Raises:
        HTTPException 404: If event not found or no damage zones
    """
    # Get all damage zones for this event
    damage_zones = db.query(DamageAssessment).filter_by(event_id=event_id).all()
    
    if not damage_zones:
        raise HTTPException(
            status_code=404,
            detail=f"No damage zones found for event {event_id}",
        )
    
    # Get all available resources
    available_resources = db.query(Resource).filter_by(status="available").all()
    
    if not available_resources:
        return {
            "event_id": event_id,
            "recommendations": [],
            "warning": "No available resources in the system",
        }
    
    # Call allocation engine
    try:
        recommendations = allocate_resources(
            damage_zones=damage_zones,
            available_resources=available_resources,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Allocation algorithm failed: {str(e)}",
        )
    
    # Convert recommendations to JSON-serializable format
    recommendations_data = []
    for rec in recommendations:
        rec_dict = {
            "zone_id": rec.zone_id,
            "zone_damage_level": rec.zone_damage_level,
            "priority_score": float(rec.priority_score),
            "recommended_resources": rec.recommended_resources,
            "estimated_arrival_minutes": rec.estimated_arrival_minutes,
            "route_geojson": rec.route_geojson,
            "rationale": rec.rationale,
        }
        recommendations_data.append(rec_dict)
    
    return {
        "event_id": event_id,
        "total_recommendations": len(recommendations_data),
        "recommendations": recommendations_data,
        "generated_at": datetime.utcnow().isoformat(),
    }


# ============================================================================
# DEPLOY RESOURCE
# ============================================================================

@router.post("/deploy")
def deploy_resource(
    deployment_data: Dict[str, Any],
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Deploy a resource to a specific damage zone.
    
    Creates a deployment record, updates resource status, and tracks
    estimated arrival time based on distance and road conditions.
    
    Request Body:
        {
            "resource_id": int,
            "zone_id": int,
            "quantity_deployed": int,
            "estimated_arrival_minutes": int
        }
    
    Returns:
        Deployment confirmation with tracking details
    """
    required_fields = {"resource_id", "zone_id", "quantity_deployed"}
    if not all(field in deployment_data for field in required_fields):
        raise HTTPException(
            status_code=422,
            detail=f"Missing required fields: {required_fields}",
        )
    
    resource_id = deployment_data.get("resource_id")
    zone_id = deployment_data.get("zone_id")
    quantity_deployed = deployment_data.get("quantity_deployed")
    estimated_arrival = deployment_data.get("estimated_arrival_minutes", 30)
    
    # Validate resource exists and has sufficient quantity
    resource = db.query(Resource).filter_by(id=resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail=f"Resource {resource_id} not found")
    
    if resource.quantity < quantity_deployed:
        raise HTTPException(
            status_code=422,
            detail=f"Insufficient quantity. Available: {resource.quantity}, requested: {quantity_deployed}",
        )
    
    # Validate zone exists
    zone = db.query(DamageAssessment).filter_by(id=zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone {zone_id} not found")
    
    # Create deployment record
    deployment = ResourceDeployment(
        resource_id=resource_id,
        zone_id=zone_id,
        quantity_deployed=quantity_deployed,
        status="en_route",
        estimated_arrival=datetime.utcnow() + timedelta(minutes=estimated_arrival),
    )
    
    db.add(deployment)
    
    # Update resource: reduce quantity and mark as deployed if fully allocated
    resource.quantity -= quantity_deployed
    if resource.quantity == 0:
        resource.status = "deployed"
    
    db.commit()
    db.refresh(deployment)
    db.refresh(resource)
    
    return {
        "deployment_id": deployment.id,
        "resource_id": resource_id,
        "resource_type": resource.resource_type,
        "zone_id": zone_id,
        "quantity_deployed": quantity_deployed,
        "status": deployment.status,
        "estimated_arrival": deployment.estimated_arrival.isoformat(),
        "remaining_quantity": resource.quantity,
    }


# ============================================================================
# GET DEPLOYMENTS FOR EVENT
# ============================================================================

@router.get("/deployments/{event_id}")
def get_deployments(
    event_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get all active deployments for a disaster event.
    
    Returns current status of all resources deployed to this event,
    including estimated arrival times and routes.
    
    Path Parameters:
    - event_id: The disaster event ID
    
    Returns:
        Dictionary with deployment tracking information
    """
    # Get all zones for this event
    zones = db.query(DamageAssessment).filter_by(event_id=event_id).all()
    zone_ids = [z.id for z in zones]
    
    if not zone_ids:
        return {
            "event_id": event_id,
            "deployments": [],
            "total_active": 0,
        }
    
    # Get all deployments to these zones
    deployments = db.query(ResourceDeployment).filter(
        ResourceDeployment.zone_id.in_(zone_ids)
    ).all()
    
    # Format deployment data
    deployment_data = []
    for dep in deployments:
        resource = db.query(Resource).filter_by(id=dep.resource_id).first()
        zone = db.query(DamageAssessment).filter_by(id=dep.zone_id).first()
        
        if resource and zone:
            dep_dict = {
                "deployment_id": dep.id,
                "resource_type": resource.resource_type,
                "quantity_deployed": dep.quantity_deployed,
                "zone_damage_level": zone.damage_level,
                "status": dep.status,
                "estimated_arrival": dep.estimated_arrival.isoformat(),
                "created_at": dep.created_at.isoformat() if dep.created_at else None,
            }
            deployment_data.append(dep_dict)
    
    return {
        "event_id": event_id,
        "total_active": len(deployment_data),
        "deployments": deployment_data,
    }


# ============================================================================
# UPDATE DEPLOYMENT STATUS
# ============================================================================

@router.patch("/deployments/{deployment_id}/status")
def update_deployment_status(
    deployment_id: int,
    new_status: str = Query(..., description="New status: en_route, arrived, distributed, completed"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Update the status of a resource deployment.
    
    Tracks deployment progress from dispatch through final distribution.
    
    Path Parameters:
    - deployment_id: The deployment record ID
    
    Query Parameters:
    - new_status: One of en_route, arrived, distributed, completed
    
    Returns:
        Updated deployment record
    """
    valid_statuses = {"en_route", "arrived", "distributed", "completed"}
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
        )
    
    deployment = db.query(ResourceDeployment).filter_by(id=deployment_id).first()
    if not deployment:
        raise HTTPException(status_code=404, detail=f"Deployment {deployment_id} not found")
    
    deployment.status = new_status
    if new_status == "completed":
        deployment.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(deployment)
    
    return {
        "deployment_id": deployment.id,
        "status": deployment.status,
        "completed_at": deployment.completed_at.isoformat() if deployment.completed_at else None,
    }
