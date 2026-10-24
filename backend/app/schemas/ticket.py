"""Ticket and Conversation Pydantic request/response schemas."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class TicketCreateRequest(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=255)
    customer_email: EmailStr
    subject: str = Field(..., min_length=3, max_length=500)
    description: str = Field(..., min_length=5)
    category: str = Field(default="general", pattern="^(billing|refunds|technical|account|orders|general)$")
    priority: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    channel: str = Field(default="web", pattern="^(web|email|api)$")


class TicketUpdateRequest(BaseModel):
    status: Optional[str] = Field(None, pattern="^(open|in_progress|waiting_customer|resolved|closed)$")
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|critical)$")
    category: Optional[str] = Field(None, pattern="^(billing|refunds|technical|account|orders|general)$")


class TicketAssignRequest(BaseModel):
    assigned_agent_id: Optional[str] = None
    assigned_team_id: Optional[str] = None


class TicketMessageCreateRequest(BaseModel):
    body: str = Field(..., min_length=1)
    is_internal_note: bool = False


class TicketMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_id: str
    sender_type: str
    sender_user_id: Optional[str] = None
    sender_name: Optional[str] = None
    body: str
    is_internal_note: bool
    created_at: datetime


class TicketAttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_id: str
    file_name: str
    file_size: int
    content_type: str
    created_at: datetime


class TicketListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reference_number: str
    customer_name: str
    customer_email: str
    subject: str
    category: str
    priority: str
    status: str
    channel: str
    assigned_agent_name: Optional[str] = None
    assigned_team_name: Optional[str] = None
    first_response_deadline: Optional[datetime] = None
    resolution_deadline: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class TicketDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reference_number: str
    customer_name: str
    customer_email: str
    subject: str
    description: str
    category: str
    priority: str
    status: str
    channel: str
    assigned_agent_id: Optional[str] = None
    assigned_agent_name: Optional[str] = None
    assigned_team_id: Optional[str] = None
    assigned_team_name: Optional[str] = None
    first_response_deadline: Optional[datetime] = None
    resolution_deadline: Optional[datetime] = None
    first_responded_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    messages: List[TicketMessageResponse] = []
    attachments: List[TicketAttachmentResponse] = []



class TicketListResponse(BaseModel):
    items: List[TicketListItemResponse]
    total: int
    page: int
    limit: int
    total_pages: int
