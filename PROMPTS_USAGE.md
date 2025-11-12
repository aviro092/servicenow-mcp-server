# ServiceNow MCP Server - Prompts Usage Guide

## 🎯 What are MCP Prompts?

MCP Prompts are pre-defined templates that combine ServiceNow data with AI-ready instructions. They fetch real data from ServiceNow and format it with specific analysis instructions.

## 📋 Available Prompts

### 1. **incident_analysis_prompt**
Analyzes a specific incident for root cause, impact, or resolution strategies.

**Parameters:**
- `incident_number` (required): The incident to analyze (e.g., "INC9243406")
- `analysis_type` (optional): "root_cause" | "impact" | "resolution" (default: "root_cause")

**Use Cases:**
- Root cause analysis of critical incidents
- Business impact assessment
- Step-by-step resolution guidance

### 2. **daily_incidents_summary_prompt**
Analyzes multiple incidents for patterns and trends.

**Parameters:**
- `state` (optional): Filter by state (1=New, 2=In Progress, etc.)
- `priority` (optional): Filter by priority (1=Critical, 2=High, 3=Medium, 4=Low)
- `assignment_group` (optional): Filter by team

**Use Cases:**
- Daily operations review
- Team performance analysis
- Incident trend identification

### 3. **change_request_approval_prompt**
Evaluates change requests for approval decisions.

**Parameters:**
- `changerequest_number` (required): The change request to evaluate (e.g., "CHG0035060")

**Use Cases:**
- CAB (Change Advisory Board) reviews
- Risk assessment
- Approval recommendations

### 4. **automation_suggestions_prompt**
Identifies automation opportunities from incident patterns.

**Parameters:** None (analyzes recent resolved incidents)

**Use Cases:**
- Process improvement
- Automation opportunity identification
- Self-healing system design

## 🚀 How to Use Prompts

### Via MCP Client (e.g., Claude Desktop)

1. **List available prompts:**
```json
{
  "method": "prompts/list"
}
```

2. **Get a specific prompt:**
```json
{
  "method": "prompts/get",
  "params": {
    "name": "incident_analysis_prompt",
    "arguments": {
      "incident_number": "INC9243406",
      "analysis_type": "root_cause"
    }
  }
}
```

### Via HTTP API

1. **List prompts endpoint:**
```bash
POST http://localhost:8000/mcp
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "prompts/list",
  "id": 1
}
```

2. **Get prompt endpoint:**
```bash
POST http://localhost:8000/mcp
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "prompts/get",
  "params": {
    "name": "incident_analysis_prompt",
    "arguments": {
      "incident_number": "INC9243406",
      "analysis_type": "root_cause"
    }
  },
  "id": 2
}
```

## 💡 Example Workflow

### Incident Root Cause Analysis

1. **Get the prompt:**
```python
# The prompt will fetch incident INC9243406 data and format it
prompt = get_prompt("incident_analysis_prompt", {
    "incident_number": "INC9243406",
    "analysis_type": "root_cause"
})
```

2. **The prompt returns formatted text with:**
- Complete incident details from ServiceNow
- Specific analysis instructions
- Structured questions for the AI to answer

3. **Feed to AI for analysis:**
- The AI receives the incident context + analysis framework
- Provides root cause analysis based on actual ServiceNow data

### Daily Operations Review

1. **Get summary of high-priority incidents:**
```python
prompt = get_prompt("daily_incidents_summary_prompt", {
    "priority": 2,  # High priority
    "state": 2      # In Progress
})
```

2. **AI analyzes the data and provides:**
- Trend analysis
- Hot spots identification
- Team performance insights
- Recommended actions

## 🔧 Benefits of Using Prompts

1. **Consistency**: Same analysis framework every time
2. **Context-Aware**: Includes real ServiceNow data
3. **Reusable**: Use the same prompt for different incidents
4. **Customizable**: Parameters allow different analysis types
5. **AI-Optimized**: Formatted for best AI comprehension

## 📊 Prompt Response Format

Each prompt returns a formatted text string containing:

1. **Context Section**: Real data from ServiceNow
2. **Instructions Section**: What the AI should analyze
3. **Tasks Section**: Specific questions to answer
4. **Format Guidelines**: How to structure the response

## 🎯 Best Practices

1. **Use specific incident numbers** for detailed analysis
2. **Apply filters** in summary prompts to focus analysis
3. **Choose appropriate analysis_type** for your needs
4. **Combine multiple prompts** for comprehensive reviews
5. **Schedule regular prompts** for ongoing monitoring

## 🚨 Error Handling

If a prompt fails, it returns an error message:
- "Error: Could not fetch incident..." - Invalid incident number
- "Error searching incidents..." - API connection issue
- "Error generating prompt..." - Server-side error

## 🔄 Prompt + Tool Workflow

Prompts work great with tools:

1. Use **tool** to search/find incidents
2. Use **prompt** to analyze them
3. Use **tool** to update based on analysis

Example:
```
1. search_incidents(state=1) → Find new incidents
2. incident_analysis_prompt(incident_number) → Analyze each
3. update_incident(state=2) → Update to "In Progress"
```

## 📈 Future Enhancements

Potential new prompts:
- `sla_breach_prediction_prompt` - Predict SLA violations
- `capacity_planning_prompt` - Analyze resource needs
- `knowledge_article_prompt` - Generate KB articles from incidents
- `escalation_decision_prompt` - Determine escalation needs