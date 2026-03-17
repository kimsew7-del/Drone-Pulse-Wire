from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.database import AsyncSessionLocal
from app.schemas import CrawlStartRequest
from app.services.crawl_manager import CrawlManager
from app.models import User

router = APIRouter(prefix="/api/crawl", tags=["crawl"])

# Singleton CrawlManager instance shared across all requests
_crawl_manager = CrawlManager(AsyncSessionLocal)


@router.get("")
async def get_crawl_status():
    """Get current crawl job status - public endpoint."""
    return _crawl_manager.get_status()


@router.post("")
async def start_crawl(
    body: CrawlStartRequest,
    user: User = Depends(get_current_user),
):
    """Start a crawl job - requires auth.

    Supported modes:
    - None / "region": region-based source discovery crawl
    - "topic": topic-focused report/research crawl
    - "stats": statistics-focused crawl
    """
    if body.mode == "topic" and body.topic:
        return _crawl_manager.start_topic_crawl(body.topic)
    elif body.mode == "stats" and body.topic:
        return _crawl_manager.start_stats_crawl(body.topic)
    else:
        return _crawl_manager.start_crawl(body.regions)


@router.delete("")
async def reset_crawl(
    user: User = Depends(get_current_user),
):
    """Reset crawl job state - requires auth."""
    return _crawl_manager.reset()
