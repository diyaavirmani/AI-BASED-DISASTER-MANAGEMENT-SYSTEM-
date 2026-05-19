# src/database/models.py — SIMPLIFIED VERSION

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database.connection import Base


class DisasterEvent(Base):
    __tablename__ = "disaster_events"

    id          = Column(Integer, primary_key=True, index=True)
    event_type  = Column(String, nullable=False)   # earthquake, flood, fire
    name        = Column(String, nullable=False)
    status      = Column(String, default="active") # active, resolved, pending
    magnitude   = Column(Float, nullable=True)
    start_time  = Column(DateTime, default=datetime.utcnow)
    end_time    = Column(DateTime, nullable=True)
    source      = Column(String, nullable=True)    # gdacs, manual
    
    # Bounding box as simple floats instead of PostGIS polygon
    bbox_min_lat = Column(Float, nullable=True)
    bbox_min_lon = Column(Float, nullable=True)
    bbox_max_lat = Column(Float, nullable=True)
    bbox_max_lon = Column(Float, nullable=True)

    gdacs_alert_score = Column(Float, nullable=True)
    affected_area_km2 = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    damage_assessments = relationship("DamageAssessment", back_populates="event", cascade="all, delete-orphan")
    resources          = relationship("ResourceDeployment", back_populates="event", cascade="all, delete-orphan")
    reports            = relationship("CrowdsourceReport", back_populates="event", cascade="all, delete-orphan")
    satellite_images   = relationship("SatelliteImage", back_populates="event", cascade="all, delete-orphan")


class DamageAssessment(Base):
    __tablename__ = "damage_assessments"

    id           = Column(Integer, primary_key=True, index=True)
    event_id     = Column(Integer, ForeignKey("disaster_events.id"), nullable=False)
    assessed_at  = Column(DateTime, default=datetime.utcnow)
    
    # support both confidence and confidence_score for full API compatibility
    confidence       = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)

    damage_level = Column(Integer, nullable=False)  # 0=no_damage, 1=minor, 2=major, 3=destroyed

    # Store damage zones as GeoJSON string instead of PostGIS geometry
    damage_zones_geojson = Column(Text, nullable=True)

    # Summary stats
    total_pixels_assessed = Column(Integer, nullable=True)
    pct_no_damage         = Column(Float, nullable=True)
    pct_minor             = Column(Float, nullable=True)
    pct_major             = Column(Float, nullable=True)
    pct_destroyed         = Column(Float, nullable=True)
    affected_population_estimate = Column(Integer, nullable=True)

    # Property to dynamically convert geometry if any client expects it
    @property
    def damage_zone(self):
        return None

    event = relationship("DisasterEvent", back_populates="damage_assessments")


class Resource(Base):
    __tablename__ = "resources"

    id            = Column(Integer, primary_key=True, index=True)
    resource_type = Column(String, nullable=False)  # medical, food, rescue
    quantity      = Column(Integer, default=1)
    status        = Column(String, default="available")  # available, deployed, exhausted
    latitude      = Column(Float, nullable=True)
    longitude     = Column(Float, nullable=True)
    last_updated  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    deployments = relationship("ResourceDeployment", back_populates="resource", cascade="all, delete-orphan")


class ResourceDeployment(Base):
    __tablename__ = "resource_deployments"

    id                 = Column(Integer, primary_key=True, index=True)
    resource_id        = Column(Integer, ForeignKey("resources.id"), nullable=False)
    event_id           = Column(Integer, ForeignKey("disaster_events.id"), nullable=False)
    
    # Support both zone_id and target_zone_id for routing/deployments compatibility
    zone_id            = Column(Integer, ForeignKey("damage_assessments.id"), nullable=True)
    target_zone_id     = Column(Integer, ForeignKey("damage_assessments.id"), nullable=True)

    deployed_at        = Column(DateTime, default=datetime.utcnow)
    completed_at       = Column(DateTime, nullable=True)
    quantity_deployed  = Column(Integer)
    status             = Column(String, default="en_route")  # en_route, arrived, completed
    estimated_arrival  = Column(DateTime, nullable=True)
    route_geojson      = Column(Text, nullable=True)

    resource = relationship("Resource", back_populates="deployments")
    event    = relationship("DisasterEvent", back_populates="resources")


class CrowdsourceReport(Base):
    __tablename__ = "crowdsource_reports"

    id             = Column(Integer, primary_key=True, index=True)
    event_id       = Column(Integer, ForeignKey("disaster_events.id"), nullable=False)
    source         = Column(String)       # twitter, reddit, gdacs
    text           = Column(Text)
    reported_at    = Column(DateTime, default=datetime.utcnow)
    
    disaster_type  = Column(String, nullable=True)
    severity_score = Column(Float, nullable=True)
    severity_source = Column(String, nullable=True)
    severity_label = Column(String, nullable=True)
    severity_resolved = Column(Boolean, default=False)
    
    verified       = Column(Boolean, default=False)
    latitude       = Column(Float, nullable=True)
    longitude      = Column(Float, nullable=True)
    image_analysis = Column(JSON, nullable=True)

    event = relationship("DisasterEvent", back_populates="reports")


class SatelliteImage(Base):
    __tablename__ = "satellite_images"

    id                  = Column(Integer, primary_key=True, index=True)
    event_id            = Column(Integer, ForeignKey("disaster_events.id"), nullable=False)
    image_type          = Column(String, nullable=True)
    captured_at         = Column(DateTime, nullable=True)
    processed_at        = Column(DateTime, nullable=True)
    file_path           = Column(String, nullable=True)
    
    bbox_min_lat        = Column(Float, nullable=True)
    bbox_min_lon        = Column(Float, nullable=True)
    bbox_max_lat        = Column(Float, nullable=True)
    bbox_max_lon        = Column(Float, nullable=True)
    
    cloud_cover_percent = Column(Float, nullable=True)

    event = relationship("DisasterEvent", back_populates="satellite_images")