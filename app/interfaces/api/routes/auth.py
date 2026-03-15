from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])

# Hardcoded demo user for now
# In production this would query a user repository
DEMO_USERS = {
    "admin": {
        "user_id": "00000000-0000-0000-0000-000000000001",
        "hashed_password": "$2b$12$XAS/2OBrU.zkibarEhZ07egSZcPQrX6Uc6RfhC./Dss2flYIjI9yC",
    }
}

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/token", response_model=TokenResponse)
async def login(request: LoginRequest):
    user = DEMO_USERS.get(request.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = create_access_token(subject=user["user_id"])
    return TokenResponse(access_token=token)