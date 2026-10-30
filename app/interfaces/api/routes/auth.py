from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/token", response_model=TokenResponse)
async def login(request: LoginRequest):
    # Fail closed: no password is accepted until an admin hash is configured.
    if not settings.admin_password_hash:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Administrator login is not configured",
        )

    if request.username != settings.admin_username or not verify_password(
        request.password,
        settings.admin_password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = create_access_token(subject=str(settings.admin_user_id))
    return TokenResponse(access_token=token)
