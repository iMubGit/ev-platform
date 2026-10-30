import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core import rate_limit
from app.core.config import settings


def make_request(
    client_ip: str = "192.0.2.10",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> Request:
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "https",
            "path": "/auth/token",
            "raw_path": b"/auth/token",
            "query_string": b"",
            "headers": headers or [],
            "client": (client_ip, 12345),
            "server": ("test", 443),
        }
    )


def test_direct_mode_ignores_spoofed_proxy_headers(monkeypatch):
    monkeypatch.setattr(settings, "trust_cloudflare_client_ip", False)
    request = make_request(
        headers=[
            (b"x-forwarded-for", b"198.51.100.200"),
            (b"cf-connecting-ip", b"203.0.113.200"),
        ]
    )

    assert rate_limit.get_client_ip(request) == "192.0.2.10"


def test_cloudflare_mode_uses_validated_cf_connecting_ip(monkeypatch):
    monkeypatch.setattr(settings, "trust_cloudflare_client_ip", True)
    request = make_request(
        headers=[
            (b"x-forwarded-for", b"198.51.100.200"),
            (b"cf-connecting-ip", b"203.0.113.25"),
        ]
    )

    assert rate_limit.get_client_ip(request) == "203.0.113.25"


def test_cloudflare_mode_accepts_ipv6(monkeypatch):
    monkeypatch.setattr(settings, "trust_cloudflare_client_ip", True)
    request = make_request(
        headers=[(b"cf-connecting-ip", b"2001:db8::1234")]
    )

    assert rate_limit.get_client_ip(request) == "2001:db8::1234"


@pytest.mark.parametrize(
    "headers",
    [
        [],
        [(b"cf-connecting-ip", b"not-an-ip")],
        [(b"cf-connecting-ip", b"203.0.113.1, 198.51.100.2")],
        [(b"cf-connecting-ip", b"")],
    ],
)
def test_cloudflare_mode_fails_closed_for_missing_or_invalid_ip(
    monkeypatch, headers
):
    monkeypatch.setattr(settings, "trust_cloudflare_client_ip", True)

    with pytest.raises(HTTPException) as error:
        rate_limit.get_client_ip(make_request(headers=headers))

    assert error.value.status_code == 503


def test_cloudflare_mode_creates_separate_rate_limit_keys_per_visitor(monkeypatch):
    monkeypatch.setattr(settings, "trust_cloudflare_client_ip", True)
    first = make_request(
        headers=[(b"cf-connecting-ip", b"203.0.113.10")]
    )
    second = make_request(
        headers=[(b"cf-connecting-ip", b"203.0.113.11")]
    )

    assert rate_limit._login_keys(first, "admin") != rate_limit._login_keys(
        second, "admin"
    )


def test_turnstile_ip_and_rate_limit_ip_share_same_trusted_source(monkeypatch):
    monkeypatch.setattr(settings, "trust_cloudflare_client_ip", True)
    request = make_request(
        headers=[
            (b"x-forwarded-for", b"198.51.100.200"),
            (b"cf-connecting-ip", b"203.0.113.30"),
        ]
    )

    assert rate_limit.get_client_ip(request) == "203.0.113.30"
    ip_key, _ = rate_limit._login_keys(request, "admin")
    assert ip_key.endswith(
        __import__("hashlib").sha256(b"203.0.113.30").hexdigest()
    )
