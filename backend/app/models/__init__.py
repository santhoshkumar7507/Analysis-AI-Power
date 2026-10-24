"""SQLAlchemy Models registry."""

from app.models.organization import Organization
from app.models.user import User, UserRole
from app.models.team import Team
from app.models.ticket import (
    Ticket,
    TicketMessage,
    TicketAttachment,
    TicketStatus,
    TicketPriority,
    TicketCategory,
    TicketChannel,
    MessageSenderType,
)
from app.models.knowledge import KnowledgeDocument, DocumentChunk, DocumentStatus
from app.models.ai import AIAnalysisRun, AIReplyDraft, AIEvaluationRun
from app.models.sla import SLAPolicy, SLAEvent, Notification
from app.models.audit import AuditLog

__all__ = [
    "Organization",
    "User",
    "UserRole",
    "Team",
    "Ticket",
    "TicketMessage",
    "TicketAttachment",
    "TicketStatus",
    "TicketPriority",
    "TicketCategory",
    "TicketChannel",
    "MessageSenderType",
    "KnowledgeDocument",
    "DocumentChunk",
    "DocumentStatus",
    "AIAnalysisRun",
    "AIReplyDraft",
    "AIEvaluationRun",
    "SLAPolicy",
    "SLAEvent",
    "Notification",
    "AuditLog",
]



