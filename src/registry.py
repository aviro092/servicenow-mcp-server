"""Tool and Prompt registration for ServiceNow MCP Server."""

from fastmcp import FastMCP

from handlers import incident_handlers
from handlers import change_request_handlers
from handlers import incident_task_handlers
from handlers import prompt_handlers


def register_incident_tools(server: FastMCP) -> None:
    """Register all incident management tools."""
    server.tool(incident_handlers.get_incident)
    server.tool(incident_handlers.list_incident_fields)
    server.tool(incident_handlers.update_incident)
    server.tool(incident_handlers.create_incident)
    server.tool(incident_handlers.search_incidents)


def register_change_request_tools(server: FastMCP) -> None:
    """Register all change request management tools."""
    server.tool(change_request_handlers.search_change_requests)
    server.tool(change_request_handlers.get_change_request)
    server.tool(change_request_handlers.list_change_request_fields)
    server.tool(change_request_handlers.update_change_request)
    server.tool(change_request_handlers.approve_change_request)


def register_incident_task_tools(server: FastMCP) -> None:
    """Register all incident task management tools."""
    server.tool(incident_task_handlers.get_incident_task)
    server.tool(incident_task_handlers.list_incident_task_fields)
    server.tool(incident_task_handlers.update_incident_task)
    server.tool(incident_task_handlers.create_incident_task)


def register_prompts(server: FastMCP) -> None:
    """Register all ServiceNow MCP prompts."""
    # Register incident analysis prompts
    server.prompt(prompt_handlers.incident_analysis_prompt)
    server.prompt(prompt_handlers.daily_incidents_summary_prompt)
    
    # Register change request prompts
    server.prompt(prompt_handlers.change_request_approval_prompt)
    
    # Register automation prompts
    server.prompt(prompt_handlers.automation_suggestions_prompt)


def register_all_tools(server: FastMCP) -> None:
    """Register all ServiceNow MCP tools and prompts."""
    # Register tools
    register_incident_tools(server)
    register_change_request_tools(server)
    register_incident_task_tools(server)
    
    # Register prompts
    register_prompts(server)