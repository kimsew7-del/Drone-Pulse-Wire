from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.database import AsyncSessionLocal
from app.services.crawl_manager import CrawlManager
from app.models import User

router = APIRouter(prefix="/api/reports", tags=["reports"])

# Reuse the same CrawlManager singleton from crawl router for clear_reports
from app.routers.crawl import _crawl_manager


@router.delete("")
async def clear_reports(
    user: User = Depends(get_current_user),
):
    """Clear all report items - requires auth."""
    return await _crawl_manager.clear_reports()
