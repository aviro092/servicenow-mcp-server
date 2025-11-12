"""MCP Prompt handlers for ServiceNow analysis and automation."""

import logging
from typing import Optional
from container import get_container

logger = logging.getLogger(__name__)


async def incident_analysis_prompt(
    incident_number: str,
    analysis_type: str = "root_cause"
) -> str:
    """Generate a prompt for incident analysis.
    
    This prompt helps analyze ServiceNow incidents for root cause,
    impact assessment, or resolution strategies.
    
    Args:
        incident_number: The incident to analyze (e.g., INC9243406)
        analysis_type: Type of analysis - root_cause, impact, or resolution
    
    Returns:
        Formatted prompt with incident context for AI analysis
    """
    logger.info(f"Generating {analysis_type} analysis prompt for {incident_number}")
    
    try:
        # Get incident data using existing tools
        container = get_container()
        tools = await container.get_incident_tools()
        incident_data = await tools.get_incident(incident_number)
        
        if "error" in incident_data:
            return f"Error: Could not fetch incident {incident_number} - {incident_data['error']}"
        
        # Format incident data for prompt
        from tools.incident_tools import format_incident_display
        formatted_incident = format_incident_display(incident_data)
        
        if analysis_type == "root_cause":
            prompt = f"""You are a ServiceNow incident analyst. Analyze the following incident and provide root cause analysis.

## Incident Details:
{formatted_incident}

## Analysis Tasks:
1. **Identify Root Cause**: Based on the symptoms and description, what is the likely root cause?
2. **Contributing Factors**: What system conditions or events may have contributed?
3. **Similar Patterns**: Does this match any known issue patterns?
4. **Prevention Strategy**: How can similar incidents be prevented?
5. **Immediate Actions**: What should be done right now to mitigate impact?

Provide specific, technical, and actionable recommendations based on the incident details."""

        elif analysis_type == "impact":
            prompt = f"""You are a ServiceNow incident analyst. Assess the business impact of the following incident.

## Incident Details:
{formatted_incident}

## Impact Assessment Tasks:
1. **Service Impact**: Which services and systems are affected?
2. **User Impact**: How many users are likely affected? Which departments?
3. **Business Impact**: What is the revenue/operational impact?
4. **Risk Assessment**: What are the risks if this escalates?
5. **Priority Recommendation**: Should the priority be adjusted?

Provide specific metrics and quantifiable impact where possible."""

        elif analysis_type == "resolution":
            prompt = f"""You are a ServiceNow incident resolver. Provide resolution guidance for the following incident.

## Incident Details:
{formatted_incident}

## Resolution Tasks:
1. **Resolution Steps**: Provide step-by-step resolution procedure
2. **Verification Steps**: How to verify the issue is resolved
3. **Communication Plan**: Who should be notified and when
4. **Documentation**: What should be documented for future reference
5. **Follow-up Actions**: Any preventive measures or monitoring needed

Provide clear, actionable steps that a technician can follow."""
        
        else:
            prompt = f"""Analyze the following ServiceNow incident:

## Incident Details:
{formatted_incident}

Provide comprehensive analysis and recommendations."""
        
        logger.info(f"Successfully generated {analysis_type} prompt for {incident_number}")
        return prompt
        
    except Exception as e:
        logger.error(f"Error generating prompt for {incident_number}: {e}")
        return f"Error generating prompt: {str(e)}"


async def daily_incidents_summary_prompt(
    state: Optional[int] = None,
    priority: Optional[int] = None,
    assignment_group: Optional[str] = None
) -> str:
    """Generate a prompt for daily incident summary and trends.
    
    This prompt helps analyze multiple incidents for patterns and trends.
    
    Args:
        state: Filter by state (1=New, 2=In Progress, 3=On Hold, etc.)
        priority: Filter by priority (1=Critical, 2=High, 3=Medium, 4=Low)
        assignment_group: Filter by assignment group
    
    Returns:
        Formatted prompt with incidents summary for analysis
    """
    logger.info("Generating daily incidents summary prompt")
    
    try:
        container = get_container()
        tools = await container.get_incident_tools()
        
        # Build search parameters
        search_params = {"active": True}
        if state is not None:
            search_params["state"] = state
        if priority is not None:
            search_params["priority"] = priority
        if assignment_group:
            search_params["assignment_group"] = assignment_group
        
        # Search for incidents
        result = await tools.search_incidents(**search_params)
        
        if "error" in result:
            return f"Error searching incidents: {result['error']}"
        
        incidents_summary = f"""Found {result.get('count', 0)} incidents matching criteria:
- Active: True
- State: {state if state else 'All'}
- Priority: {priority if priority else 'All'}
- Assignment Group: {assignment_group if assignment_group else 'All'}

## Incidents List:
"""
        
        # Add incident summaries
        for i, incident in enumerate(result.get('incidents', [])[:20], 1):
            if isinstance(incident, dict):
                incidents_summary += f"""
### {i}. {incident.get('number', 'N/A')}
- State: {incident.get('state', 'N/A')}
- Priority: {incident.get('priority', 'N/A')}
- Short Description: {incident.get('short_description', 'N/A')}
- Assignment Group: {incident.get('assignment_group', 'N/A')}
- Created: {incident.get('created_date', 'N/A')}
"""
        
        prompt = f"""You are a ServiceNow operations manager. Analyze the following incidents and provide insights.

## Incident Summary:
{incidents_summary}

## Analysis Tasks:
1. **Trend Analysis**: Identify patterns in incident types, categories, or services
2. **Volume Analysis**: Are incident volumes normal, increasing, or decreasing?
3. **Hot Spots**: Which services or components have the most issues?
4. **Team Performance**: How are assignment groups performing?
5. **Priority Assessment**: Are incidents correctly prioritized?
6. **Action Items**: Top 3 immediate actions to improve service quality

Provide data-driven insights and specific recommendations."""
        
        logger.info(f"Successfully generated summary prompt for {result.get('count', 0)} incidents")
        return prompt
        
    except Exception as e:
        logger.error(f"Error generating summary prompt: {e}")
        return f"Error generating summary prompt: {str(e)}"


async def change_request_approval_prompt(
    changerequest_number: str
) -> str:
    """Generate a prompt for change request approval decision.
    
    This prompt helps evaluate change requests for approval decisions.
    
    Args:
        changerequest_number: The change request to evaluate (e.g., CHG0035060)
    
    Returns:
        Formatted prompt with change request details for approval analysis
    """
    logger.info(f"Generating approval prompt for change request {changerequest_number}")
    
    try:
        container = get_container()
        tools = await container.get_change_request_tools()
        cr_data = await tools.get_change_request(changerequest_number)
        
        if "error" in cr_data:
            return f"Error: Could not fetch change request {changerequest_number} - {cr_data['error']}"
        
        # Format change request data
        from tools.change_request_tools import format_change_request_display
        formatted_cr = format_change_request_display(cr_data["changerequest"])
        
        prompt = f"""You are a Change Advisory Board (CAB) member. Evaluate the following change request for approval.

## Change Request Details:
{formatted_cr}

## Evaluation Criteria:
1. **Risk Assessment**: 
   - What is the risk level (Low/Medium/High/Critical)?
   - What could go wrong?
   - What is the blast radius if it fails?

2. **Implementation Review**:
   - Is the implementation plan complete and clear?
   - Are all dependencies identified?
   - Is the timeline realistic?

3. **Testing Assessment**:
   - Is the test plan adequate?
   - Has similar changes been tested before?
   - What testing gaps exist?

4. **Rollback Plan**:
   - Is the backout plan comprehensive?
   - How quickly can we rollback if needed?
   - What data might be lost in rollback?

5. **Business Impact**:
   - What is the business benefit?
   - What is the cost of NOT doing this change?
   - Are stakeholders informed and ready?

## Final Recommendation:
- **Decision**: APPROVE / REJECT / DEFER
- **Conditions**: Any conditions for approval
- **Risk Mitigations**: Required safeguards
- **Follow-up**: Post-implementation requirements

Provide detailed justification for your recommendation."""
        
        logger.info(f"Successfully generated approval prompt for {changerequest_number}")
        return prompt
        
    except Exception as e:
        logger.error(f"Error generating approval prompt for {changerequest_number}: {e}")
        return f"Error generating approval prompt: {str(e)}"


async def automation_suggestions_prompt() -> str:
    """Generate a prompt for automation opportunity identification.
    
    This prompt analyzes recent incidents to identify automation opportunities.
    
    Returns:
        Formatted prompt with incident patterns for automation analysis
    """
    logger.info("Generating automation suggestions prompt")
    
    try:
        container = get_container()
        tools = await container.get_incident_tools()
        
        # Get recent resolved incidents to analyze patterns
        result = await tools.search_incidents(state=6, active=False)  # State 6 = Resolved
        
        if "error" in result:
            return f"Error searching incidents: {result['error']}"
        
        incident_patterns = f"""Analyzed {result.get('count', 0)} recently resolved incidents.

## Common Incident Categories:
"""
        
        # Group incidents by category
        categories = {}
        for incident in result.get('incidents', [])[:50]:
            if isinstance(incident, dict):
                cat = incident.get('category', 'Unknown')
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(incident.get('short_description', ''))
        
        for cat, descriptions in categories.items():
            incident_patterns += f"""
### {cat} ({len(descriptions)} incidents)
Sample issues:
"""
            for desc in descriptions[:3]:
                incident_patterns += f"- {desc}\n"
        
        prompt = f"""You are an IT automation specialist. Identify automation opportunities from these ServiceNow incidents.

## Incident Pattern Analysis:
{incident_patterns}

## Automation Analysis Tasks:

1. **Repeatable Patterns**: Which incident types occur frequently and could be automated?
2. **Self-Healing Opportunities**: Which issues could be automatically detected and resolved?
3. **Automated Diagnostics**: What diagnostic data collection could be automated?
4. **Proactive Monitoring**: What monitoring could prevent these incidents?
5. **Workflow Automation**: Which manual processes could be automated?

## Deliverables:
1. **Top 5 Automation Opportunities** (ranked by impact)
2. **Implementation Approach** for each opportunity
3. **Expected Benefits** (time saved, incidents prevented)
4. **Required Tools/Technologies**
5. **Quick Wins** (can be implemented in <1 week)

Focus on practical, high-impact automation that can be implemented with existing ServiceNow capabilities."""
        
        logger.info("Successfully generated automation suggestions prompt")
        return prompt
        
    except Exception as e:
        logger.error(f"Error generating automation prompt: {e}")
        return f"Error generating automation prompt: {str(e)}"