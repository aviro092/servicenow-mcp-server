# Dell Identity Integration Setup Guide

This guide explains how to integrate your ServiceNow MCP Server with Dell Identity (DI) G2 environment for OAuth authentication.

## Prerequisites

1. Access to Dell Identity portal for your team
2. ServiceNow MCP Server deployed and accessible
3. Understanding of OAuth 2.0 and OIDC flows

## Step 1: Register in Dell Identity Portal

### 1.1 Get Access to DI Portal

- **Existing Group**: Contact your team's group owner for access. Check [registered applications list](https://your-di-portal-link.dell.com).
- **New Group**: Raise a ServiceNow ticket to create a new Application Group.

### 1.2 Register Your MCP Server as API

1. Log into Dell Identity portal
2. Navigate to **Application Registration**
3. Create new application with type **"API"**
4. Fill in details:
   - **Application Name**: `servicenow-mcp-server`
   - **Description**: `ServiceNow MCP Server for AI integration`
   - **API URL**: `https://your-mcp-server.dell.com`
   - **Scopes**: Define your API scopes:
     - `servicenow.incident.read`
     - `servicenow.incident.write`
     - `servicenow.changerequest.read`
     - `servicenow.changerequest.write`
     - `servicenow.incidenttask.read`
     - `servicenow.incidenttask.write`

### 1.3 Register Your Client Application

1. Create another application with type **"Web"**
2. Fill in details:
   - **Application Name**: `my-mcp-client`
   - **Redirect URIs**: `https://your-app.dell.com/callback`
   - **Grant Types**: `authorization_code`, `client_credentials`
   - **Scopes**: Request access to your API scopes

### 1.4 Subscribe Client to API

1. Go to your client application settings
2. Navigate to **Subscriptions**
3. Subscribe to your `servicenow-mcp-server` API
4. Select required scopes

## Step 2: Configure Your MCP Server

### 2.1 Environment Configuration

Copy the `.env.dell-identity.example` file to `.env`:

```bash
cp .env.dell-identity.example .env
```

Update the configuration with your Dell Identity settings:

```env
# Dell Identity Integration
MCP_AUTH_ENABLE_AUTH=true
MCP_AUTH_AUTH_MODE=identity-provider

# Dell Identity G2 Environment
MCP_AUTH_IDENTITY_JWKS_URI=https://www-sit-g2.dell.com/di/v3/fp/oidc/v3/.well-known/jwks.json
MCP_AUTH_IDENTITY_DISCOVERY_URL=https://www-sit-g2.dell.com/di/v3/fp/oidc/v3/.well-known/openid-configuration
MCP_AUTH_API_IDENTIFIER=your-servicenow-mcp-api-identifier

# OAuth Endpoints for Client Reference
MCP_AUTH_OAUTH_AUTHORIZATION_ENDPOINT=https://di-federationgateway-g2.di-np.pcf.dell.com/dci/fp/oidc/authorize
MCP_AUTH_OAUTH_TOKEN_ENDPOINT=https://di-federationgateway-g2.di-np.pcf.dell.com/dci/fp/oidc/token

# Resource Server (Your MCP Server)
MCP_AUTH_RESOURCE_SERVER_URL=https://your-mcp-server.dell.com
MCP_AUTH_REALM=Dell ServiceNow MCP Server

# Client Credentials (from DI portal)
DELL_IDENTITY_CLIENT_ID=your-registered-client-id
DELL_IDENTITY_CLIENT_SECRET=your-client-secret
```

### 2.2 Start Your MCP Server

```bash
python scripts/run_fastmcp_server.py --transport http --port 8000
```

## Step 3: Client Integration

### 3.1 Using the Example Client

Update the client example with your credentials:

```python
# In dell_identity_client_example.py
CLIENT_ID = "your-dell-identity-client-id"  # From DI portal
CLIENT_SECRET = "your-dell-identity-client-secret"  # From DI portal
MCP_SERVER_URL = "https://your-mcp-server.dell.com"  # Your MCP server
ENVIRONMENT = "G2"  # Dell Identity environment
```

Run the test:

```bash
python dell_identity_client_example.py
```

### 3.2 Client Authentication Flow

For **Client Credentials Flow** (API-to-API):

```python
import httpx
import base64

# Dell Identity API protection endpoint
token_endpoint = "https://www-sit-g2.dell.com/di/api/v3/oauth/token"

# Create Basic Auth header
credentials = f"{client_id}:{client_secret}"
encoded_credentials = base64.b64encode(credentials.encode()).decode()

headers = {
    "Authorization": f"Basic {encoded_credentials}",
    "Content-Type": "application/x-www-form-urlencoded"
}

data = {
    "grant_type": "client_credentials",
    "scope": "servicenow.incident.read servicenow.incident.write"
}

async with httpx.AsyncClient() as client:
    response = await client.post(token_endpoint, headers=headers, data=data)
    token_data = response.json()
    access_token = token_data["access_token"]
```

For **Authorization Code Flow** (User Authentication):

```python
# 1. Redirect user to authorization URL
auth_url = "https://di-federationgateway-g2.di-np.pcf.dell.com/dci/fp/oidc/authorize"
params = {
    "response_type": "code",
    "client_id": your_client_id,
    "redirect_uri": "https://your-app.dell.com/callback",
    "scope": "openid profile servicenow.incident.read",
    "state": random_state,
    "code_challenge": pkce_challenge,
    "code_challenge_method": "S256"
}

# 2. Handle callback with authorization code
# 3. Exchange code for tokens at token endpoint
```

### 3.3 Making API Calls

Once you have the access token:

```python
# Access MCP server endpoints
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# Get available tools
response = await client.get(f"{mcp_server_url}/mcp/tools", headers=headers)

# Call a specific tool
tool_call = {
    "name": "get_incident", 
    "arguments": {"incident_number": "INC123456"}
}
response = await client.post(f"{mcp_server_url}/mcp/call", headers=headers, json=tool_call)
```

## Step 4: Environment-Specific Configuration

### Dell Identity Environments

| Environment | Authorization Endpoint | Token Endpoint | Discovery Endpoint |
|-------------|----------------------|----------------|-------------------|
| **G1** | `https://di-federationgateway-g1.di-np.pcf.dell.com/dci/fp/oidc/authorize` | `https://di-federationgateway-g1.di-np.pcf.dell.com/dci/fp/oidc/token` | `https://www-sit-g1.dell.com/di/v3/fp/oidc/v3/.well-known/openid-configuration` |
| **G2** | `https://di-federationgateway-g2.di-np.pcf.dell.com/dci/fp/oidc/authorize` | `https://di-federationgateway-g2.di-np.pcf.dell.com/dci/fp/oidc/token` | `https://www-sit-g2.dell.com/di/v3/fp/oidc/v3/.well-known/openid-configuration` |
| **G3** | `https://di-federationgateway-g3.di-np.pcf.dell.com/dci/fp/oidc/authorize` | `https://di-federationgateway-g3.di-np.pcf.dell.com/dci/fp/oidc/token` | `https://www-sit-g3.dell.com/di/v3/fp/oidc/v3/.well-known/openid-configuration` |
| **G4** | `https://di-federationgateway-g4.di-np.pcf.dell.com/dci/fp/oidc/authorize` | `https://di-federationgateway-g4.di-np.pcf.dell.com/dci/fp/oidc/token` | `https://www-sit-g4.dell.com/di/v3/fp/oidc/v3/.well-known/openid-configuration` |
| **Perf** | `https://di-federationgateway-perf.di-np.pcf.dell.com/dci/fp/oidc/authorize` | `https://di-federationgateway-perf.di-np.pcf.dell.com/dci/fp/oidc/token` | `https://www-perf.dell.com/di/v3/fp/oidc/v3/.well-known/openid-configuration` |
| **Prod** | `https://www.dell.com/dci/fp/oidc/authorize` | `https://www.dell.com/dci/fp/oidc/token` | `https://www.dell.com/di/v3/fp/oidc/v3/.well-known/openid-configuration` |

### API Protection Token Endpoints

For **Client Credentials** flow, use these endpoints:

| Environment | API Token Endpoint |
|-------------|-------------------|
| **G1** | `https://www-sit-g1.dell.com/di/api/v3/oauth/token` |
| **G2** | `https://www-sit-g2.dell.com/di/api/v3/oauth/token` |
| **G3** | `https://www-sit-g3.dell.com/di/api/v3/oauth/token` |
| **G4** | `https://www-sit-g4.dell.com/di/api/v3/oauth/token` |
| **Perf** | `https://www-perf.dell.com/di/api/v3/oauth/token` |
| **Prod** | `https://www.dell.com/di/api/v3/oauth/token` |

## Step 5: Testing

### 5.1 Test MCP Server OAuth Metadata

```bash
curl https://your-mcp-server.dell.com/.well-known/oauth-protected-resource
curl https://your-mcp-server.dell.com/.well-known/oauth-authorization-server
```

### 5.2 Test Token Generation

```bash
# Client Credentials Flow
curl -X POST https://www-sit-g2.dell.com/di/api/v3/oauth/token \
  -H "Authorization: Basic $(echo -n 'client_id:client_secret' | base64)" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&scope=servicenow.incident.read"
```

### 5.3 Test MCP Server Access

```bash
# Test without token (should return 401)
curl https://your-mcp-server.dell.com/mcp/tools

# Test with token (should return tools list)
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://your-mcp-server.dell.com/mcp/tools
```

### 5.4 Run Integration Test

```bash
python dell_identity_client_example.py
```

## Troubleshooting

### Common Issues

1. **401 Unauthorized**
   - Verify client credentials are correct
   - Check token hasn't expired
   - Ensure client is subscribed to API in DI portal

2. **403 Forbidden** 
   - Check scope permissions
   - Verify client has required scopes for the API endpoint

3. **Token Validation Errors**
   - Verify JWKS URI is accessible
   - Check Dell Identity environment settings
   - Ensure API identifier matches registration

4. **CORS Issues**
   - Configure proper CORS headers on your MCP server
   - Use appropriate redirect URIs

### Debug Mode

Enable debug logging:

```bash
LOG_LEVEL=DEBUG python scripts/run_fastmcp_server.py --transport http --port 8000
```

## Production Deployment

### Before Production

1. **Register in Production Environment**
   - Contact Dell Identity team 5 days before production deployment
   - Migrate applications from SIT to Prod using Push & Export feature

2. **Update Configuration**
   - Use Production endpoints
   - Update environment variables
   - Test thoroughly in Perf environment first

3. **Security Considerations**
   - Use HTTPS for all endpoints
   - Implement proper CORS policies
   - Monitor authentication logs
   - Set up proper key rotation

### Production Configuration

```env
# Production Dell Identity Settings
MCP_AUTH_IDENTITY_JWKS_URI=https://www.dell.com/di/v3/fp/oidc/v3/.well-known/jwks.json
MCP_AUTH_IDENTITY_DISCOVERY_URL=https://www.dell.com/di/v3/fp/oidc/v3/.well-known/openid-configuration
MCP_AUTH_OAUTH_AUTHORIZATION_ENDPOINT=https://www.dell.com/dci/fp/oidc/authorize
MCP_AUTH_OAUTH_TOKEN_ENDPOINT=https://www.dell.com/dci/fp/oidc/token
```

## Support

- **Dell Identity Documentation**: Check the DI portal documentation
- **ServiceNow Integration**: Refer to your ServiceNow API documentation
- **MCP Server Issues**: Check server logs and authentication middleware
- **OAuth Flow Issues**: Verify client registration and subscription in DI portal