"""Analytics, reporting, AI benchmarks, and safe CSV export API endpoints."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.analytics_service import AnalyticsService
from app.ai.evaluation import AIEvaluationBenchmark

router = APIRouter(prefix="/analytics", tags=["Analytics & Reporting"])


@router.get("/overview")
def get_analytics_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve aggregate performance and workload analytics computed from database records."""
    return AnalyticsService.get_overview_metrics(db=db, organization_id=current_user.organization_id)


@router.get("/ai-performance")
def get_ai_evaluation_performance():
    """Retrieve benchmark results measuring Precision, Recall, F1, and Latency against curated dataset."""
    return AIEvaluationBenchmark.run_benchmark()


@router.get("/export")
def export_tickets_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download sanitized CSV export of tickets (protected against CSV formula injection)."""
    csv_data = AnalyticsService.export_tickets_csv(db=db, organization_id=current_user.organization_id)
    filename = f"resolveai_tickets_export_{current_user.organization.slug}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
