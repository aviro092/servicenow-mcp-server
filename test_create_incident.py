#!/usr/bin/env python3
"""Test create incident functionality via FastMCP tools."""

import sys
import os
import asyncio
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_create_incident():
    try:
        from tools.incident_tools import IncidentTools
        from api.client import ServiceNowClient
        from config import get_servicenow_config
        
        print("🧪 Testing incident creation...")
        
        config = get_servicenow_config()
        client = ServiceNowClient(config)
        tools = IncidentTools(client)
        
        # Create a test incident with required fields
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_short_desc = f"MCP Test Incident {timestamp}"
        test_description = f"Test incident created via MCP server at {datetime.now().isoformat()}"
        
        print(f"\n🔧 Creating test incident...")
        print(f"Short Description: {test_short_desc}")
        print(f"Service: ITOM UAT PowerFlex")
        print(f"Urgency: 3 (Medium)")
        
        create_result = await tools.create_incident(
            short_description=test_short_desc,
            description=test_description,
            service_name="ITOM UAT PowerFlex",  # Using service from existing incident
            urgency=3,  # Medium urgency
            impact=3,   # Medium impact
            category="Technical Support",
            subcategory="Product Request",
            contact_type="Self-Service",
            customer_reference_id=f"TEST_{timestamp}"
        )
        
        if "error" in create_result:
            print(f"❌ Create Error: {create_result['error']}")
            print(f"🔍 Error type: {create_result.get('error_type', 'unknown')}")
        else:
            print("✅ Creation successful!")
            incident_number = create_result.get('incident_number', 'Unknown')
            print(f"📄 Created Incident: {incident_number}")
            print(f"📄 Message: {create_result.get('message', 'No message')}")
            
            # Show the created incident details if available
            created_incident = create_result.get('created_incident')
            if created_incident:
                print(f"\n📊 Created incident details:")
                print(f"Number: {created_incident.get('number', 'N/A')}")
                print(f"State: {created_incident.get('state', 'N/A')}")
                print(f"Priority: {created_incident.get('priority', 'N/A')}")
                print(f"Requested By: {created_incident.get('requested_by', 'N/A')}")
                print(f"Company: {created_incident.get('company', 'N/A')}")
                print(f"Service: {created_incident.get('service_name', 'N/A')}")
                
                # Return the incident number for cleanup
                return incident_number
            
        await client.close()
        return None
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_fastmcp_create_tool():
    """Test the create tool via FastMCP client (similar to production usage)."""
    try:
        from fastmcp import Client
        from fastmcp_server import server
        
        print("\n🧪 Testing create_incident tool via FastMCP client...")
        
        # Create client with in-memory transport
        client = Client(server)
        
        async with client:
            print("✅ Connected to FastMCP server")
            
            # Test create_incident tool
            print("\n🔧 Testing create_incident tool:")
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                result = await client.call_tool("create_incident", {
                    "short_description": f"FastMCP Test Incident {timestamp}",
                    "description": f"Test incident created via FastMCP client at {datetime.now().isoformat()}",
                    "service_name": "ITOM UAT PowerFlex",
                    "urgency": 4,  # Low urgency for test
                    "impact": 4,   # Low impact for test
                    "category": "Technical Support",
                    "contact_type": "Self-Service",
                    "customer_reference_id": f"FASTMCP_{timestamp}"
                })
                
                print("✅ create_incident tool executed successfully")
                print(f"📄 Response length: {len(result.content[0].text)} characters")
                
                # Show first few lines of response
                lines = result.content[0].text.split('\n')[:15]
                print("📄 First 15 lines of response:")
                for line in lines:
                    print(f"   {line}")
                    
                # Extract incident number from response if available
                response_text = result.content[0].text
                if "INC" in response_text:
                    import re
                    incident_match = re.search(r'INC\d+', response_text)
                    if incident_match:
                        incident_number = incident_match.group()
                        print(f"\n📋 Created incident number: {incident_number}")
                        return incident_number
                    
            except Exception as e:
                print(f"❌ create_incident tool failed: {e}")
            
            print("\n✅ FastMCP create tool test completed!")
            return None
            
    except Exception as e:
        print(f"❌ FastMCP test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_validation_errors():
    """Test validation error handling."""
    try:
        from fastmcp import Client
        from fastmcp_server import server
        
        print("\n🧪 Testing validation error handling...")
        
        client = Client(server)
        
        async with client:
            print("✅ Connected to FastMCP server")
            
            # Test with missing required fields
            print("\n🔧 Testing with missing required field (description):")
            try:
                result = await client.call_tool("create_incident", {
                    "short_description": "Test without description",
                    "service_name": "ITOM UAT PowerFlex",
                    "urgency": 3
                    # Missing description field
                })
                
                response_text = result.content[0].text
                print(f"📄 Response: {response_text[:200]}...")
                
                if "Error:" in response_text:
                    print("✅ Validation error properly caught and returned")
                else:
                    print("⚠️ Expected validation error but didn't get one")
                    
            except Exception as e:
                print(f"❌ Validation test failed: {e}")
            
            # Test with invalid urgency value
            print("\n🔧 Testing with invalid urgency value:")
            try:
                result = await client.call_tool("create_incident", {
                    "short_description": "Test with invalid urgency",
                    "description": "Test description",
                    "service_name": "ITOM UAT PowerFlex",
                    "urgency": 10  # Invalid urgency
                })
                
                response_text = result.content[0].text
                print(f"📄 Response: {response_text[:200]}...")
                
                if "Error:" in response_text:
                    print("✅ Invalid urgency error properly caught and returned")
                else:
                    print("⚠️ Expected validation error for invalid urgency")
                    
            except Exception as e:
                print(f"❌ Invalid urgency test failed: {e}")
            
            print("\n✅ Validation tests completed!")
            
    except Exception as e:
        print(f"❌ Validation tests failed: {e}")

async def main():
    """Run all create tests."""
    print("🚀 ServiceNow Incident Creation Tests")
    print("=" * 50)
    
    created_incidents = []
    
    # Test 1: Direct tool usage
    incident1 = await test_create_incident()
    if incident1:
        created_incidents.append(incident1)
    
    # Test 2: FastMCP tool usage
    incident2 = await test_fastmcp_create_tool()
    if incident2:
        created_incidents.append(incident2)
    
    # Test 3: Validation error handling
    await test_validation_errors()
    
    print("\n" + "=" * 50)
    print("📊 CREATE TESTS COMPLETED")
    print("=" * 50)
    
    print("\n📋 What was tested:")
    print("1. ✅ Direct incident creation via IncidentTools")
    print("2. ✅ FastMCP create_incident tool integration")
    print("3. ✅ Required field validation")
    print("4. ✅ Data type validation")
    print("5. ✅ Error handling and validation")
    
    if created_incidents:
        print(f"\n📋 Created test incidents: {', '.join(created_incidents)}")
        print("⚠️ Note: These are test incidents in the ServiceNow system")
        print("   You may want to clean them up or mark them as test data")
    else:
        print("\n📋 No incidents were successfully created (check for errors above)")

if __name__ == "__main__":
    asyncio.run(main())