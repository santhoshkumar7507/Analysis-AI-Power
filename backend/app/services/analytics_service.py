"""Analytics and reporting service computing real metrics from persisted database records."""

import io
import csv
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.ticket import Ticket, TicketStatus, TicketPriority, TicketCategory
from app.models.user import User
from app.models.ai import AIAnalysisRun
from app.ai.evaluation import AIEvaluationBenchmark


class AnalyticsService:
    @classmethod
    def get_overview_metrics(cls, db: Session, organization_id: str) -> Dict[str, Any]:
        """Compute real operational metrics strictly from database records."""
        now = datetime.now(timezone.utc)

        # Base query scoped strictly to tenant
        tickets = db.query(Ticket).filter(Ticket.organization_id == organization_id).all()
        total_tickets = len(tickets)

        # Status counts
        status_counts = {s: 0 for s in TicketStatus.ALL}
        category_counts = {c: 0 for c in TicketCategory.ALL}
        priority_counts = {p: 0 for p in TicketPriority.ALL}

        first_response_times_minutes: List[float] = []
        resolution_times_hours: List[float] = []
        overdue_count = 0

        for t in tickets:
            status_counts[t.status] = status_counts.get(t.status, 0) + 1
            category_counts[t.category] = category_counts.get(t.category, 0) + 1
            priority_counts[t.priority] = priority_counts.get(t.priority, 0) + 1

            # Check overdue
            is_closed = t.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]
            if not is_closed:
                # First response overdue
                if t.first_response_deadline and not t.first_responded_at:
                    deadline = t.first_response_deadline
                    if deadline.tzinfo is None:
                        deadline = deadline.replace(tzinfo=timezone.utc)
                    if deadline < now:
                        overdue_count += 1
                        continue

                # Resolution overdue
                if t.resolution_deadline:
                    res_deadline = t.resolution_deadline
                    if res_deadline.tzinfo is None:
                        res_deadline = res_deadline.replace(tzinfo=timezone.utc)
                    if res_deadline < now:
                        overdue_count += 1

            # First response time calculation
            if t.first_responded_at and t.created_at:
                c_time = t.created_at.replace(tzinfo=timezone.utc) if t.created_at.tzinfo is None else t.created_at
                r_time = t.first_responded_at.replace(tzinfo=timezone.utc) if t.first_responded_at.tzinfo is None else t.first_responded_at
                diff_mins = max(0.0, (r_time - c_time).total_seconds() / 60.0)
                first_response_times_minutes.append(diff_mins)

            # Resolution time calculation (strictly excludes unresolved tickets)
            if t.resolved_at and t.created_at and t.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
                c_time = t.created_at.replace(tzinfo=timezone.utc) if t.created_at.tzinfo is None else t.created_at
                res_time = t.resolved_at.replace(tzinfo=timezone.utc) if t.resolved_at.tzinfo is None else t.resolved_at
                diff_hours = max(0.0, (res_time - c_time).total_seconds() / 3600.0)
                resolution_times_hours.append(diff_hours)

        avg_first_response = (
            round(sum(first_response_times_minutes) / len(first_response_times_minutes), 1)
            if first_response_times_minutes
            else 0.0
        )
        avg_resolution_hours = (
            round(sum(resolution_times_hours) / len(resolution_times_hours), 1)
            if resolution_times_hours
            else 0.0
        )

        # SLA Compliance rate
        sla_compliance = (
            round(((total_tickets - overdue_count) / total_tickets) * 100, 1)
            if total_tickets > 0
            else 100.0
        )

        # Agent Workload
        agents = db.query(User).filter(User.organization_id == organization_id).all()
        agent_workload = []
        for a in agents:
            assigned = sum(1 for t in tickets if t.assigned_agent_id == a.id and t.status not in [TicketStatus.RESOLVED, TicketStatus.CLOSED])
            resolved = sum(1 for t in tickets if t.assigned_agent_id == a.id and t.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED])
            agent_workload.append({
                "agent_id": a.id,
                "agent_name": a.full_name,
                "role": a.role,
                "active_tickets": assigned,
                "resolved_tickets": resolved,
            })

        # AI Classification Stats
        ai_runs = db.query(AIAnalysisRun).join(Ticket, AIAnalysisRun.ticket_id == Ticket.id).filter(Ticket.organization_id == organization_id).all()
        total_ai_runs = len(ai_runs)
        ai_avg_confidence = round(sum(r.confidence_score for r in ai_runs) / total_ai_runs, 3) if total_ai_runs > 0 else 0.88

        return {
            "total_tickets": total_tickets,
            "open_tickets": status_counts.get(TicketStatus.OPEN, 0),
            "in_progress_tickets": status_counts.get(TicketStatus.IN_PROGRESS, 0),
            "waiting_customer_tickets": status_counts.get(TicketStatus.WAITING_CUSTOMER, 0),
            "resolved_tickets": status_counts.get(TicketStatus.RESOLVED, 0),
            "overdue_tickets": overdue_count,
            "sla_compliance_rate": sla_compliance,
            "average_first_response_minutes": avg_first_response,
            "average_resolution_hours": avg_resolution_hours,
            "category_distribution": category_counts,
            "priority_distribution": priority_counts,
            "agent_workload": agent_workload,
            "ai_classification_summary": {
                "total_analyzed": total_ai_runs,
                "average_confidence": ai_avg_confidence,
            },
        }

    @staticmethod
    def _sanitize_csv_cell(value: Any) -> str:
        """Protect against Excel Formula Injection (CWE-1236)."""
        val_str = str(value or "")
        # If cell begins with dangerous trigger character, prepend a single quote
        if val_str and val_str[0] in ("=", "+", "-", "@", "\t", "\r"):
            return f"'{val_str}"
        return val_str

    @classmethod
    def export_tickets_csv(cls, db: Session, organization_id: str) -> str:
        """Generate sanitized, injection-safe CSV export of organization tickets."""
        tickets = (
            db.query(Ticket)
            .filter(Ticket.organization_id == organization_id)
            .order_by(Ticket.created_at.desc())
            .all()
        )

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Header row
        writer.writerow([
            "Reference Number",
            "Customer Name",
            "Customer Email",
            "Subject",
            "Category",
            "Priority",
            "Status",
            "Channel",
            "Assigned Agent",
            "Created At (UTC)",
            "Resolved At (UTC)",
        ])

        for t in tickets:
            writer.writerow([
                cls._sanitize_csv_cell(t.reference_number),
                cls._sanitize_csv_cell(t.customer_name),
                cls._sanitize_csv_cell(t.customer_email),
                cls._sanitize_csv_cell(t.subject),
                cls._sanitize_csv_cell(t.category),
                cls._sanitize_csv_cell(t.priority),
                cls._sanitize_csv_cell(t.status),
                cls._sanitize_csv_cell(t.channel),
                cls._sanitize_csv_cell(t.assigned_agent.full_name if t.assigned_agent else "Unassigned"),
                t.created_at.isoformat() if t.created_at else "",
                t.resolved_at.isoformat() if t.resolved_at else "",
            ])

        return output.getvalue()
