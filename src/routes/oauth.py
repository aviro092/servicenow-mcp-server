"""OAuth authentication routes for MCP server."""

import json
import logging
from typing import Dict, Any, Optional
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from auth.oauth_provider import OAuthProvider
from config import get_auth_config

logger = logging.getLogger(__name__)
oauth_provider = OAuthProvider()


async def protected_resource_metadata(request: Request) -> JSONResponse:
    """Return Protected Resource Metadata (PRM) document.
    
    This endpoint provides metadata about the protected resource
    as defined in RFC 8707.
    """
    metadata = oauth_provider.get_protected_resource_metadata()
    logger.info("Served protected resource metadata")
    
    return JSONResponse(
        content=metadata,
        headers={
            "Content-Type": "application/json",
            "Cache-Control": "public, max-age=3600"
        }
    )


async def authorization_server_metadata(request: Request) -> JSONResponse:
    """Return Authorization Server Metadata document.
    
    This endpoint provides metadata about the authorization server
    as defined in RFC 8414.
    """
    metadata = oauth_provider.get_authorization_server_metadata()
    logger.info("Served authorization server metadata")
    
    return JSONResponse(
        content=metadata,
        headers={
            "Content-Type": "application/json",
            "Cache-Control": "public, max-age=3600"
        }
    )


async def client_id_metadata_document(request: Request) -> JSONResponse:
    """Return Client ID Metadata Document (CIMD).
    
    This endpoint provides pre-registered client metadata
    for a specific client ID.
    """
    client_id = request.path_params.get("client_id")
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id required")
    
    # For demo purposes, generate CIMD for any requested client
    redirect_uris = [get_auth_config().oauth_redirect_uri]
    metadata = oauth_provider.generate_client_id_metadata_document(client_id, redirect_uris)
    
    logger.info(f"Served CIMD for client: {client_id}")
    
    return JSONResponse(
        content=metadata,
        headers={
            "Content-Type": "application/json"
        }
    )


async def dynamic_client_registration(request: Request) -> JSONResponse:
    """Handle Dynamic Client Registration (DCR).
    
    This endpoint allows clients to register themselves dynamically
    as defined in RFC 7591.
    """
    try:
        registration_request = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")
    
    # Validate required fields
    required_fields = ["redirect_uris"]
    for field in required_fields:
        if field not in registration_request:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    
    try:
        client_metadata = await oauth_provider.register_client_dynamically(registration_request)
        
        logger.info(f"Dynamic client registration successful: {client_metadata['client_id']}")
        
        return JSONResponse(
            content=client_metadata,
            status_code=201,
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "no-store"
            }
        )
        
    except Exception as e:
        logger.error(f"Dynamic client registration failed: {e}")
        raise HTTPException(status_code=400, detail="Client registration failed")


async def oauth_authorize(request: Request) -> Response:
    """Handle OAuth authorization requests.
    
    This is a simplified authorization endpoint that would normally
    present a user consent screen.
    """
    # Extract query parameters
    client_id = request.query_params.get("client_id")
    redirect_uri = request.query_params.get("redirect_uri")
    scope = request.query_params.get("scope")
    state = request.query_params.get("state")
    code_challenge = request.query_params.get("code_challenge")
    code_challenge_method = request.query_params.get("code_challenge_method")
    response_type = request.query_params.get("response_type")
    
    # Validate required parameters
    if not all([client_id, redirect_uri, response_type]):
        raise HTTPException(status_code=400, detail="Missing required parameters")
    
    if response_type != "code":
        raise HTTPException(status_code=400, detail="Unsupported response_type")
    
    # Validate client
    if not oauth_provider.validate_client_credentials(client_id):
        raise HTTPException(status_code=400, detail="Invalid client_id")
    
    # In a real implementation, this would present a consent screen
    # For this demo, we'll auto-approve and redirect with a code
    
    # Generate authorization code (simplified)
    import secrets
    auth_code = secrets.token_urlsafe(32)
    
    # Store code with associated data (in production, use proper storage)
    # This is simplified for demo purposes
    
    # Build redirect URL with authorization code
    redirect_params = {"code": auth_code}
    if state:
        redirect_params["state"] = state
    
    import urllib.parse
    redirect_url = f"{redirect_uri}?{urllib.parse.urlencode(redirect_params)}"
    
    logger.info(f"Authorization granted for client {client_id}, redirecting to {redirect_uri}")
    
    return RedirectResponse(url=redirect_url, status_code=302)


async def oauth_token(request: Request) -> JSONResponse:
    """Handle OAuth token requests.
    
    This endpoint exchanges authorization codes for access tokens.
    """
    # Parse form data
    try:
        form_data = await request.form()
        grant_type = form_data.get("grant_type")
        
        if grant_type == "authorization_code":
            # Handle authorization code flow
            code = form_data.get("code")
            client_id = form_data.get("client_id")
            client_secret = form_data.get("client_secret")
            redirect_uri = form_data.get("redirect_uri")
            code_verifier = form_data.get("code_verifier")
            
            # Validate client credentials
            if not oauth_provider.validate_client_credentials(client_id, client_secret):
                raise HTTPException(status_code=401, detail="Invalid client credentials")
            
            # In production, validate the authorization code and code_verifier
            # For this demo, we'll generate a token response
            
            import jwt
            import time
            
            # Generate access token (simplified)
            token_payload = {
                "sub": "demo-user",
                "aud": get_auth_config().resource_server_url,
                "iss": get_auth_config().oauth_authorization_endpoint.split('/oauth')[0],
                "exp": int(time.time()) + 3600,  # 1 hour
                "iat": int(time.time()),
                "scope": form_data.get("scope", get_auth_config().oauth_scope),
                "client_id": client_id
            }
            
            # In production, use proper signing key
            access_token = jwt.encode(token_payload, "demo-secret", algorithm="HS256")
            
            token_response = {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": token_payload["scope"]
            }
            
            logger.info(f"Token issued for client {client_id}")
            
            return JSONResponse(
                content=token_response,
                headers={
                    "Content-Type": "application/json",
                    "Cache-Control": "no-store",
                    "Pragma": "no-cache"
                }
            )
            
        elif grant_type == "client_credentials":
            # Handle client credentials flow
            client_id = form_data.get("client_id")
            client_secret = form_data.get("client_secret")
            scope = form_data.get("scope", get_auth_config().oauth_scope)
            
            # Validate client credentials
            if not oauth_provider.validate_client_credentials(client_id, client_secret):
                raise HTTPException(status_code=401, detail="Invalid client credentials")
            
            import jwt
            import time
            
            # Generate access token for client credentials flow
            token_payload = {
                "sub": client_id,
                "aud": get_auth_config().resource_server_url,
                "iss": get_auth_config().oauth_authorization_endpoint.split('/oauth')[0],
                "exp": int(time.time()) + 3600,  # 1 hour
                "iat": int(time.time()),
                "scope": scope,
                "client_id": client_id,
                "grant_type": "client_credentials"
            }
            
            # In production, use proper signing key
            access_token = jwt.encode(token_payload, "demo-secret", algorithm="HS256")
            
            token_response = {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": scope
            }
            
            logger.info(f"Client credentials token issued for {client_id}")
            
            return JSONResponse(
                content=token_response,
                headers={
                    "Content-Type": "application/json",
                    "Cache-Control": "no-store",
                    "Pragma": "no-cache"
                }
            )
        
        else:
            raise HTTPException(status_code=400, detail="Unsupported grant_type")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token request failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid token request")


async def oauth_userinfo(request: Request) -> JSONResponse:
    """Return user information based on the access token.
    
    This endpoint provides user information for the authenticated user.
    """
    # Extract Bearer token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    
    token = auth_header[7:]  # Remove "Bearer " prefix
    
    try:
        # Validate and decode token (simplified)
        import jwt
        payload = jwt.decode(token, "demo-secret", algorithms=["HS256"])
        
        # Return user info based on token
        user_info = {
            "sub": payload.get("sub"),
            "name": "Demo User",
            "email": "demo@example.com",
            "preferred_username": payload.get("sub"),
            "scope": payload.get("scope")
        }
        
        logger.info(f"Served user info for subject: {payload.get('sub')}")
        
        return JSONResponse(content=user_info)
        
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token in userinfo request: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")