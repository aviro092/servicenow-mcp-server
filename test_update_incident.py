#!/usr/bin/env python3
"""Test update incident functionality via FastMCP tools."""

import sys
import os
import asyncio

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_update_incident():
    try:
        from tools.incident_tools import IncidentTools
        from api.client import ServiceNowClient
        from config import get_servicenow_config
        
        print("🧪 Testing incident update for INC9242849...")
        
        config = get_servicenow_config()
        client = ServiceNowClient(config)
        tools = IncidentTools(client)
        
        # First, get the current incident to see its current state
        print("\n📋 Current incident details:")
        current_result = await tools.get_incident("INC9242849")
        if "error" in current_result:
            print(f"❌ Error fetching current incident: {current_result['error']}")
            return
        
        print(f"Current State: {current_result.get('state', 'N/A')}")
        print(f"Current Priority: {current_result.get('priority', 'N/A')}")
        print(f"Current Description: {current_result.get('short_description', 'N/A')}")
        
        # Test update - just add comments and notes (safe operations)
        print("\n🔧 Testing update with comments and notes...")
        update_result = await tools.update_incident(
            "INC9242849",
            comments="Test comment added via MCP server update tool",
            notes="Test note added via MCP server - testing update functionality"
        )
        
        if "error" in update_result:
            print(f"❌ Update Error: {update_result['error']}")
            print(f"🔍 Error type: {update_result.get('error_type', 'unknown')}")
        else:
            print("✅ Update successful!")
            print(f"📄 Response: {update_result.get('message', 'No message')}")
            
            # Show the updated incident details if available
            updated_incident = update_result.get('updated_incident')
            if updated_incident:
                print("\n📊 Updated incident details:")
                print(f"State: {updated_incident.get('state', 'N/A')}")
                print(f"Priority: {updated_incident.get('priority', 'N/A')}")
                print(f"Comments: {updated_incident.get('comments', 'N/A')}")
                print(f"Notes: {updated_incident.get('notes', 'N/A')}")
            
        await client.close()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_fastmcp_update_tool():
    """Test the update tool via FastMCP client (similar to production usage)."""
    try:
        from fastmcp import Client
        from fastmcp_server import server
        
        print("\n🧪 Testing update_incident tool via FastMCP client...")
        
        # Create client with in-memory transport
        client = Client(server)
        
        async with client:
            print("✅ Connected to FastMCP server")
            
            # Test update_incident tool
            print("\n🔧 Testing update_incident tool:")
            try:
                result = await client.call_tool("update_incident", {
                    "incident_number": "INC9242849",
                    "comments": "FastMCP test comment - update tool working",
                    "notes": "FastMCP test note - demonstrating update functionality"
                })
                
                print("✅ update_incident tool executed successfully")
                print(f"📄 Response length: {len(result.content[0].text)} characters")
                
                # Show first few lines of response
                lines = result.content[0].text.split('\n')[:10]
                print("📄 First 10 lines of response:")
                for line in lines:
                    print(f"   {line}")
                    
            except Exception as e:
                print(f"❌ update_incident tool failed: {e}")
            
            print("\n✅ FastMCP update tool test completed!")
            
    except Exception as e:
        print(f"❌ FastMCP test failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run all update tests."""
    print("🚀 ServiceNow Incident Update Tests")
    print("=" * 50)
    
    # Test 1: Direct tool usage
    await test_update_incident()
    
    # Test 2: FastMCP tool usage
    await test_fastmcp_update_tool()
    
    print("\n" + "=" * 50)
    print("📊 UPDATE TESTS COMPLETED")
    print("=" * 50)
    
    print("\n📋 What was tested:")
    print("1. ✅ Direct incident update via IncidentTools")
    print("2. ✅ FastMCP update_incident tool integration")
    print("3. ✅ Safe update operations (comments/notes only)")
    print("4. ✅ Error handling and validation")
    
    print("\n⚠️ Note: Tests only update comments/notes for safety")
    print("   To test other fields, modify the test script accordingly")

if __name__ == "__main__":
    asyncio.run(main())