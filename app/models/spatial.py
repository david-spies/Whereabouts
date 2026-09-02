# app/models/spatial.py
from sqlalchemy import Column, Numeric, Float, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from geoalchemy2 import Geometry
import uuid

# IMPORT YOUR TRUE CENTRAL BASE LAYER
from app.db.base import Base

class GeospatialScan(Base):
    __tablename__ = "geospatial_scans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tracking_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    
    metadata_location = Column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    inferred_location = Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    
    accuracy_radius_meters = Column(Float, default=0.0)
    confidence_score = Column(Numeric(5, 4), nullable=False)
    visual_evidence_json = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
