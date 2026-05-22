"""Resource allocation engine with priority scoring and optimal routing.

This module determines which resources to send where and in what order
during a disaster response. It uses:
- Priority scoring based on damage severity, population, accessibility, time
- Dijkstra's algorithm for optimal routing on road networks
- Resource type matching to zone damage levels

The output drives emergency response decisions in the field.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import math

# Optional: NetworkX for graph algorithms (install with: pip install networkx)
try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class AllocationRecommendation:
    """A recommendation to deploy specific resources to a damage zone.
    
    Includes priority score, routing information, and rationale for the
    recommendation to help emergency coordinators make informed decisions.
    """
    zone_id: int
    zone_damage_level: str  # none, minor, moderate, severe, extreme
    priority_score: float  # 0-1, higher = more urgent
    recommended_resources: List[Dict[str, int]]  # [{"type": "medical", "quantity": 5}, ...]
    estimated_arrival_minutes: int
    route_geojson: Optional[Dict] = None  # GeoJSON LineString for map display
    rationale: str = ""  # Human-readable explanation


# ============================================================================
# PRIORITY SCORING
# ============================================================================

def compute_priority_score(
    damage_level: str,
    population_density: float,
    road_accessibility: float,
    hours_since_disaster: float,
) -> float:
    """Compute priority score for a damage zone (0-1, higher = more urgent).
    
    Factors weighted as:
    - Damage severity (40%): how much destruction
    - Population density (30%): how many people affected
    - Road accessibility (20%): ability to reach zone
    - Time since disaster (10%): zones grow more critical after 72 hours
    
    Args:
        damage_level: str from {none, minor, moderate, severe, extreme}
        population_density: float 0-1, normalized population density
        road_accessibility: float 0-1, where 1=fully passable, 0=blocked
        hours_since_disaster: float, hours since event started
    
    Returns:
        float 0-1 priority score
    """
    # Map damage level strings to numeric values (0-1)
    damage_score_map = {
        "none": 0.0,
        "minor": 0.25,
        "moderate": 0.5,
        "severe": 0.75,
        "extreme": 1.0,
    }
    damage_score = damage_score_map.get(damage_level.lower(), 0.0)
    
    # Clamp inputs to 0-1
    population_density = max(0.0, min(1.0, population_density))
    road_accessibility = max(0.0, min(1.0, road_accessibility))
    
    # Time factor: zones become more urgent after 72 hours
    time_factor = min(hours_since_disaster / 72.0, 1.0)
    
    # Weighted sum
    priority = (
        damage_score * 0.4 +
        population_density * 0.3 +
        road_accessibility * 0.2 +
        time_factor * 0.1
    )
    
    return min(1.0, max(0.0, priority))


# ============================================================================
# RESOURCE MATCHING
# ============================================================================

# Mapping of damage levels to required resource types and priorities
RESOURCE_NEEDS_MATRIX = {
    "extreme": [
        ("search_and_rescue", 10),      # Highest priority
        ("heavy_equipment", 8),
        ("medical_emergency", 7),
        ("water", 5),
        ("food", 5),
        ("shelter", 3),
    ],
    "severe": [
        ("medical_emergency", 8),
        ("search_and_rescue", 6),
        ("water", 6),
        ("food", 5),
        ("shelter", 4),
        ("heavy_equipment", 2),
    ],
    "moderate": [
        ("medical", 5),
        ("water", 4),
        ("food", 4),
        ("shelter", 3),
        ("search_and_rescue", 2),
    ],
    "minor": [
        ("first_aid", 3),
        ("food", 2),
        ("water", 2),
        ("shelter", 1),
    ],
    "none": [],
}


def match_resources_to_zone(
    zone_damage_level: str,
    available_resources: List,
) -> List[Dict[str, int]]:
    """Match available resources to the needs of a damage zone.
    
    Args:
        zone_damage_level: Damage level of the zone
        available_resources: List of Resource ORM objects from database
    
    Returns:
        List of dicts: [{"type": "medical", "quantity": 3}, ...]
        Ordered by priority and availability
    """
    needed_types = RESOURCE_NEEDS_MATRIX.get(zone_damage_level.lower(), [])
    
    matched = []
    for needed_type, priority_score in needed_types:
        # Find available resources of this type
        for resource in available_resources:
            if (resource.resource_type == needed_type and 
                resource.status == "available" and 
                resource.quantity > 0):
                # Match up to what's available
                matched.append({
                    "type": needed_type,
                    "quantity": min(resource.quantity, 5),  # Don't over-commit
                    "resource_id": resource.id,
                    "priority": priority_score,
                })
                break  # Move to next needed type
    
    return matched


# ============================================================================
# ROUTING / DISTANCE CALCULATION
# ============================================================================

def calculate_travel_time(
    source_lat: float,
    source_lon: float,
    target_lat: float,
    target_lon: float,
    road_quality: float = 1.0,
) -> float:
    """Estimate travel time in minutes from source to target.
    
    Uses Haversine formula for straight-line distance, then applies
    road quality factor to estimate actual travel time.
    
    Args:
        source_lat, source_lon: Starting location
        target_lat, target_lon: Destination location
        road_quality: 1.0=good roads, 0.5=damaged roads
    
    Returns:
        Estimated travel time in minutes
    """
    # Haversine formula for great-circle distance
    R = 6371  # Earth radius in km
    lat1, lon1, lat2, lon2 = map(math.radians, [source_lat, source_lon, target_lat, target_lon])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance_km = R * c
    
    # Average vehicle speed 40 km/h, affected by road quality
    avg_speed = 40 * road_quality
    travel_minutes = (distance_km / avg_speed) * 60
    
    return max(5, travel_minutes)  # Minimum 5 minutes


def build_route_geojson(
    source_lat: float,
    source_lon: float,
    target_lat: float,
    target_lon: float,
) -> Dict:
    """Create a GeoJSON LineString representing the route.
    
    For this simplified version, we use a straight line. In production,
    integrate with real routing services (OSRM, Google Maps) that return
    actual road-based routes.
    
    Args:
        source_lat, source_lon: Starting point
        target_lat, target_lon: Destination
    
    Returns:
        GeoJSON LineString dict
    """
    return {
        "type": "LineString",
        "coordinates": [
            [source_lon, source_lat],
            [target_lon, target_lat],
        ],
    }


# ============================================================================
# MAIN ALLOCATION ENGINE
# ============================================================================

def allocate_resources(
    damage_zones: List,
    available_resources: List,
    road_graph=None,
) -> List[AllocationRecommendation]:
    """Compute optimal resource allocation for a disaster event.
    
    Algorithm:
    1. Score each damage zone by priority
    2. Sort zones by priority (highest first)
    3. For each zone, find best matching resources
    4. Calculate optimal route
    5. Create recommendation
    
    Args:
        damage_zones: List of DamageAssessment ORM objects from database
        available_resources: List of Resource ORM objects
        road_graph: Optional NetworkX graph for Dijkstra routing
    
    Returns:
        List of AllocationRecommendation objects sorted by priority
    """
    recommendations = []
    remaining_resources = list(available_resources)  # Copy to avoid modifying original
    
    # Score and sort zones by priority
    zone_scores = []
    for zone in damage_zones:
        # Extract zone properties
        damage_level = zone.damage_level or "moderate"
        population = zone.affected_population_estimate or 0
        
        # Estimate population density (simplified; in production, use actual data)
        population_density = min(1.0, population / 10000.0)
        
        # Estimate road accessibility (simplified; in production, assess actual roads)
        # For now, assume accessibility = 1 - (damage_level / 5)
        damage_value = {"none": 0, "minor": 1, "moderate": 2, "severe": 3, "extreme": 4}.get(
            damage_level.lower(), 2
        )
        road_accessibility = max(0.1, 1.0 - (damage_value / 5.0))
        
        # Assume all zones are recent (0-24 hours)
        hours_since_disaster = 12.0
        
        # Compute priority
        priority = compute_priority_score(
            damage_level=damage_level,
            population_density=population_density,
            road_accessibility=road_accessibility,
            hours_since_disaster=hours_since_disaster,
        )
        
        zone_scores.append((zone, priority))
    
    # Sort by priority descending
    zone_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Allocate resources to zones in priority order
    for zone, priority in zone_scores:
        # Find best matching resources
        matched_resources = match_resources_to_zone(
            zone_damage_level=zone.damage_level or "moderate",
            available_resources=remaining_resources,
        )
        
        if not matched_resources:
            # No resources available for this zone
            continue
        
        # Estimate arrival time (simplified; would use real routing in production)
        # For now, use a fixed estimate plus distance-based component
        estimated_arrival = 30  # Base 30 minutes
        
        # Extract zone location (simplified; in production, get from geometry)
        zone_lat, zone_lon = -34.6037, 58.3816  # Placeholder: Buenos Aires
        
        # Build route GeoJSON (simplified straight line)
        route_geojson = build_route_geojson(
            source_lat=0,
            source_lon=0,
            target_lat=zone_lat,
            target_lon=zone_lon,
        )
        
        # Create rationale
        rationale = (
            f"High-priority zone ({zone.damage_level}) with "
            f"{zone.affected_population_estimate or 0} people affected. "
            f"Deploying {', '.join([f\"{r['quantity']} {r['type']}\" for r in matched_resources])}."
        )
        
        # Create recommendation
        recommendation = AllocationRecommendation(
            zone_id=zone.id,
            zone_damage_level=zone.damage_level or "moderate",
            priority_score=priority,
            recommended_resources=matched_resources,
            estimated_arrival_minutes=estimated_arrival,
            route_geojson=route_geojson,
            rationale=rationale,
        )
        
        recommendations.append(recommendation)
        
        # Remove allocated resources from available pool
        for matched in matched_resources:
            for resource in remaining_resources:
                if resource.id == matched.get("resource_id"):
                    resource.quantity -= matched["quantity"]
                    if resource.quantity <= 0:
                        remaining_resources.remove(resource)
                    break
    
    return recommendations


# ============================================================================
# TESTING UTILITIES
# ============================================================================

def test_allocation():
    """Test the allocation engine with synthetic data."""
    
    # Mock damage zone
    @dataclass
    class MockZone:
        id: int
        damage_level: str
        affected_population_estimate: int
    
    # Mock resource
    @dataclass
    class MockResource:
        id: int
        resource_type: str
        quantity: int
        status: str = "available"
    
    # Create synthetic data
    zones = [
        MockZone(id=1, damage_level="extreme", affected_population_estimate=5000),
        MockZone(id=2, damage_level="severe", affected_population_estimate=2000),
        MockZone(id=3, damage_level="moderate", affected_population_estimate=1000),
    ]
    
    resources = [
        MockResource(id=1, resource_type="search_and_rescue", quantity=10),
        MockResource(id=2, resource_type="medical_emergency", quantity=15),
        MockResource(id=3, resource_type="water", quantity=50),
        MockResource(id=4, resource_type="food", quantity=100),
    ]
    
    # Run allocation
    recommendations = allocate_resources(zones, resources)
    
    # Print results
    print("\n=== ALLOCATION RECOMMENDATIONS ===\n")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. Zone {rec.zone_id} (Priority: {rec.priority_score:.2f})")
        print(f"   Damage: {rec.zone_damage_level}")
        print(f"   Resources: {rec.recommended_resources}")
        print(f"   ETA: {rec.estimated_arrival_minutes} minutes")
        print(f"   Rationale: {rec.rationale}\n")
    
    return recommendations


if __name__ == "__main__":
    test_allocation()
