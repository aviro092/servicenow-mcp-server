"""Health check routes for ServiceNow MCP Server."""

from starlette.requests import Request
from starlette.responses import PlainTextResponse


async def health_check(request: Request) -> PlainTextResponse:
    """Health check endpoint for Docker health checks."""
    return PlainTextResponse("OK")