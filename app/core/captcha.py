import httpx
from fastapi import HTTPException, status

from app.core.config import settings


TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile_token(token: str, remote_ip: str | None = None) -> bool:
    """Verify a single-use Turnstile token with Cloudflare."""
    if not settings.turnstile_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CAPTCHA verification is not configured",
        )

    payload = {
        "secret": settings.turnstile_secret_key,
        "response": token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(TURNSTILE_VERIFY_URL, data=payload)
            response.raise_for_status()
            result = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CAPTCHA verification is temporarily unavailable",
        ) from exc

    if result.get("success") is not True:
        return False

    # The client must create the widget with action="login".
    if result.get("action") != "login":
        return False

    expected_hostname = settings.turnstile_expected_hostname
    if expected_hostname and result.get("hostname") != expected_hostname:
        return False

    return True
