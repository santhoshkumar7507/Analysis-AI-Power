"""Ticket, TicketMessage, and TicketAttachment models."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base


class TicketStatus:
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"

    ALL = [OPEN, IN_PROGRESS, WAITING_CUSTOMER, RESOLVED, CLOSED]


class TicketPriority:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    ALL = [LOW, MEDIUM, HIGH, CRITICAL]


class TicketCategory:
    BILLING = "billing"
    REFUNDS = "refunds"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    ORDERS = "orders"
    GENERAL = "general"

    ALL = [BILLING, REFUNDS, TECHNICAL, ACCOUNT, ORDERS, GENERAL]


class TicketChannel:
    WEB = "web"
    EMAIL = "email"
    API = "api"

    ALL = [WEB, EMAIL, API]


class MessageSenderType:
    CUSTOMER = "customer"
    AGENT = "agent"
    AI_COPILOT = "ai_copilot"
    SYSTEM = "system"

    ALL = [CUSTOMER, AGENT, AI_COPILOT, SYSTEM]


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    reference_number = Column(String(50), nullable=False, unique=True, index=True)

    # Customer Information
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255), nullable=False, index=True)
    subject = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)

    # Classification & Attributes
    category = Column(String(50), default=TicketCategory.GENERAL, nullable=False, index=True)
    priority = Column(String(50), default=TicketPriority.MEDIUM, nullable=False, index=True)
    status = Column(String(50), default=TicketStatus.OPEN, nullable=False, index=True)
    channel = Column(String(50), default=TicketChannel.WEB, nullable=False)

    # Assignments
    assigned_team_id = Column(String(36), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_agent_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # SLA Tracking Timestamps
    first_response_deadline = Column(DateTime, nullable=True)
    resolution_deadline = Column(DateTime, nullable=True)
    first_responded_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    organization = relationship("Organization", back_populates="tickets")
    assigned_team = relationship("Team", back_populates="tickets")
    assigned_agent = relationship("User", back_populates="assigned_tickets", foreign_keys=[assigned_agent_id])
    messages = relationship("TicketMessage", back_populates="ticket", cascade="all, delete-orphan", order_by="TicketMessage.created_at")
    attachments = relationship("TicketAttachment", back_populates="ticket", cascade="all, delete-orphan")


class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id = Column(String(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_type = Column(String(50), default=MessageSenderType.AGENT, nullable=False)
    sender_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    body = Column(Text, nullable=False)
    is_internal_note = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    ticket = relationship("Ticket", back_populates="messages")
    sender_user = relationship("User", back_populates="messages")


class TicketAttachment(Base):
    __tablename__ = "ticket_attachments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id = Column(String(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    content_type = Column(String(100), nullable=False)
    file_path = Column(String(500), nullable=False)
    checksum = Column(String(64), nullable=True)
    uploaded_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    ticket = relationship("Ticket", back_populates="attachments")
