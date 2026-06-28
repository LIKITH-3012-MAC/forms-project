"""
Request ID Middleware
=====================
Generates or propagates a unique request ID for every incoming request.
- If the client sends an `X-Request-ID` header, it is reused.
- Otherwise, a new UUID4 is generated.
- The request ID is stored in `request.state.request_id` and added
  to the `X-Request-ID` response header for tracing.
"""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns a unique request ID to every request."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Reuse client-provided request ID or generate a new one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Store on request state for downstream access
        request.state.request_id = request_id

        # Process the request
        response = await call_next(request)

        # Attach request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response
