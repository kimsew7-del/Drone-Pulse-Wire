from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.schemas import NoteUpdateRequest
from app.services import news_service
from app.models import User

router = APIRouter(prefix="/api/articles", tags=["articles"])


@router.post("/{item_id}/publish")
async def publish_article(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mark an article as published - requires auth."""
    return await news_service.update_status(db, item_id, "published")


@router.post("/{item_id}/queue")
async def queue_article(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Move an article back to queue - requires auth."""
    return await news_service.update_status(db, item_id, "queued")


@router.post("/{item_id}/note")
async def update_note(
    item_id: str,
    body: NoteUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update editor note on an article - requires auth."""
    return await news_service.update_note(db, item_id, body.note)


@router.post("/{item_id}/translate")
async def translate_article(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Force-translate a single article - requires auth."""
    return await news_service.translate_item(db, item_id)
