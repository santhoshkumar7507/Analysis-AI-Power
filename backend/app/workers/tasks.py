"""Background asynchronous worker tasks for AI classification, RAG pre-drafting, and SLA evaluations."""

import logging
from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.ticket import Ticket, TicketCategory, TicketPriority
from app.models.ai import AIAnalysisRun, AIReplyDraft
from app.models.sla import SLAPolicy
from app.models.organization import Organization
from app.services.knowledge_service import KnowledgeService
from app.services.sla_service import SLAService
from app.ai.copilot import AICopilotEngine
import json

logger = logging.getLogger("resolveai.worker")


@celery_app.task(name="app.workers.tasks.async_classify_ticket")
def async_classify_ticket(ticket_id: str):
    """Background task to run AI ticket categorization, sentiment analysis, and priority routing."""
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            logger.warning(f"Ticket {ticket_id} not found for async classification.")
            return

        # Perform AI analysis
        analysis_data = AICopilotEngine.classify_ticket(
            subject=ticket.subject,
            description=ticket.description,
        )

        analysis = AIAnalysisRun(
            ticket_id=ticket.id,
            category=analysis_data["category"],
            priority=analysis_data["priority"],
            sentiment=analysis_data["sentiment"],
            confidence_score=analysis_data["confidence_score"],
            issue_summary=analysis_data["issue_summary"],
            suggested_team_name=analysis_data.get("suggested_team_name"),
            recommended_action=analysis_data.get("recommended_action", "Acknowledge inquiry"),
            model_provider=analysis_data.get("model_provider", "deterministic-fallback"),
            latency_ms=analysis_data.get("latency_ms", 10),
            status=analysis_data.get("status", "success"),
        )
        db.add(analysis)

        # Update ticket classification if default
        if ticket.category == TicketCategory.GENERAL and analysis_data["category"] in TicketCategory.ALL:
            ticket.category = analysis_data["category"]
        if ticket.priority == TicketPriority.MEDIUM and analysis_data["priority"] in TicketPriority.ALL:
            ticket.priority = analysis_data["priority"]

        db.commit()
        logger.info(f"Completed async classification for ticket {ticket_id}.")
        return {"status": "success", "ticket_id": ticket_id, "category": analysis_data["category"]}
    except Exception as e:
        db.rollback()
        logger.error(f"Error in async_classify_ticket for {ticket_id}: {e}", exc_info=True)
        raise
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.async_generate_copilot_draft")
def async_generate_copilot_draft(ticket_id: str):
    """Background task to retrieve grounded knowledge and pre-synthesize AI draft reply."""
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return

        # Retrieve relevant chunks from org knowledge base
        search_query = f"{ticket.subject} {ticket.description}"
        retrieved_chunks = KnowledgeService.semantic_search(
            db=db,
            organization_id=ticket.organization_id,
            query=search_query,
            top_k=3,
            threshold=0.35,
        )

        draft_data = AICopilotEngine.generate_reply_draft(
            subject=ticket.subject,
            description=ticket.description,
            retrieved_chunks=retrieved_chunks,
        )

        draft = AIReplyDraft(
            ticket_id=ticket.id,
            suggested_reply=draft_data["suggested_reply"],
            reasoning=draft_data["reasoning"],
            citations_json=json.dumps(draft_data.get("citations", [])),
            status="draft",
        )
        db.add(draft)
        db.commit()
        logger.info(f"Synthesized async copilot draft for ticket {ticket_id}.")
        return {"status": "success", "ticket_id": ticket_id}
    except Exception as e:
        db.rollback()
        logger.error(f"Error in async_generate_copilot_draft for {ticket_id}: {e}", exc_info=True)
        raise
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.check_all_sla_breaches")
def check_all_sla_breaches():
    """Periodic Celery Beat task scanning all organizations and evaluating SLA deadlines."""
    db = SessionLocal()
    try:
        orgs = db.query(Organization).all()
        total_evaluations = 0
        total_breaches = 0

        for org in orgs:
            result = SLAService.evaluate_sla_deadlines(db, org.id)
            total_evaluations += result["active_tickets_evaluated"]
            total_breaches += result["breaches_triggered"]

        logger.info(f"Periodic SLA evaluation completed: {total_evaluations} tickets evaluated, {total_breaches} breaches detected.")
        return {
            "status": "success",
            "evaluated_tickets": total_evaluations,
            "breaches": total_breaches,
        }
    except Exception as e:
        logger.error(f"Error running periodic SLA check: {e}", exc_info=True)
        raise
    finally:
        db.close()
