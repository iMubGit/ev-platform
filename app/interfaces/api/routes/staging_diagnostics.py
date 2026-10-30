import hmac
import ipaddress

from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.rate_limit import get_client_ip

router = APIRouter(prefix="/__staging__", tags=["Staging diagnostics"])


class ClientIPDiagnosticRequest(BaseModel):
    # Obtain this independently from the tester's network, not from request
    # headers. It is used only for a boolean comparison and is never returned.
    expected_public_ip: str


class ClientIPDiagnosticResponse(BaseModel):
    cloudflare_header_matches_expected: bool
    application_ip_matches_expected: bool


@router.post(
    "/diagnostics/client-ip",
    response_model=ClientIPDiagnosticResponse,
    include_in_schema=False,
)
async def diagnose_client_ip(
    payload: ClientIPDiagnosticRequest,
    request: Request,
    response: Response,
    diagnostic_token: str | None = Header(
        default=None,
        alias="X-Staging-Diagnostic-Token",
    ),
):
    # Hide the endpoint completely unless explicitly enabled for staging.
    if not settings.staging_diagnostics_enabled:
        raise HTTPException(status_code=404, detail="Not found")

    configured_token = settings.staging_diagnostics_token
    if not configured_token or len(configured_token) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Staging diagnostics are not configured",
        )

    if not diagnostic_token or not hmac.compare_digest(
        diagnostic_token, configured_token
    ):
        raise HTTPException(status_code=404, detail="Not found")

    try:
        expected_ip = str(ipaddress.ip_address(payload.expected_public_ip.strip()))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A valid expected public IP is required",
        ) from exc

    cf_headers = request.headers.getlist("cf-connecting-ip")
    try:
        cf_ip = (
            str(ipaddress.ip_address(cf_headers[0].strip()))
            if len(cf_headers) == 1
            else None
        )
    except ValueError:
        cf_ip = None

    try:
        application_ip = get_client_ip(request)
        application_matches = hmac.compare_digest(application_ip, expected_ip)
    except HTTPException:
        application_matches = False

    # Do not return or log IP addresses or the diagnostic token.
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    return ClientIPDiagnosticResponse(
        cloudflare_header_matches_expected=(
            cf_ip is not None and hmac.compare_digest(cf_ip, expected_ip)
        ),
        application_ip_matches_expected=application_matches,
    )
