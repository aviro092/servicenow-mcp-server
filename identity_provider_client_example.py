#!/usr/bin/env python3
"""
Dell Identity Integration Client Example for ServiceNow MCP Server

This script demonstrates how to authenticate with Dell Identity G2 environment
and access the ServiceNow MCP Server as a protected resource.

Prerequisites:
1. Register your application in Dell Identity portal as 'Web' type
2. Get client credentials from DI portal  
3. Register ServiceNow MCP Server as API type in DI portal
4. Subscribe your client to the ServiceNow MCP API in DI portal
"""

import asyncio
import base64
import hashlib
import json
import secrets
import urllib.parse
import webbrowser
from typing import Dict, Any, Optional
import httpx


class DellIdentityMCPClient:
    """Client for accessing ServiceNow MCP Server via Dell Identity authentication."""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        mcp_server_url: str = "https://your-mcp-server.dell.com",
        environment: str = "G2"
    ):
        """Initialize Dell Identity MCP client.
        
        Args:
            client_id: Your Dell Identity client ID (from DI portal)
            client_secret: Your Dell Identity client secret (from DI portal)
            mcp_server_url: URL of your ServiceNow MCP server
            environment: Dell Identity environment (G1, G2, G3, G4, Perf, Prod)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.mcp_server_url = mcp_server_url
        self.environment = environment
        
        # Dell Identity environment endpoints
        self.endpoints = {
            "G1": {
                "auth": "https://di-federationgateway-g1.di-np.pcf.dell.com/dci/fp/oidc/authorize",
                "token": "https://di-federationgateway-g1.di-np.pcf.dell.com/dci/fp/oidc/token",
                "discovery": "https://www-sit-g1.dell.com/di/v3/fp/oidc/v3/.well-known/openid-configuration"
            },
            "G2": {
                "auth": "https://di-federationgateway-g2.di-np.pcf.dell.com/dci/fp/oidc/authorize",
                "token": "https://di-federationgateway-g2.di-np.pcf.dell.com/dci/fp/oidc/token", 
                "discovery": "https://www-sit-g2.dell.com/di/v3/fp/oidc/v3/.well-known/openid-configuration"
            },
            "G3": {
                "auth": "https://di-federationgateway-g3.di-np.pcf.dell.com/dci/fp/oidc/authorize",
                "token": "https://di-federationgateway-g3.di-np.pcf.dell.com/dci/fp/oidc/token",
                "discovery": "https://www-sit-g3.dell.com/di/v3/fp/oidc/v3/.well-known/openid-configuration"
            },
            "G4": {
                "auth": "https://di-federationgateway-g4.di-np.pcf.dell.com/dci/fp/oidc/authorize", 
                "token": "https://di-federationgateway-g4.di-np.pcf.dell.com/dci/fp/oidc/token",
                "discovery": "https://www-sit-g4.dell.com/di/v3/fp/oidc/v3/.well-known/openid-configuration"
            },
            "Perf": {
                "auth": "https://di-federationgateway-perf.di-np.pcf.dell.com/dci/fp/oidc/authorize",
                "token": "https://di-federationgateway-perf.di-np.pcf.dell.com/dci/fp/oidc/token",
                "discovery": "https://www-perf.dell.com/di/v3/fp/oidc/v3/.well-known/openid-configuration"
            },
            "Prod": {
                "auth": "https://www.dell.com/dci/fp/oidc/authorize",
                "token": "https://www.dell.com/dci/fp/oidc/token",
                "discovery": "https://www.dell.com/di/v3/fp/oidc/v3/.well-known/openid-configuration"
            }
        }
        
        # PKCE parameters
        self.code_verifier = self._generate_code_verifier()
        self.code_challenge = self._generate_code_challenge(self.code_verifier)
        self.state = secrets.token_urlsafe(32)
        
        # Token storage
        self.access_token = None
        self.id_token = None
        self.refresh_token = None
        
    def _generate_code_verifier(self) -> str:
        """Generate PKCE code verifier."""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    
    def _generate_code_challenge(self, verifier: str) -> str:
        """Generate PKCE code challenge."""
        digest = hashlib.sha256(verifier.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
    
    async def discover_mcp_server_metadata(self) -> Dict[str, Any]:
        """Discover MCP server OAuth metadata."""
        print("🔍 Step 1: Discovering MCP server OAuth metadata...")
        
        async with httpx.AsyncClient() as client:
            # Get protected resource metadata
            prm_response = await client.get(f"{self.mcp_server_url}/.well-known/oauth-protected-resource")
            prm_data = prm_response.json()
            print(f"✅ Protected Resource Metadata: {json.dumps(prm_data, indent=2)}")
            
            # Get authorization server metadata  
            asm_response = await client.get(f"{self.mcp_server_url}/.well-known/oauth-authorization-server")
            asm_data = asm_response.json()
            print(f"✅ Authorization Server Metadata: {json.dumps(asm_data, indent=2)}")
            
            return {"prm": prm_data, "asm": asm_data}
    
    def build_authorization_url(self, scopes: str = "openid profile servicenow.incident.read servicenow.incident.write") -> str:
        """Build Dell Identity authorization URL with PKCE."""
        print("🔗 Step 2: Building Dell Identity authorization URL...")
        
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": "https://your-app.dell.com/callback",  # Replace with your registered redirect URI
            "scope": scopes,
            "state": self.state,
            "code_challenge": self.code_challenge,
            "code_challenge_method": "S256"
        }
        
        auth_url = f"{self.endpoints[self.environment]['auth']}?{urllib.parse.urlencode(params)}"
        print(f"✅ Authorization URL: {auth_url}")
        return auth_url
    
    async def exchange_code_for_tokens(self, authorization_code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens using Dell Identity."""
        print("🔄 Step 3: Exchanging authorization code for tokens...")
        
        token_data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": "https://your-app.dell.com/callback",  # Must match authorization request
            "code_verifier": self.code_verifier,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.endpoints[self.environment]["token"],
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                token_response = response.json()
                print(f"✅ Token response: {json.dumps(token_response, indent=2)}")
                
                self.access_token = token_response.get("access_token")
                self.id_token = token_response.get("id_token")
                self.refresh_token = token_response.get("refresh_token")
                
                return token_response
            else:
                raise Exception(f"Token exchange failed: {response.status_code} - {response.text}")
    
    async def get_client_credentials_token(self, scopes: str = "servicenow.incident.read servicenow.incident.write") -> Dict[str, Any]:
        """Get access token using client credentials flow."""
        print("🤖 Using Client Credentials Flow...")
        
        # For Dell Identity API protection, you'll use this endpoint
        api_token_endpoint = f"https://www-sit-{self.environment.lower()}.dell.com/di/api/v3/oauth/token"
        
        # Create Basic Auth header
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "client_credentials",
            "scope": scopes
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(api_token_endpoint, headers=headers, data=data)
            
            if response.status_code == 200:
                token_response = response.json()
                print(f"✅ Client Credentials Token: {json.dumps(token_response, indent=2)}")
                self.access_token = token_response.get("access_token")
                return token_response
            else:
                print(f"❌ Client credentials flow failed: {response.status_code} - {response.text}")
                raise Exception(f"Client credentials flow failed: {response.status_code} - {response.text}")
    
    async def test_mcp_server_access(self) -> Optional[Dict[str, Any]]:
        """Test accessing ServiceNow MCP server with Dell Identity token."""
        print("🛡️  Step 4: Testing MCP server access with Dell Identity token...")
        
        if not self.access_token:
            raise Exception("No access token available. Please authenticate first.")
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            # Test MCP tools endpoint
            response = await client.get(f"{self.mcp_server_url}/mcp/tools", headers=headers)
            
            print(f"MCP server response status: {response.status_code}")
            if response.status_code == 200:
                tools = response.json()
                print(f"✅ Successfully accessed MCP server! Available tools: {len(tools.get('tools', []))}")
                return tools
            elif response.status_code == 401:
                print("❌ 401 Unauthorized - Token may be invalid or expired")
                print(f"Response: {response.text}")
                return None
            else:
                print(f"❌ MCP server access failed: {response.status_code} - {response.text}")
                return None
    
    async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call an MCP tool with the authenticated token."""
        if not self.access_token:
            raise Exception("No access token available. Please authenticate first.")
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        tool_call_data = {
            "name": tool_name,
            "arguments": arguments
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.mcp_server_url}/mcp/call",
                headers=headers,
                json=tool_call_data
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Tool '{tool_name}' executed successfully")
                return result
            else:
                print(f"❌ Tool call failed: {response.status_code} - {response.text}")
                return None
    
    async def run_full_test(self, use_client_credentials: bool = True):
        """Run complete Dell Identity integration test."""
        print("🚀 Starting Dell Identity ServiceNow MCP Integration Test")
        print(f"🌍 Environment: {self.environment}")
        print("=" * 70)
        
        try:
            # Step 1: Discover MCP server metadata
            await self.discover_mcp_server_metadata()
            print()
            
            # Step 2: Get access token
            if use_client_credentials:
                # For API-to-API access, use client credentials
                await self.get_client_credentials_token()
            else:
                # For user-interactive flows, show authorization URL
                auth_url = self.build_authorization_url()
                print(f"\n🌐 For user authentication, visit: {auth_url}")
                print("   After authorization, extract the 'code' parameter from callback URL")
                auth_code = input("Enter the authorization code from callback: ").strip()
                await self.exchange_code_for_tokens(auth_code)
            
            print()
            
            # Step 3: Test MCP server access
            tools = await self.test_mcp_server_access()
            print()
            
            # Step 4: Try calling a tool (optional)
            if tools and tools.get('tools'):
                # Example: Call list_incident_fields if available
                incident_tools = [t for t in tools['tools'] if 'incident' in t.get('name', '').lower()]
                if incident_tools:
                    tool_name = incident_tools[0]['name']
                    print(f"🔧 Testing tool call: {tool_name}")
                    await self.call_mcp_tool(tool_name, {})
            
            print("\n🎉 Dell Identity integration test completed successfully!")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Main test function."""
    print("Dell Identity ServiceNow MCP Client Example")
    print("=" * 50)
    
    # Configuration - Replace with your actual values from DI portal
    CLIENT_ID = "your-dell-identity-client-id"  # From DI portal registration
    CLIENT_SECRET = "your-dell-identity-client-secret"  # From DI portal
    MCP_SERVER_URL = "https://your-mcp-server.dell.com"  # Your MCP server URL
    ENVIRONMENT = "G2"  # G1, G2, G3, G4, Perf, or Prod
    
    if CLIENT_ID == "your-dell-identity-client-id":
        print("⚠️  Please update CLIENT_ID, CLIENT_SECRET, and MCP_SERVER_URL with your actual values")
        print("\nSteps to get these values:")
        print("1. Register in Dell Identity portal as 'Web' application")
        print("2. Register your MCP server as 'API' application")
        print("3. Subscribe your client to your API")
        print("4. Update configuration in this script")
        return
    
    client = DellIdentityMCPClient(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        mcp_server_url=MCP_SERVER_URL,
        environment=ENVIRONMENT
    )
    
    await client.run_full_test(use_client_credentials=True)


if __name__ == "__main__":
    asyncio.run(main())