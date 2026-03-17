from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.services import news_service
from app.models import User

router = APIRouter(prefix="/api", tags=["news"])


@router.get("/news")
async def get_news(db: AsyncSession = Depends(get_db)):
    """Get complete news payload - public endpoint."""
    return await news_service.get_payload(db)


@router.post("/refresh")
async def refresh_feed(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Refresh feed from all sources - requires auth."""
    return await news_service.refresh_feed(db)
