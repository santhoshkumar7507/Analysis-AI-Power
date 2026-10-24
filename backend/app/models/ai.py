"""AI Analysis Runs, Reply Drafts, and AI Evaluation Benchmark models."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class AIAnalysisRun(Base):
    __tablename__ = "ai_analysis_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id = Column(String(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(50), nullable=False)
    priority = Column(String(50), nullable=False)
    sentiment = Column(String(50), nullable=False)  # positive, neutral, negative, urgent
    issue_summary = Column(Text, nullable=False)
    detected_language = Column(String(20), default="en", nullable=False)
    suggested_team_name = Column(String(100), nullable=True)
    recommended_action = Column(String(255), nullable=False)
    confidence_score = Column(Float, nullable=False)
    model_provider = Column(String(50), default="mock", nullable=False)
    latency_ms = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="success", nullable=False)  # success, fallback, failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class AIReplyDraft(Base):
    __tablename__ = "ai_reply_drafts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id = Column(String(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    suggested_reply = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=False)
    citations_json = Column(Text, nullable=False)  # list of {chunk_id, doc_title, citation}
    status = Column(String(50), default="draft", nullable=False)  # draft, approved, edited_and_approved, rejected
    reviewer_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_comment = Column(Text, nullable=True)
    final_sent_body = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class AIEvaluationRun(Base):
    __tablename__ = "ai_evaluation_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    benchmark_name = Column(String(100), nullable=False)
    total_samples = Column(Integer, nullable=False)
    accuracy_score = Column(Float, nullable=False)
    precision_score = Column(Float, nullable=False)
    recall_score = Column(Float, nullable=False)
    f1_score = Column(Float, nullable=False)
    avg_latency_ms = Column(Float, nullable=False)
    grounding_faithfulness = Column(Float, nullable=False)
    details_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
