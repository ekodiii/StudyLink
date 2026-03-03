import random
import string
import urllib.parse

import httpx
import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..core.config import settings
from ..core.database import get_db
from ..core.security import (
    create_access_token,
    create_refresh_token,
    create_extension_token,
    decode_token,
    get_current_user as get_current_user_dep,
)
from ..core.apple_auth import verify_apple_token
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
limiter = Limiter(key_func=get_remote_address)


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
@limiter.limit("10/minute")
async def auth_apple(req: AppleAuthRequest, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        # Verify Apple identity token with signature verification
        payload = await verify_apple_token(req.identity_token, settings.apple_client_id)
        apple_sub = payload.get("sub")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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
@limiter.limit("10/minute")
async def auth_google(req: GoogleAuthRequest, request: Request, db: AsyncSession = Depends(get_db)):
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
            # Verify audience matches our web or iOS client
            ios_client_id = "374855005519-b4vrdccg2ts9i5po31r3inotu6ij8i7k.apps.googleusercontent.com"
            aud = payload.get("aud")
            if settings.google_client_id and aud not in [settings.google_client_id, ios_client_id]:
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
@limiter.limit("20/minute")
async def refresh_token(req: RefreshRequest, request: Request):
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


# ---------------------------------------------------------------------------
# Extension OAuth flows (server-side redirect for browser extensions)
# ---------------------------------------------------------------------------

@router.get("/google/extension-flow")
async def google_extension_flow():
    """Redirect the user to Google's OAuth consent screen."""
    params = urllib.parse.urlencode({
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_extension_redirect_uri,
        "response_type": "code",
        "scope": "openid email",
        "access_type": "offline",
        "prompt": "consent",
    })
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@router.get("/google/extension-callback")
async def google_extension_callback(
    code: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Google redirects here with an authorization code.
    Exchange it for tokens, look up / create the user, and render an HTML
    page that the extension's background script can detect.
    """
    # Exchange auth code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_extension_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            return HTMLResponse("<h1>Authentication failed</h1><p>Could not exchange code.</p>", status_code=400)
        tokens = token_resp.json()

    # Verify the ID token to get the user's Google sub
    id_token = tokens.get("id_token", "")
    try:
        async with httpx.AsyncClient() as client:
            info_resp = await client.get(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
            )
            if info_resp.status_code != 200:
                raise ValueError("Bad id_token")
            payload = info_resp.json()
            google_sub = payload.get("sub")
            if not google_sub:
                raise ValueError("Missing sub")
            if settings.google_client_id and payload.get("aud") != settings.google_client_id:
                raise ValueError("Audience mismatch")
    except ValueError:
        return HTMLResponse("<h1>Authentication failed</h1><p>Invalid Google token.</p>", status_code=400)

    user, _ = await _get_or_create_user(db, google_id=google_sub)
    ext_token = create_extension_token(str(user.id))

    # Render an HTML page with the token in the URL hash.
    # The extension's background script detects this URL and extracts the data.
    html = f"""<!DOCTYPE html>
<html>
<head><title>StudyLink — Signed In</title></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;background:#f9fafb">
<div style="text-align:center">
  <h1 style="color:#4f46e5">✓ Signed in to StudyLink</h1>
  <p>You can close this tab and return to the extension.</p>
</div>
<script>
  // Store auth data in the URL hash so the extension can read it
  window.location.hash = "studylink-auth:" + JSON.stringify({{
    authToken: "{ext_token}",
    username: "{user.username}",
    discriminator: "{user.discriminator}"
  }});
</script>
</body>
</html>"""
    return HTMLResponse(html)


@router.get("/apple/extension-flow")
async def apple_extension_flow():
    """Redirect the user to Apple's OAuth consent screen."""
    params = urllib.parse.urlencode({
        "client_id": settings.apple_client_id,
        "redirect_uri": f"{settings.api_base_url}/auth/apple/extension-callback",
        "response_type": "code id_token",
        "scope": "name email",
        "response_mode": "form_post",
    })
    return RedirectResponse(f"https://appleid.apple.com/auth/authorize?{params}")


@router.post("/apple/extension-callback")
async def apple_extension_callback(
    code: str = "",
    id_token: str = "",
    db: AsyncSession = Depends(get_db),
):
    """
    Apple redirects here via form_post with code and id_token.
    Decode the id_token to get the Apple sub, create/find user,
    and render the auth-handoff page.
    """
    if not id_token:
        return HTMLResponse("<h1>Authentication failed</h1><p>No identity token received.</p>", status_code=400)

    try:
        # Verify Apple identity token with signature verification
        payload = await verify_apple_token(id_token, settings.apple_client_id)
        apple_sub = payload.get("sub")
    except ValueError as e:
        return HTMLResponse(f"<h1>Authentication failed</h1><p>{str(e)}</p>", status_code=400)

    user, _ = await _get_or_create_user(db, apple_id=apple_sub)
    ext_token = create_extension_token(str(user.id))

    html = f"""<!DOCTYPE html>
<html>
<head><title>StudyLink — Signed In</title></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;background:#f9fafb">
<div style="text-align:center">
  <h1 style="color:#4f46e5">✓ Signed in to StudyLink</h1>
  <p>You can close this tab and return to the extension.</p>
</div>
<script>
  window.location.hash = "studylink-auth:" + JSON.stringify({{
    authToken: "{ext_token}",
    username: "{user.username}",
    discriminator: "{user.discriminator}"
  }});
</script>
</body>
</html>"""
    return HTMLResponse(html)
