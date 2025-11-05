# ServiceNow MCP Server

A comprehensive Model Context Protocol (MCP) server built with FastMCP for ServiceNow API integration. This server provides AI assistants with tools to interact with ServiceNow's incident management, change requests, and incident tasks using OAuth2 authentication and Bearer Token security.

## Features

- **🏗️ Modular Architecture**: Clean, maintainable codebase with dependency injection
- **🔧 Complete ServiceNow Integration**: Full CRUD operations for incidents, change requests, and incident tasks
- **🔐 OAuth2 Authentication**: Secure client credentials flow with automatic token refresh
- **🛡️ Bearer Token Security**: JWT-based authentication with identity provider integration
- **🚀 Multiple Transports**: Support for stdio, HTTP, and SSE protocols
- **📋 15+ MCP Tools**: Comprehensive ServiceNow operations across all major record types
- **🔑 Scope-based Authorization**: Fine-grained access control with read/write scopes
- **🤖 CrewAI Compatible**: HTTP/SSE endpoints for AI agent integration
- **🐳 Docker Support**: Containerized deployment with health checks and MCP Inspector
- **✅ Type Safety**: Pydantic models for data validation and input sanitization
- **🔄 Retry Logic**: Automatic retry with exponential backoff for network failures
- **🧪 Comprehensive Testing**: Extensive test suite for all functionality

## Project Structure

```
servicenow-mcp-server/
├── src/
│   ├── api/                          # ServiceNow API client
│   │   ├── __init__.py
│   │   ├── client.py                 # OAuth2 client with retry logic
│   │   └── exceptions.py             # Custom exception types
│   ├── auth/                         # Bearer Token authentication
│   │   ├── __init__.py
│   │   └── bearer_token.py           # JWT verification & identity provider
│   ├── models/                       # Pydantic data models
│   │   ├── __init__.py
│   │   ├── incident.py               # Incident models
│   │   ├── change_request.py         # Change request models
│   │   └── incident_task.py          # Incident task models
│   ├── handlers/                     # 🆕 MCP tool handlers (modular)
│   │   ├── __init__.py
│   │   ├── incident_handlers.py      # Incident tool handlers
│   │   ├── change_request_handlers.py # Change request handlers
│   │   └── incident_task_handlers.py # Incident task handlers
│   ├── routes/                       # 🆕 HTTP routes
│   │   ├── __init__.py
│   │   └── health.py                 # Health check endpoint
│   ├── tools/                        # Business logic implementations
│   │   ├── __init__.py
│   │   ├── incident_tools.py         # Incident CRUD operations
│   │   ├── change_request_tools.py   # Change request operations
│   │   └── incident_task_tools.py    # Incident task operations
│   ├── __init__.py
│   ├── config.py                     # Configuration management
│   ├── container.py                  # 🆕 Dependency injection container
│   ├── registry.py                   # 🆕 Tool registration
│   ├── fastmcp_server.py             # 🆕 Clean modular server (125 lines)
│   └── fastmcp_server_bkp.py         # Original monolithic server backup
├── scripts/
│   └── run_fastmcp_server.py         # Server startup script
├── test/                             # Test scripts
│   ├── test_fastmcp_client.py        # FastMCP client tests
│   ├── test_create_incident.py       # Create incident tests
│   ├── test_update_incident.py       # Update incident tests
│   ├── test_search_incidents.py      # Search incident tests
│   └── test_change_request.py        # 🆕 Change request tests
├── docker-compose.yml                # Docker orchestration with MCP Inspector
├── Dockerfile                        # Container definition
├── requirements.txt                  # Python dependencies
├── pyproject.toml                   # Project metadata
├── .env.example                     # Environment template
└── README.md                        # This file
```

### 🏗️ Architecture Highlights

- **88.5% Reduction**: Main server file reduced from 1,087 to 125 lines
- **Single Responsibility**: Each module has one clear purpose
- **Dependency Injection**: Proper DI container replaces global variables  
- **Handler Pattern**: Business logic separated into focused handler modules
- **Easy Testing**: Each handler can be tested in isolation
- **Plugin-Ready**: Extensible architecture for adding new ServiceNow modules

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

# Authorization Scopes
MCP_AUTH_INCIDENT_READ_SCOPE=servicenow.incident.read
MCP_AUTH_INCIDENT_WRITE_SCOPE=servicenow.incident.write
MCP_AUTH_CHANGE_REQUEST_READ_SCOPE=servicenow.changerequest.read
MCP_AUTH_CHANGE_REQUEST_WRITE_SCOPE=servicenow.changerequest.write
MCP_AUTH_INCIDENT_TASK_READ_SCOPE=servicenow.incidenttask.read
MCP_AUTH_INCIDENT_TASK_WRITE_SCOPE=servicenow.incidenttask.write
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

#### Incident Management
- `servicenow.incident.read` - Required for: get_incident, search_incidents, list_incident_fields
- `servicenow.incident.write` - Required for: create_incident, update_incident

#### Change Request Management  
- `servicenow.changerequest.read` - Required for: search_change_requests, get_change_request, list_change_request_fields
- `servicenow.changerequest.write` - Required for: update_change_request, approve_change_request

#### Incident Task Management
- `servicenow.incidenttask.read` - Required for: get_incident_task, list_incident_task_fields  
- `servicenow.incidenttask.write` - Required for: create_incident_task, update_incident_task

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

The ServiceNow MCP Server provides **15+ comprehensive tools** across three main categories:

### 🎫 Incident Management (5 tools)

#### 1. `get_incident`
Retrieves comprehensive details about a ServiceNow incident.
**Required Scope:** `servicenow.incident.read`

**Parameters:**
- `incident_number` (string): The incident number (e.g., INC654321)

#### 2. `create_incident`
Creates a new ServiceNow incident.
**Required Scope:** `servicenow.incident.write`

**Required Parameters:**
- `short_description` (string): Brief description (max 120 chars)
- `description` (string): Full description (max 4000 chars)
- `service_name` (string): Service name mapped to cmdb_ci_service table
- `urgency` (int): Urgency level (1=Critical, 2=High, 3=Medium, 4=Low)

**Optional Parameters:**
- `impact`, `category`, `subcategory`, `configuration_item`, `assigned_to`, `assignment_group`, etc.

#### 3. `update_incident`
Updates an existing ServiceNow incident.
**Required Scope:** `servicenow.incident.write`

**Required Parameters:**
- `incident_number` (string): The incident number to update

**Optional Parameters:**
- `state`, `impact`, `urgency`, `category`, `subcategory`, `short_description`, `description`, etc.

#### 4. `search_incidents`
Searches ServiceNow incidents based on criteria.
**Required Scope:** `servicenow.incident.read`

**Parameters:** All optional - `active`, `requested_by`, `company`, `service_name`, `category`, `state`, `priority`, etc.

#### 5. `list_incident_fields`
Lists all available incident fields with descriptions and examples.
**Required Scope:** `servicenow.incident.read`

### 🔄 Change Request Management (5 tools)

#### 6. `search_change_requests`
Searches ServiceNow change requests based on criteria.
**Required Scope:** `servicenow.changerequest.read`

**Parameters:** All optional - `active`, `requested_by`, `company`, `type`, `priority`, `risk`, `impact`, `state`, etc.

#### 7. `get_change_request`
Retrieves comprehensive details about a ServiceNow change request.
**Required Scope:** `servicenow.changerequest.read`

**Parameters:**
- `changerequest_number` (string): The change request number (e.g., CHG0035060)

#### 8. `update_change_request`
Updates an existing ServiceNow change request.
**Required Scope:** `servicenow.changerequest.write`

**Required Parameters:**
- `changerequest_number` (string): The change request number to update
- `company_name` (string): Company name from company record

**Optional Parameters:**
- `description`, `comments`, `on_hold`, `on_hold_reason`, `resolved`, `customer_reference_id`

#### 9. `approve_change_request`
Approves or rejects a change request.
**Required Scope:** `servicenow.changerequest.write`

**Required Parameters:**
- `changerequest_number` (string): The change request number
- `state` (string): Either 'approved' or 'rejected'
- `approver_email` (string): Email of the approver user

**Optional Parameters:**
- `approver_name`, `on_behalf`

#### 10. `list_change_request_fields`
Lists all available change request fields with descriptions and examples.
**Required Scope:** `servicenow.changerequest.read`

### 📋 Incident Task Management (5 tools)

#### 11. `get_incident_task`
Retrieves comprehensive details about a ServiceNow incident task.
**Required Scope:** `servicenow.incidenttask.read`

**Parameters:**
- `incident_task_number` (string): The incident task number (e.g., TASK0133364)

#### 12. `create_incident_task`
Creates a new ServiceNow incident task.
**Required Scope:** `servicenow.incidenttask.write`

**Required Parameters:**
- `incident_number` (string): Parent incident number
- `short_description` (string): Task short description (max 120 chars)
- `service_name` (string): Service name mapped to cmdb_ci_service table
- `company_name` (string): Company name
- `configuration_item` (string): Configuration item sys_id

**Optional Parameters:**
- `description`, `priority`, `assignment_group`, `assigned_to`

#### 13. `update_incident_task`
Updates an existing ServiceNow incident task.
**Required Scope:** `servicenow.incidenttask.write`

**Required Parameters:**
- `incident_task_number` (string): The task number to update
- `short_description` (string): Task short description
- `state` (int): Task state (1=New, 2=In Progress, 3=On Hold, 6=Resolved, 7=Closed, 8=Canceled)

**Optional Parameters:**
- `description`, `priority`, `assignment_group`, `assigned_to`

#### 14. `list_incident_task_fields`
Lists all available incident task fields with descriptions and examples.
**Required Scope:** `servicenow.incidenttask.read`

### 📊 Summary

| Category | Read Tools | Write Tools | Total |
|----------|------------|-------------|-------|
| **Incidents** | 3 | 2 | 5 |
| **Change Requests** | 3 | 2 | 5 |  
| **Incident Tasks** | 2 | 2 | 4 |
| **TOTAL** | **8** | **6** | **14** |

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

### 🏗️ Modular Architecture

The new modular architecture makes development much easier:

```python
# 🆕 Clean main server (125 lines vs 1,087 lines originally)
src/fastmcp_server.py          # Server configuration only
src/container.py               # Dependency injection  
src/registry.py                # Tool registration
src/handlers/                  # MCP tool handlers
src/routes/                    # HTTP routes
src/tools/                     # Business logic
```

### Adding New Tools

The modular structure makes adding new tools simple:

#### 1. Create Business Logic
Add implementation in `src/tools/your_new_tools.py`:
```python
class YourNewTools:
    def __init__(self, client: ServiceNowClient):
        self.client = client
    
    async def your_operation(self, param: str) -> Dict[str, Any]:
        # Business logic here
        return result
```

#### 2. Create Handler
Add handler in `src/handlers/your_new_handlers.py`:
```python
@require_scope(auth_config.your_scope)
async def your_new_tool(param: str) -> str:
    """Tool description."""
    container = get_container()
    tools = await container.get_your_tools()
    result = await tools.your_operation(param)
    return formatted_result
```

#### 3. Register Tool
Add to `src/registry.py`:
```python
def register_your_tools(server: FastMCP) -> None:
    server.tool(your_handlers.your_new_tool)
```

#### 4. Update Container (if needed)
Add getter in `src/container.py` if new tool category:
```python
async def get_your_tools(self) -> YourNewTools:
    if self._your_tools is None:
        client = await self.get_client()
        self._your_tools = YourNewTools(client)
    return self._your_tools
```

### 🧪 Testing Individual Handlers

The modular architecture enables easy unit testing:

```python
# Test handlers in isolation
async def test_your_handler():
    # Mock the container
    mock_container = Mock()
    mock_tools = Mock()
    mock_container.get_your_tools.return_value = mock_tools
    
    # Test the handler
    with patch('handlers.your_handlers.get_container', return_value=mock_container):
        result = await your_handlers.your_new_tool("test_param")
        assert result == expected_result
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