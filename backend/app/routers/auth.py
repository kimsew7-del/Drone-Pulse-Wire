from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, get_password_hash, verify_password
from app.dependencies import get_db
from app.models import User
from app.schemas import TokenResponse, UserCreate, UserLogin

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    body: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return a JWT token."""
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    return TokenResponse(access_token=access_token)


@router.post("/register", response_model=TokenResponse)
async def register(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user and return a JWT token."""
    result = await db.execute(select(User).where(User.username == body.username))
    existing = result.scalar_one_or_none()

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    user = User(
        username=body.username,
        hashed_password=get_password_hash(body.password),
    )
    db.add(user)
    await db.flush()

    access_token = create_access_token(data={"sub": user.username})
    return TokenResponse(access_token=access_token)
