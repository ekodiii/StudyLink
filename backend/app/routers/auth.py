import random
import string

import httpx
import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_db
from ..core.security import (
    create_access_token,
    create_refresh_token,
    create_extension_token,
    decode_token,
    get_current_user as get_current_user_dep,
)
from ..models.user import User
from ..schemas.auth import (
    AppleAuthRequest,
    GoogleAuthRequest,
    AuthResponse,
    UserBrief,
    RefreshRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _random_discriminator() -> str:
    return f"{random.randint(0, 9999):04d}"


def _random_username() -> str:
    return "student" + "".join(random.choices(string.digits, k=4))


async def _get_or_create_user(
    db: AsyncSession, *, apple_id: str | None = None, google_id: str | None = None
) -> tuple[User, bool]:
    if apple_id:
        result = await db.execute(select(User).where(User.apple_id == apple_id))
    else:
        result = await db.execute(select(User).where(User.google_id == google_id))

    user = result.scalar_one_or_none()
    if user:
        return user, False

    username = _random_username()
    disc = _random_discriminator()
    # Ensure unique combo
    for _ in range(20):
        exists = await db.execute(
            select(func.count()).where(User.username == username, User.discriminator == disc)
        )
        if exists.scalar() == 0:
            break
        disc = _random_discriminator()

    user = User(username=username, discriminator=disc, apple_id=apple_id, google_id=google_id)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user, True


@router.post("/apple", response_model=AuthResponse)
async def auth_apple(req: AppleAuthRequest, db: AsyncSession = Depends(get_db)):
    try:
        # Decode Apple identity token (unverified for structure; production should verify with Apple's public keys)
        payload = pyjwt.decode(req.identity_token, options={"verify_signature": False})
        apple_sub = payload.get("sub")
        if not apple_sub:
            raise ValueError("Missing sub")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Apple identity token")

    user, is_new = await _get_or_create_user(db, apple_id=apple_sub)
    return AuthResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        user=UserBrief(
            id=str(user.id),
            username=user.username,
            discriminator=user.discriminator,
            is_new_user=is_new,
        ),
    )


@router.post("/google", response_model=AuthResponse)
async def auth_google(req: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    try:
        # Verify Google ID token
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={req.id_token}"
            )
            if resp.status_code != 200:
                raise ValueError("Invalid token")
            payload = resp.json()
            google_sub = payload.get("sub")
            if not google_sub:
                raise ValueError("Missing sub")
            # Verify audience matches our client
            if settings.google_client_id and payload.get("aud") != settings.google_client_id:
                raise ValueError("Audience mismatch")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Google ID token")

    user, is_new = await _get_or_create_user(db, google_id=google_sub)
    return AuthResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        user=UserBrief(
            id=str(user.id),
            username=user.username,
            discriminator=user.discriminator,
            is_new_user=is_new,
        ),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshRequest):
    payload = decode_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=400, detail="Invalid refresh token")
    return TokenResponse(access_token=create_access_token(payload["sub"]))


@router.post("/extension-token", response_model=TokenResponse)
async def get_extension_token(user: User = Depends(get_current_user_dep)):
    return TokenResponse(access_token=create_extension_token(str(user.id)))


@router.get("/config")
async def auth_config():
    return {"google_client_id": settings.google_client_id}


@router.post("/logout")
async def logout():
    # Client-side token deletion; stateless JWTs
    return {"ok": True}
