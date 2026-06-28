"""
Security Headers Middleware
===========================
Adds standard security headers to every HTTP response to mitigate
common web vulnerabilities (XSS, clickjacking, MIME sniffing, etc.).

Headers added:
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy: camera=(), microphone=(), geolocation=()
- Strict-Transport-Security (HTTPS only)
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


# Security headers applied to every response
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}

# HSTS header for HTTPS connections
HSTS_HEADER_VALUE = "max-age=31536000; includeSubDomains"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that adds security headers to all responses."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Process the request
        response = await call_next(request)

        # Add standard security headers
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value

        # Add HSTS header for HTTPS requests
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = HSTS_HEADER_VALUE

        return response
