# ServiceNow MCP Server

A Model Context Protocol (MCP) server built with FastMCP for ServiceNow API integration. This server provides AI assistants with tools to interact with ServiceNow incident management system using OAuth2 authentication.

## Features

- **FastMCP Framework**: Clean, efficient MCP server implementation
- **OAuth2 Authentication**: Secure client credentials flow with automatic token refresh
- **Multiple Transports**: Support for stdio, HTTP, and SSE protocols
- **Incident Management**: Retrieve and format ServiceNow incident details
- **CrewAI Compatible**: HTTP/SSE endpoints for AI agent integration
- **Docker Support**: Containerized deployment with health checks
- **Comprehensive Logging**: Structured logging with rotation and colored output
- **Type Safety**: Pydantic models for data validation
- **Retry Logic**: Automatic retry with exponential backoff for network failures

## Project Structure

```
servicenow-mcp-server/
├── src/
│   └── servicenow_mcp/
│       ├── api/                 # ServiceNow API client
│       │   ├── __init__.py
│       │   ├── client.py        # OAuth2 client with retry logic
│       │   └── exceptions.py    # Custom exception types
│       ├── models/              # Pydantic data models
│       │   ├── __init__.py
│       │   └── incident.py      # Incident response models
│       ├── tools/               # MCP tool implementations
│       │   ├── __init__.py
│       │   └── incident_tools.py # Incident-related tools
│       ├── __init__.py
│       ├── config.py            # Configuration management
│       ├── fastmcp_server.py    # FastMCP server implementation
│       └── logging_config.py    # Logging configuration
├── scripts/
│   └── run_fastmcp_server.py    # Server startup script
├── docker-compose.yml           # Docker orchestration
├── Dockerfile                   # Container definition
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Project metadata
├── test_server.py              # Test suite
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
```

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

#### HTTP/SSE Transport (Default)
```bash
docker-compose up
```

#### Stdio Transport
```bash
docker-compose --profile stdio up servicenow-mcp-stdio
```

### Testing

Run the comprehensive test suite:
```bash
python test_server.py
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

**Parameters:**
- `incident_number` (string): The incident number (e.g., INC654321)

**Returns:**
- Formatted incident details including:
  - Basic information (number, state, priority)
  - Contact & classification details
  - Assignment information
  - Timestamps
  - Description and resolution details
  - Associated incident tasks
  - Notes and comments

**Example:**
```json
{
  "name": "get_incident",
  "arguments": {
    "incident_number": "INC1234567"
  }
}
```

### 2. `list_incident_fields`
Lists all available incident fields with descriptions and examples.

**Parameters:** None

**Returns:**
- Comprehensive list of incident fields
- Field descriptions and data types
- Example values for each field

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

1. Create tool implementation in `src/servicenow_mcp/tools/`
2. Add FastMCP tool decorator in `fastmcp_server.py`:

```python
@server.tool
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
- SSL verification is enabled by default
- Docker container runs as non-root user
- Sensitive data is never logged

## Troubleshooting

### Common Issues

1. **OAuth2 Authentication Failed**
   - Verify client_id and client_secret are correct
   - Ensure OAuth2 client has necessary permissions
   - Check ServiceNow instance URL

2. **Connection Errors**
   - Verify network connectivity to ServiceNow instance
   - Check SSL certificate validity
   - Review proxy settings if applicable

3. **Docker Issues**
   - Ensure .env file exists and is readable
   - Check port availability (8000 by default)
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
4. Run tests: `python test_server.py`
5. Submit a pull request

## Support

For issues or questions:
- Create an issue in the repository
- Check existing documentation
- Review test examples in `test_server.py`