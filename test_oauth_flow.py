#!/usr/bin/env python3
"""Test script for MCP OAuth authentication flow."""

import asyncio
import base64
import hashlib
import json
import secrets
import urllib.parse
import webbrowser
from typing import Dict, Any
import httpx


class MCPOAuthTester:
    """Test the MCP OAuth authentication flow."""
    
    def __init__(self, server_base_url: str = "http://localhost:8000"):
        """Initialize OAuth tester.
        
        Args:
            server_base_url: Base URL of the MCP server
        """
        self.server_base_url = server_base_url
        self.client_id = "mcp_demo_client"
        self.redirect_uri = "http://localhost:3000/callback"
        self.scope = "servicenow.incident.read servicenow.incident.write"
        
        # PKCE parameters
        self.code_verifier = self._generate_code_verifier()
        self.code_challenge = self._generate_code_challenge(self.code_verifier)
        self.state = secrets.token_urlsafe(32)
        
        self.access_token = None
        
    def _generate_code_verifier(self) -> str:
        """Generate PKCE code verifier."""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    
    def _generate_code_challenge(self, verifier: str) -> str:
        """Generate PKCE code challenge."""
        digest = hashlib.sha256(verifier.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
    
    async def discover_oauth_metadata(self) -> Dict[str, Any]:
        """Discover OAuth metadata from the server."""
        print("🔍 Step 1: Discovering OAuth metadata...")
        
        async with httpx.AsyncClient() as client:
            # Get protected resource metadata
            prm_response = await client.get(f"{self.server_base_url}/.well-known/oauth-protected-resource")
            prm_data = prm_response.json()
            print(f"✅ Protected Resource Metadata: {json.dumps(prm_data, indent=2)}")
            
            # Get authorization server metadata
            asm_response = await client.get(f"{self.server_base_url}/.well-known/oauth-authorization-server")
            asm_data = asm_response.json()
            print(f"✅ Authorization Server Metadata: {json.dumps(asm_data, indent=2)}")
            
            return {"prm": prm_data, "asm": asm_data}
    
    async def register_client_dynamically(self) -> Dict[str, Any]:
        """Register client using Dynamic Client Registration."""
        print("📝 Step 2: Registering client dynamically...")
        
        registration_request = {
            "client_name": "MCP Test Client",
            "redirect_uris": [self.redirect_uri],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "scope": self.scope
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.server_base_url}/oauth/register",
                json=registration_request
            )
            
            if response.status_code == 201:
                client_data = response.json()
                print(f"✅ Client registered successfully: {json.dumps(client_data, indent=2)}")
                self.client_id = client_data["client_id"]
                self.client_secret = client_data["client_secret"]
                return client_data
            else:
                raise Exception(f"Client registration failed: {response.status_code} - {response.text}")
    
    def build_authorization_url(self) -> str:
        """Build OAuth authorization URL."""
        print("🔗 Step 3: Building authorization URL...")
        
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "state": self.state,
            "code_challenge": self.code_challenge,
            "code_challenge_method": "S256",
            "resource": self.server_base_url
        }
        
        auth_url = f"{self.server_base_url}/oauth/authorize?{urllib.parse.urlencode(params)}"
        print(f"✅ Authorization URL: {auth_url}")
        return auth_url
    
    async def exchange_code_for_token(self, authorization_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        print("🔄 Step 4: Exchanging authorization code for access token...")
        
        token_data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": getattr(self, 'client_secret', 'demo_secret_12345'),
            "code_verifier": self.code_verifier
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.server_base_url}/oauth/token",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                token_response = response.json()
                print(f"✅ Token response: {json.dumps(token_response, indent=2)}")
                self.access_token = token_response["access_token"]
                return token_response
            else:
                raise Exception(f"Token exchange failed: {response.status_code} - {response.text}")
    
    async def test_client_credentials_flow(self) -> Dict[str, Any]:
        """Test the client credentials OAuth flow."""
        print("🤖 Testing Client Credentials Flow...")
        
        token_data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": getattr(self, 'client_secret', 'demo_secret_12345'),
            "scope": self.scope
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.server_base_url}/oauth/token",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                token_response = response.json()
                print(f"✅ Client Credentials Token: {json.dumps(token_response, indent=2)}")
                self.access_token = token_response["access_token"]
                return token_response
            else:
                raise Exception(f"Client credentials flow failed: {response.status_code} - {response.text}")
    
    async def test_protected_endpoint(self):
        """Test accessing protected MCP endpoint with token."""
        print("🛡️  Step 5: Testing protected endpoint access...")
        
        if not self.access_token:
            raise Exception("No access token available")
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # Test MCP tools endpoint
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.server_base_url}/mcp/tools",
                headers=headers
            )
            
            print(f"Protected endpoint response status: {response.status_code}")
            if response.status_code == 200:
                tools = response.json()
                print(f"✅ Successfully accessed protected endpoint. Available tools: {len(tools.get('tools', []))}")
                return tools
            else:
                print(f"❌ Protected endpoint access failed: {response.text}")
                return None
    
    async def test_without_token(self):
        """Test accessing protected endpoint without token to verify 401 response."""
        print("🚫 Testing access without token (expecting 401)...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.server_base_url}/mcp/tools")
            
            print(f"Response status without token: {response.status_code}")
            if response.status_code == 401:
                print("✅ Correctly received 401 Unauthorized")
                auth_header = response.headers.get("WWW-Authenticate")
                if auth_header:
                    print(f"✅ WWW-Authenticate header: {auth_header}")
                return True
            else:
                print(f"❌ Unexpected response: {response.status_code}")
                return False
    
    async def run_full_test(self):
        """Run the complete OAuth test flow."""
        print("🚀 Starting MCP OAuth Authentication Test")
        print("=" * 60)
        
        try:
            # Step 1: Discover metadata
            metadata = await self.discover_oauth_metadata()
            print()
            
            # Step 2: Register client (optional)
            try:
                await self.register_client_dynamically()
                print()
            except Exception as e:
                print(f"⚠️  Dynamic client registration failed (using pre-configured client): {e}")
                print()
            
            # Step 3: Test without token first
            await self.test_without_token()
            print()
            
            # Step 4: Test client credentials flow (simpler than authorization code)
            await self.test_client_credentials_flow()
            print()
            
            # Step 5: Test protected endpoint
            await self.test_protected_endpoint()
            print()
            
            print("🎉 OAuth test completed successfully!")
            
            # Optional: Show authorization code flow URL
            auth_url = self.build_authorization_url()
            print(f"\n🌐 For authorization code flow, visit: {auth_url}")
            print("   (This would open in a browser and redirect back with an authorization code)")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Main test function."""
    tester = MCPOAuthTester()
    await tester.run_full_test()


if __name__ == "__main__":
    asyncio.run(main())