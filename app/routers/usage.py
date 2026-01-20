"""API Usage tracking router."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from datetime import datetime, timedelta
from app.db import get_session
from app.models import APIUsage, APIUsageStats

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/stats", response_model=APIUsageStats)
def get_usage_stats(session: Session = Depends(get_session)):
    """
    Get API usage statistics.
    
    Returns statistics about API requests including:
    - Total requests
    - Total tokens used
    - Requests today
    - Requests this month
    - Failed requests
    """
    
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    month_start = datetime(now.year, now.month, 1)
    
    # Total requests and tokens
    total_query = select(
        func.count(APIUsage.id).label("total_requests"),
        func.sum(APIUsage.tokens_used).label("total_tokens")
    )
    total_result = session.exec(total_query).first()
    total_requests = total_result.total_requests or 0
    total_tokens = total_result.total_tokens or 0
    
    # Requests today
    today_query = select(
        func.count(APIUsage.id).label("requests_today"),
        func.sum(APIUsage.tokens_used).label("tokens_today")
    ).where(APIUsage.created_at >= today_start)
    today_result = session.exec(today_query).first()
    requests_today = today_result.requests_today or 0
    tokens_today = today_result.tokens_today or 0
    
    # Requests this month
    month_query = select(
        func.count(APIUsage.id).label("requests_this_month"),
        func.sum(APIUsage.tokens_used).label("tokens_this_month")
    ).where(APIUsage.created_at >= month_start)
    month_result = session.exec(month_query).first()
    requests_this_month = month_result.requests_this_month or 0
    tokens_this_month = month_result.tokens_this_month or 0
    
    # Failed requests
    failed_query = select(func.count(APIUsage.id)).where(
        APIUsage.request_successful is False
    )
    failed_requests = session.exec(failed_query).first() or 0
    
    # Last request timestamp
    last_request_query = select(APIUsage).order_by(APIUsage.created_at.desc()).limit(1)
    last_request = session.exec(last_request_query).first()
    last_request_at = last_request.created_at if last_request else None
    
    return APIUsageStats(
        total_requests=total_requests,
        total_tokens=total_tokens,
        requests_today=requests_today,
        tokens_today=tokens_today,
        requests_this_month=requests_this_month,
        tokens_this_month=tokens_this_month,
        failed_requests=failed_requests,
        last_request_at=last_request_at
    )


@router.get("/requests", response_model=list)
def get_recent_requests(
    limit: int = 50,
    session: Session = Depends(get_session)
):
    """
    Get recent API requests.
    
    Args:
        limit: Maximum number of requests to return (default: 50, max: 200)
    """
    if limit > 200:
        limit = 200
    
    query = select(APIUsage).order_by(APIUsage.created_at.desc()).limit(limit)
    requests = session.exec(query).all()
    
    return [
        {
            "id": req.id,
            "provider": req.provider,
            "model": req.model,
            "endpoint": req.endpoint,
            "tokens_used": req.tokens_used,
            "request_successful": req.request_successful,
            "error_message": req.error_message,
            "created_at": req.created_at
        }
        for req in requests
    ]


@router.delete("/clear", response_model=dict)
def clear_usage_history(
    keep_days: int = 0,
    session: Session = Depends(get_session)
):
    """
    Clear API usage history.
    
    Args:
        keep_days: Keep requests from the last N days (0 = clear all)
    """
    if keep_days > 0:
        cutoff_date = datetime.utcnow() - timedelta(days=keep_days)
        query = select(APIUsage).where(APIUsage.created_at < cutoff_date)
    else:
        query = select(APIUsage)
    
    requests_to_delete = session.exec(query).all()
    count = len(requests_to_delete)
    
    for req in requests_to_delete:
        session.delete(req)
    
    session.commit()
    
    return {
        "message": f"Deleted {count} API usage records",
        "deleted_count": count
    }
