"""
utils/models.py
───────────────
SQLAlchemy database models for the Risk Agent.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


class AnalysisResult(Base):
    """Model for storing document analysis results."""

    __tablename__ = "analysis_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Standardized data
    standardized_data = Column(JSON, nullable=False)

    # Validation result
    validation_result = Column(JSON, nullable=False)

    # Analysis results
    risk_score = Column(Float, nullable=False)
    recommendation = Column(String(50), nullable=False)  # approve/review/reject
    confidence = Column(Float, nullable=False)
    summary = Column(Text, nullable=True)

    # Risk breakdown
    risk_breakdown = Column(JSON, nullable=False)

    # Processing metadata
    processing_time_ms = Column(Integer, nullable=True)
    llm_provider = Column(String(50), nullable=True)  # ollama/anthropic/fallback

    def __repr__(self):
        return f"<AnalysisResult(id={self.id}, document_id={self.document_id}, risk_score={self.risk_score:.3f})>"


class AuditLog(Base):
    """Model for storing audit logs of API requests."""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Request information
    method = Column(String(10), nullable=False)
    path = Column(String(500), nullable=False)
    query_params = Column(JSON, nullable=True)
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6

    # Authentication
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)
    user_id = Column(String(255), nullable=True)

    # Response information
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    # Request/Response data (truncated for audit)
    request_size_bytes = Column(Integer, nullable=True)
    response_size_bytes = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<AuditLog(id={self.id}, method={self.method}, path={self.path}, status={self.status_code})>"


class APIKey(Base):
    """Model for storing API keys."""

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_hash = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Permissions
    permissions = Column(JSON, default=list, nullable=False)  # List of permission strings

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)

    # Usage tracking
    request_count = Column(Integer, default=0, nullable=False)
    rate_limit_remaining = Column(Integer, nullable=True)

    # Relationships
    audit_logs = relationship("AuditLog", backref="api_key")

    def __repr__(self):
        return f"<APIKey(id={self.id}, name={self.name}, active={self.is_active})>"