from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from app.core.captcha import verify_turnstile_token
from app.core.config import settings
from app.core.rate_limit import (
    clear_login_attempts,
    consume_login_attempt,
    record_failed_login,
)
from app.core.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    username: str
    password: str
    captcha_token: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/token", response_model=TokenResponse)
async def login(request: Request, credentials: LoginRequest):
    # Apply IP limits and determine whether this request needs a CAPTCHA.
    captcha_required = await consume_login_attempt(request, credentials.username)
    if captcha_required:
        if not credentials.captcha_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "captcha_required",
                    "message": "Complete the CAPTCHA challenge and retry login.",
                },
            )

        client_ip = request.client.host if request.client else None
        if not await verify_turnstile_token(credentials.captcha_token, client_ip):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "captcha_failed",
                    "message": "CAPTCHA verification failed. Please try again.",
                },
            )

    # Fail closed: no password is accepted until an admin hash is configured.
    if not settings.admin_password_hash:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Administrator login is not configured",
        )

    if credentials.username != settings.admin_username or not verify_password(
        credentials.password,
        settings.admin_password_hash,
    ):
        await record_failed_login(credentials.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    await clear_login_attempts(request, credentials.username)
    token = create_access_token(subject=str(settings.admin_user_id))
    return TokenResponse(access_token=token)
