from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.schemas import SourceCreate
from app.services import news_service
from app.models import User

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("")
async def get_sources(db: AsyncSession = Depends(get_db)):
    """Get all sources and source stats - public endpoint."""
    payload = await news_service.get_payload(db)
    return {
        "sources": payload.get("sources", []),
        "source_stats": payload.get("source_stats", {}),
    }


@router.post("")
async def create_source(
    body: SourceCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Add a new source - requires auth."""
    return await news_service.create_source(db, body.name, body.url, body.type)


@router.delete("/{source_id}")
async def delete_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a source by id - requires auth."""
    return await news_service.delete_source(db, source_id)
