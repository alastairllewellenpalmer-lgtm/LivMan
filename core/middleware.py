import logging
import time

logger = logging.getLogger("performance")


class ServerTimingMiddleware:
    """Adds Server-Timing header to every response and logs slow requests."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        total_ms = (time.monotonic() - start) * 1000

        response["Server-Timing"] = f"total;dur={total_ms:.1f}"

        if total_ms > 2000:
            logger.warning(
                "Slow request: %s %s took %.0fms",
                request.method,
                request.get_full_path(),
                total_ms,
            )

        return response
