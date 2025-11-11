"""ServiceNow MCP Server built with FastMCP - Modular Version."""

import logging
import signal
import sys
from typing import Optional

from fastmcp import FastMCP

from container import get_container, cleanup_container
from registry import register_all_tools
from routes.health import health_check
from routes import oauth
from auth.identity_provider import create_identity_provider, IdentityProviderAuth
from auth.mcp_auth_middleware import MCPAuthMiddleware
from config import get_auth_config

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,  # Temporarily enable debug logging 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_server() -> FastMCP:
    """Create and configure the FastMCP server."""
    # Check if authentication should be enabled
    auth_config = get_auth_config()
    auth_provider = None
    
    if auth_config.enable_auth:
        logger.info(f"[SERVER] Authentication ENABLED - mode: {auth_config.auth_mode}")
        logger.info(f"[SERVER] JWKS URI: {auth_config.identity_jwks_uri}")
        logger.info(f"[SERVER] API Identifier: {auth_config.api_identifier}")
        # Initialize the auth provider for use in handlers
        auth_provider = create_identity_provider()
        logger.info("[SERVER] Authentication provider initialized successfully")
    else:
        logger.info("[SERVER] Authentication DISABLED - all requests will be allowed")
        auth_provider = None
    
    # Store auth provider globally for handlers to access
    import builtins
    builtins.global_auth_provider = auth_provider
    
    server = FastMCP(
        name="servicenow-mcp",
        instructions="ServiceNow MCP server for incident management and API integration",
        version="0.1.0"
    )
    
    # Add authentication middleware to capture Bearer tokens
    server.add_middleware(MCPAuthMiddleware)
    logger.info("Added MCP authentication middleware")
    
    # Register health check route
    server.custom_route("/health", methods=["GET"])(health_check)
    
    # Register OAuth routes (per MCP OAuth specification)
    server.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])(oauth.protected_resource_metadata)
    server.custom_route("/.well-known/oauth-authorization-server", methods=["GET"])(oauth.authorization_server_metadata)
    server.custom_route("/oauth/clients/{client_id}", methods=["GET"])(oauth.client_id_metadata_document)
    server.custom_route("/oauth/register", methods=["POST"])(oauth.dynamic_client_registration)
    server.custom_route("/oauth/authorize", methods=["GET"])(oauth.oauth_authorize)
    server.custom_route("/oauth/token", methods=["POST"])(oauth.oauth_token)
    server.custom_route("/oauth/userinfo", methods=["GET"])(oauth.oauth_userinfo)
    
    # Register all MCP tools
    register_all_tools(server)
    
    logger.info("ServiceNow MCP server configured successfully")
    return server


def setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        # Cleanup will be handled by the main function
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def initialize_services() -> None:
    """Initialize services during server startup."""
    logger.info("Starting ServiceNow MCP Server...")
    # Pre-initialize the container to validate configuration
    container = get_container()
    logger.info("Service container initialized")


async def cleanup_services() -> None:
    """Cleanup services during shutdown."""
    logger.info("Shutting down ServiceNow MCP Server...")
    await cleanup_container()
    logger.info("Cleanup completed")


def main() -> None:
    """Main entry point for ServiceNow MCP Server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ServiceNow FastMCP Server")
    parser.add_argument(
        "--transport", 
        choices=["stdio", "http", "sse"], 
        default="http",
        help="Transport protocol to use (default: http)"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host address for HTTP/SSE")
    parser.add_argument("--port", type=int, default=8000, help="Port for HTTP/SSE")
    parser.add_argument("--no-banner", action="store_true", help="Disable startup banner")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Configure debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Setup signal handlers
    setup_signal_handlers()
    
    # Initialize services
    initialize_services()
    
    # Create server
    server = create_server()
    
    try:
        logger.info(f"Starting server with transport: {args.transport}")
        if args.transport in ["http", "sse"]:
            logger.info(f"Server will be available at {args.transport}://{args.host}:{args.port}")
        
        # Run the server
        if args.transport == "stdio":
            server.run(
                transport=args.transport,
                show_banner=not args.no_banner
            )
        else:
            # HTTP and SSE transports
            server.run(
                transport=args.transport,
                host=args.host,
                port=args.port,
                show_banner=not args.no_banner
            )
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        # Ensure cleanup happens
        import asyncio
        try:
            asyncio.run(cleanup_services())
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


if __name__ == "__main__":
    main()