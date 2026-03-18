# Task 3: System Agent Plan

## Overview
Add query_api tool to allow agent to interact with the deployed backend. The agent will answer:
- Static system facts (framework, ports, status codes)
- Data-dependent queries (item count, scores)
- Bug diagnosis by combining API calls with code reading

## Tool Schema: query_api

{
    "type": "function",
    "function": {
        "name": "query_api",
        "description": "Call the deployed backend API to get system information or data",
        "parameters": {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE"],
                    "description": "HTTP method for the request"
                },
                "path": {
                    "type": "string",
                    "description": "API endpoint path (e.g., '/items/', '/analytics/completion-rate?lab=lab-99')"
                },
                "body": {
                    "type": "string",
                    "description": "Optional JSON request body for POST/PUT requests"
                }
            },
            "required": ["method", "path"]
        }
    }
}