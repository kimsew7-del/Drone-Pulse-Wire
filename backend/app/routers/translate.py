from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.schemas import TranslateCompareRequest
from app.services import news_service
from app.models import User

router = APIRouter(prefix="/api/translate", tags=["translate"])


@router.post("/compare")
async def compare_translations(
    body: TranslateCompareRequest,
    user: User = Depends(get_current_user),
):
    """Compare translations across all available engines - requires auth."""
    return await news_service.do_compare_translations(body.text, body.mode)
