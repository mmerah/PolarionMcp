import logging

logger = logging.getLogger(__name__)


class MCPPathFix:
    """
    ASGI middleware applied to the MCP HTTP server.

    Handles two quirks:

    1. Trailing-slash redirect — Starlette redirects POST /mcp → /mcp/ with 307,
       which clients (Copilot Studio, etc.) do not follow for POST requests.
       Normalise the path before it reaches the router so the redirect never fires.

    2. .well-known paths — Starlette's Mount("/mcp") catches requests like
       /mcp/.well-known/openid-configuration and the MCP handler returns 406,
       which makes clients (e.g. Claude Code) think OAuth is misconfigured
       instead of absent. Return 404 immediately.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # /mcp/.well-known/* → 404
        if "/.well-known/" in path:
            await send(
                {
                    "type": "http.response.start",
                    "status": 404,
                    "headers": [(b"content-type", b"text/plain")],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b"Not Found",
                    "more_body": False,
                }
            )
            return

        # /mcp → /mcp/ (prevent 307 redirect)
        if path == "/mcp":
            scope = dict(scope)
            scope["path"] = "/mcp/"
            scope["raw_path"] = b"/mcp/"

        await self.app(scope, receive, send)
