from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Boolean, JSON
)
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from datetime import datetime

from src.database.connection import Base


# --------------------------------------------------
# 147. DISASTER EVENT
# --------------------------------------------------
class DisasterEvent(Base):
    __tablename__ = "disaster_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)
    name = Column(String, nullable=False)

    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)

    magnitude = Column(Float)
    affected_area_km2 = Column(Float)

    status = Column(String)
    source = Column(String)
    gdacs_alert_score = Column(Float)

    # Relationships
    damage_assessments = relationship("DamageAssessment", back_populates="event")
    resources = relationship("ResourceDeployment", back_populates="event")
    reports = relationship("CrowdsourceReport", back_populates="event")
    satellite_images = relationship("SatelliteImage", back_populates="event")


# --------------------------------------------------
# 148. DAMAGE ASSESSMENT
# --------------------------------------------------
class DamageAssessment(Base):
    __tablename__ = "damage_assessments"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("disaster_events.id"), nullable=False)

    assessed_at = Column(DateTime, default=datetime.utcnow)
    confidence_score = Column(Float)

    damage_zone = Column(Geometry("POLYGON"))  # PostGIS
    damage_level = Column(Integer)  # 0–3

    affected_population_estimate = Column(Integer)

    # Relationships
    event = relationship("DisasterEvent", back_populates="damage_assessments")


# --------------------------------------------------
# 149. RESOURCE
# --------------------------------------------------
class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    resource_type = Column(String, nullable=False)
    quantity = Column(Integer)

    location = Column(Geometry("POINT"))  # PostGIS
    status = Column(String)

    last_updated = Column(DateTime, default=datetime.utcnow)

    # Relationships
    deployments = relationship("ResourceDeployment", back_populates="resource")


# --------------------------------------------------
# 150. RESOURCE DEPLOYMENT
# --------------------------------------------------
class ResourceDeployment(Base):
    __tablename__ = "resource_deployments"

    id = Column(Integer, primary_key=True, index=True)

    resource_id = Column(Integer, ForeignKey("resources.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("disaster_events.id"), nullable=False)
    target_zone_id = Column(Integer, ForeignKey("damage_assessments.id"))

    deployed_at = Column(DateTime, default=datetime.utcnow)
    quantity_deployed = Column(Integer)

    estimated_arrival = Column(DateTime)
    route = Column(Geometry("LINESTRING"))  # PostGIS

    # Relationships
    resource = relationship("Resource", back_populates="deployments")
    event = relationship("DisasterEvent", back_populates="resources")


# --------------------------------------------------
# 151. CROWDSOURCE REPORT
# --------------------------------------------------
class CrowdsourceReport(Base):
    __tablename__ = "crowdsource_reports"

    id = Column(Integer, primary_key=True, index=True)

    event_id = Column(Integer, ForeignKey("disaster_events.id"), nullable=False)

    source = Column(String)
    text = Column(String)

    location = Column(Geometry("POINT"))  # PostGIS
    reported_at = Column(DateTime, default=datetime.utcnow)

    disaster_type = Column(String)

    severity_score = Column(Float)
    severity_source = Column(String)
    severity_label = Column(String)
    severity_resolved = Column(Boolean, default=False)

    image_analysis = Column(JSON)

    location_source = Column(String)
    verified = Column(Boolean, default=False)

    # Relationships
    event = relationship("DisasterEvent", back_populates="reports")


# --------------------------------------------------
# 152. SATELLITE IMAGE
# --------------------------------------------------
class SatelliteImage(Base):
    __tablename__ = "satellite_images"

    id = Column(Integer, primary_key=True, index=True)

    event_id = Column(Integer, ForeignKey("disaster_events.id"), nullable=False)

    image_type = Column(String)

    captured_at = Column(DateTime)
    processed_at = Column(DateTime)

    file_path = Column(String)

    bounding_box = Column(Geometry("POLYGON"))  # PostGIS
    cloud_cover_percent = Column(Float)

    # Relationships
    event = relationship("DisasterEvent", back_populates="satellite_images")