# ServiceNow MCP Server

A Model Context Protocol (MCP) server built with FastMCP for ServiceNow API integration. This server provides AI assistants with tools to interact with ServiceNow incident management system using OAuth2 authentication and Bearer Token security.

## Features

- **FastMCP Framework**: Clean, efficient MCP server implementation
- **OAuth2 Authentication**: Secure client credentials flow with automatic token refresh
- **Bearer Token Security**: JWT-based authentication with identity provider integration
- **Multiple Transports**: Support for stdio, HTTP, and SSE protocols
- **Complete CRUD Operations**: Create, read, update, and search ServiceNow incidents
- **Scope-based Authorization**: Fine-grained access control with read/write scopes
- **CrewAI Compatible**: HTTP/SSE endpoints for AI agent integration
- **Docker Support**: Containerized deployment with health checks and MCP Inspector
- **Type Safety**: Pydantic models for data validation
- **Retry Logic**: Automatic retry with exponential backoff for network failures

## Project Structure

```
servicenow-mcp-server/
├── src/
│   ├── api/                     # ServiceNow API client
│   │   ├── __init__.py
│   │   ├── client.py            # OAuth2 client with retry logic
│   │   └── exceptions.py        # Custom exception types
│   ├── auth/                    # Bearer Token authentication
│   │   ├── __init__.py
│   │   └── bearer_token.py      # JWT verification & identity provider
│   ├── models/                  # Pydantic data models
│   │   ├── __init__.py
│   │   └── incident.py          # Incident request/response models
│   ├── tools/                   # MCP tool implementations
│   │   ├── __init__.py
│   │   └── incident_tools.py    # Incident CRUD operations
│   ├── __init__.py
│   ├── config.py                # Configuration management
│   └── fastmcp_server.py        # FastMCP server implementation
├── scripts/
│   └── run_fastmcp_server.py    # Server startup script
├── tests/                       # Test scripts
│   ├── test_fastmcp_client.py   # FastMCP client tests
│   ├── test_create_incident.py  # Create incident tests
│   ├── test_update_incident.py  # Update incident tests
│   └── test_search_incidents.py # Search incident tests
├── docker-compose.yml           # Docker orchestration with MCP Inspector
├── Dockerfile                   # Container definition
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Project metadata
├── .env.example                # Environment template
└── README.md                   # This file
```

## Requirements

- Python 3.10+
- ServiceNow instance with OAuth2 client credentials
- Docker (optional, for containerized deployment)

## Installation

### Local Development

1. Clone the repository:
```bash
git clone <repository-url>
cd servicenow-mcp-server
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your ServiceNow credentials
```

### Environment Variables

Create a `.env` file with the following variables:

```env
# ServiceNow API Configuration
SERVICENOW_BASE_URL=https://yourinstance.service-now.com
SERVICENOW_CLIENT_ID=your_oauth_client_id
SERVICENOW_CLIENT_SECRET=your_oauth_client_secret

# Optional: Override default OAuth token endpoint
# SERVICENOW_TOKEN_ENDPOINT=/oauth_token.do

# API Configuration
SERVICENOW_API_VERSION=v1
SERVICENOW_API_NAMESPACE=x_dusal_cmspapi
SERVICENOW_TIMEOUT=30
SERVICENOW_MAX_RETRIES=3
SERVICENOW_VERIFY_SSL=true

# MCP Server Configuration
MCP_SERVER_NAME=servicenow-mcp
LOG_LEVEL=INFO
ENABLE_DEBUG=false

# MCP Bearer Token Authentication Configuration
MCP_AUTH_ENABLE_AUTH=false
MCP_AUTH_AUTH_MODE=mock
MCP_AUTH_IDENTITY_JWKS_URI=https://example.com/jwks
MCP_AUTH_API_IDENTIFIER=ServiceNowMCPServerAPI
MCP_AUTH_INCIDENT_READ_SCOPE=servicenow.incident.read
MCP_AUTH_INCIDENT_WRITE_SCOPE=servicenow.incident.write
```

### Authentication Modes

The server supports two authentication modes:

#### 1. Mock Authentication (Development)
```env
MCP_AUTH_ENABLE_AUTH=true
MCP_AUTH_AUTH_MODE=mock
```
Uses predefined mock tokens for testing. Valid tokens include: `valid_auth_token`, `VALID_AUTH_TOKEN`, `mock_token`, etc.

#### 2. Identity Provider Authentication (Production)
```env
MCP_AUTH_ENABLE_AUTH=true
MCP_AUTH_AUTH_MODE=identity-provider
MCP_AUTH_IDENTITY_JWKS_URI=https://your-identity-provider.com/.well-known/jwks.json
MCP_AUTH_API_IDENTIFIER=your-api-identifier
```
Uses JWT token verification with OIDC-compatible identity provider.

### Authorization Scopes

- `servicenow.incident.read` - Required for: get_incident, search_incidents, list_incident_fields
- `servicenow.incident.write` - Required for: create_incident, update_incident

## Usage

### Running the Server

#### Stdio Transport (Default)
```bash
python scripts/run_fastmcp_server.py --transport stdio
```

#### HTTP Transport
```bash
python scripts/run_fastmcp_server.py --transport http --host 0.0.0.0 --port 8000
```

#### SSE Transport
```bash
python scripts/run_fastmcp_server.py --transport sse --host 0.0.0.0 --port 8000
```

### Docker Deployment

#### HTTP/SSE Transport with MCP Inspector (Default)
```bash
docker-compose up
```
This starts:
- ServiceNow MCP Server on port 8000
- MCP Inspector on port 6274 for testing and debugging

#### Stdio Transport
```bash
docker-compose --profile stdio up servicenow-mcp-stdio
```

#### MCP Inspector Access
After starting with docker-compose, access the MCP Inspector at:
- **Inspector UI**: http://localhost:6274
- **Inspector WebSocket**: ws://localhost:6277

### Testing

Run the test scripts to verify functionality:

```bash
# Test FastMCP client integration
python test_fastmcp_client.py

# Test incident creation
python test_create_incident.py

# Test incident updates
python test_update_incident.py

# Test incident search functionality
python test_search_incidents.py
```

## API Endpoints (HTTP/SSE Transport)

- **Root**: `http://localhost:8000/` - Server information
- **Health**: `http://localhost:8000/health` - Health check endpoint
- **Tools**: `http://localhost:8000/mcp/tools` - List available tools
- **Call**: `http://localhost:8000/mcp/call` - Execute tool calls
- **SSE**: `http://localhost:8000/sse` - Server-sent events endpoint

## Available Tools

### 1. `get_incident`
Retrieves comprehensive details about a ServiceNow incident.
**Required Scope:** `servicenow.incident.read`

**Parameters:**
- `incident_number` (string): The incident number (e.g., INC654321)

**Returns:**
- Formatted incident details including basic information, assignment details, timestamps, and associated tasks

### 2. `create_incident`
Creates a new ServiceNow incident.
**Required Scope:** `servicenow.incident.write`

**Parameters:**
- `short_description` (string): Brief description (max 120 chars) - **REQUIRED**
- `description` (string): Full description (max 4000 chars) - **REQUIRED**
- `service_name` (string): Service name - **REQUIRED**
- `urgency` (int): Urgency level (1=Critical, 2=High, 3=Medium, 4=Low) - **REQUIRED**
- `impact` (int): Impact level (1=Critical, 2=High, 3=Medium, 4=Low)
- `category` (string): Category (e.g., "Performance")
- `subcategory` (string): Subcategory (e.g., "Timeout")
- Additional optional fields: `configuration_item`, `assigned_to`, `assignment_group`, etc.

### 3. `update_incident`
Updates an existing ServiceNow incident.
**Required Scope:** `servicenow.incident.write`

**Parameters:**
- `incident_number` (string): The incident number to update - **REQUIRED**
- `state` (int): Incident state (1=New, 2=In Progress, 3=On Hold, 6=Resolved, 7=Closed, 8=Canceled)
- `impact` (int): Impact level (1=Critical, 2=High, 3=Medium, 4=Low)
- `urgency` (int): Urgency level (1=Critical, 2=High, 3=Medium, 4=Low)
- Additional optional fields: `category`, `subcategory`, `short_description`, `description`, etc.

### 4. `search_incidents`
Searches ServiceNow incidents based on criteria.
**Required Scope:** `servicenow.incident.read`

**Parameters:**
- `active` (bool): Select active records (default True)
- `requested_by` (string): Search by incident requestor name
- `company` (string): Search by company value
- `service_name` (string): Search by service name
- `category` (string): Search by category
- `state` (int): Search by incident state
- `priority` (int): Search by priority
- Additional optional search fields

### 5. `list_incident_fields`
Lists all available incident fields with descriptions and examples.
**Required Scope:** `servicenow.incident.read`

**Parameters:** None

**Returns:**
- Comprehensive list of incident fields with descriptions and examples

## ServiceNow API Integration

The server connects to ServiceNow's custom API endpoints:

- **Base URL**: `{SERVICENOW_BASE_URL}/api/{namespace}/{version}`
- **Incident Endpoint**: `/itsm/incident/{incident_number}`
- **OAuth Token**: `/oauth_token.do`

### OAuth2 Flow

1. Client credentials are exchanged for access token
2. Token is cached and automatically refreshed before expiration
3. All API requests include Bearer token authentication

## CrewAI Integration

For CrewAI compatibility, use the HTTP transport:

```python
# In your CrewAI configuration
tools_endpoint = "http://localhost:8000/mcp/tools"
call_endpoint = "http://localhost:8000/mcp/call"

# Example tool call
response = requests.post(call_endpoint, json={
    "name": "get_incident",
    "arguments": {"incident_number": "INC1234567"}
})
```

## Development

### Adding New Tools

1. Create tool implementation in `src/tools/`
2. Add FastMCP tool decorator with scope authorization in `src/fastmcp_server.py`:

```python
@server.tool
@require_scope(auth_config.incident_read_scope)  # or incident_write_scope
async def your_new_tool(param: str) -> str:
    """Tool description."""
    # Implementation
    return result
```

### Error Handling

The server includes comprehensive error handling:
- `ServiceNowAuthError`: OAuth2 authentication failures
- `ServiceNowNotFoundError`: Resource not found (404)
- `ServiceNowRateLimitError`: Rate limiting (429)
- `ServiceNowAPIError`: General API errors

### Logging

Structured logging with:
- Colored console output for development
- File rotation (10MB max, 5 backups)
- Contextual error logging
- API request/response tracking

## Security Considerations

- OAuth2 client credentials are stored securely in environment variables
- Bearer Token authentication with JWT verification
- Scope-based authorization for fine-grained access control
- SSL verification is enabled by default
- Docker container runs as non-root user
- Sensitive data is never logged
- Identity provider integration for enterprise authentication

## Troubleshooting

### Common Issues

1. **OAuth2 Authentication Failed**
   - Verify client_id and client_secret are correct
   - Ensure OAuth2 client has necessary permissions
   - Check ServiceNow instance URL

2. **Bearer Token Authentication Failed**
   - Verify `MCP_AUTH_IDENTITY_JWKS_URI` is accessible
   - Check JWT token format and claims
   - Ensure API identifier matches identity provider configuration
   - Verify token has required scopes

3. **Authorization Errors**
   - Check if token has required scope (read/write)
   - Verify `MCP_AUTH_ENABLE_AUTH` setting
   - Review scope configuration in identity provider

4. **Connection Errors**
   - Verify network connectivity to ServiceNow instance
   - Check SSL certificate validity
   - Review proxy settings if applicable

5. **Docker Issues**
   - Ensure .env file exists and is readable
   - Check port availability (8000, 6274, 6277)
   - Review Docker logs: `docker-compose logs`

### Debug Mode

Enable debug logging:
```bash
LOG_LEVEL=DEBUG ENABLE_DEBUG=true python scripts/run_fastmcp_server.py
```


## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python test_*.py`
5. Submit a pull request

## Support

For issues or questions:
- Create an issue in the repository
- Check existing documentation
- Review test examples in `test_*.py` files
- Use MCP Inspector for debugging: http://localhost:6274