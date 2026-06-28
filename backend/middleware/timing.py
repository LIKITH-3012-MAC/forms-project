"""
Request Timing Middleware
=========================
Records the start time of each incoming request and measures the
total processing duration. The duration (in milliseconds) is:
- Stored in `request.state.duration_ms`
- Added to the response as the `X-Response-Time` header
"""

import time
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware that measures and reports request processing time."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Record the start time
        start_time = time.perf_counter()

        # Process the request
        response = await call_next(request)

        # Calculate duration in milliseconds
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Store on request state for downstream access
        request.state.duration_ms = duration_ms

        # Attach timing header to response
        response.headers["X-Response-Time"] = f"{duration_ms}ms"

        return response
