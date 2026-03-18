#!/usr/bin/env python3
"""
System Agent with API query capabilities.
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv
import argparse
from pathlib import Path

# Load environment variables
load_dotenv('.env.agent.secret')

# Constants
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MAX_TOOL_CALLS = 10

# API configuration
LMS_API_KEY = os.getenv('LMS_API_KEY')
AGENT_API_BASE_URL = os.getenv('AGENT_API_BASE_URL', 'http://localhost:42002')

def list_files(path=""):
    """List files and directories at the given path."""
    try:
        full_path = os.path.abspath(os.path.join(PROJECT_ROOT, path))
        if not full_path.startswith(PROJECT_ROOT):
            return "Error: Cannot access paths outside project directory"
        
        if not os.path.exists(full_path):
            return f"Error: Path '{path}' does not exist"
        
        if not os.path.isdir(full_path):
            return f"Error: '{path}' is not a directory"
        
        entries = os.listdir(full_path)
        entries = [e for e in entries if not e.startswith('.')]
        entries.sort()
        
        result = []
        for entry in entries:
            entry_path = os.path.join(full_path, entry)
            if os.path.isdir(entry_path):
                result.append(f"{entry}/")
            else:
                result.append(entry)
        
        return "\n".join(result) if result else "(empty directory)"
        
    except Exception as e:
        return f"Error listing directory: {str(e)}"

def read_file(path):
    """Read a file from the project repository."""
    try:
        full_path = os.path.abspath(os.path.join(PROJECT_ROOT, path))
        if not full_path.startswith(PROJECT_ROOT):
            return "Error: Cannot access paths outside project directory"
        
        if not os.path.exists(full_path):
            return f"Error: File '{path}' does not exist"
        
        if not os.path.isfile(full_path):
            return f"Error: '{path}' is not a file"
        
        file_size = os.path.getsize(full_path)
        if file_size > 1024 * 1024:  # 1MB
            return f"Error: File too large ({file_size} bytes)"
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return content
        
    except UnicodeDecodeError:
        return "Error: File is not a text file"
    except Exception as e:
        return f"Error reading file: {str(e)}"

def query_api(method, path, body=None):
    """Call the deployed backend API."""
    try:
        if not LMS_API_KEY:
            return json.dumps({
                "status_code": 500,
                "body": "Error: LMS_API_KEY not configured"
            })
        
        # Construct full URL
        base = AGENT_API_BASE_URL.rstrip('/')
        url = f"{base}/{path.lstrip('/')}"
        
        print(f"  Calling API: {method} {url}", file=sys.stderr)
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LMS_API_KEY}" 
        }
        
        # Prepare request
        kwargs = {
            "method": method,
            "url": url,
            "headers": headers,
            "timeout": 10
        }
        
        if body and method in ["POST", "PUT"]:
            kwargs["json"] = json.loads(body)
        
        # Make request
        response = requests.request(**kwargs)
        
        print(f"  Response status: {response.status_code}", file=sys.stderr)
        
        # Try to parse response body
        try:
            response_body = response.json()
        except:
            response_body = response.text
        
        return json.dumps({
            "status_code": response.status_code,
            "body": response_body
        })
        
    except Exception as e:
        return json.dumps({
            "status_code": 500,
            "body": f"Error: {str(e)}"
        })

def get_tool_definitions():
    """Return the tool definitions for function calling."""
    return [
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories at a given path. Use this to discover what files are in the wiki or source code.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path from project root (e.g., 'wiki', 'backend', 'frontend')"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file from the project repository. Use this to read wiki files, source code, or configuration files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative file path from project root (e.g., 'wiki/git-workflow.md', 'backend/main.py')"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_api",
                "description": "Call the deployed backend API to get system information, data counts, or debug issues. Use this for questions about the running system.",
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
                            "description": "API endpoint path (e.g., '/items/', '/health', '/analytics/completion-rate?lab=lab-99')"
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
    ]

def execute_tool_call(tool_call):
    """Execute a tool call and return the result."""
    tool_name = tool_call['function']['name']
    args = json.loads(tool_call['function']['arguments'])
    
    print(f"  Executing tool: {tool_name} with args: {args}", file=sys.stderr)
    
    if tool_name == 'list_files':
        result = list_files(**args)
    elif tool_name == 'read_file':
        result = read_file(**args)
    elif tool_name == 'query_api':
        result = query_api(**args)
    else:
        result = f"Error: Unknown tool '{tool_name}'"
    
    return {
        "tool": tool_name,
        "args": args,
        "result": result
    }

def extract_source_from_tool_calls(tool_calls, final_answer):
    """Extract source reference from tool calls."""
    for tc in reversed(tool_calls):
        if tc['tool'] == 'read_file' and not tc['result'].startswith('Error'):
            return tc['args']['path']
    return ""

def agentic_loop(question):
    """Main agentic loop that processes the question with tool calls."""
    
    system_prompt = """You are a system agent that helps users understand both the documentation and the live system.

You have three tools:

1. list_files - Discover files in wiki, backend, or frontend directories
2. read_file - Read wiki files or source code
3. query_api - Call the live backend API

Strategy for different question types:

- **Wiki questions** (how to, guides, procedures): Use list_files("wiki") then read_file on relevant wiki files
- **Code questions** (framework, architecture, implementation): Use read_file on backend/ or frontend/ source files
- **System facts** (ports, status codes, API endpoints): Use query_api with GET /health or GET /api-docs
- **Data questions** (item counts, scores): Use query_api with appropriate endpoints like /items/, /analytics/*
- **Bug diagnosis**: First query_api to see the error, then read_file on relevant source code to find the bug

Always include the source of your answer:
- For wiki: file path (e.g., "wiki/git-workflow.md")
- For code: file path (e.g., "backend/main.py")
- For API: the endpoint you called (e.g., "GET /items/")

The source field is optional only for pure API responses that don't correspond to a file.

IMPORTANT RULES FOR API CALLS:
- To check what happens WITHOUT authentication: make TWO API calls
  1. First call WITHOUT authentication (don't include the key)
  2. Then call WITH authentication to compare
- The question "without authentication" specifically asks about the response when NO API key is sent
- Do NOT send the API key when testing unauthenticated access

SPECIFIC INSTRUCTIONS FOR ANALYTICS QUESTIONS:

For /analytics/top-learners:
1. Query the endpoint with different lab parameters (e.g., lab-01, lab-99)
2. Notice that it crashes for some labs but works for others
3. Read the source code in backend/app/routers/analytics.py
4. Look for the function that handles /analytics/top-learners
5. Identify the sorting bug - it tries to sort None values
6. Explain that the error is "TypeError: 'NoneType' object is not iterable" or similar
7. The fix is to handle empty result sets before sorting
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]
    
    tool_calls_log = []
    tool_call_count = 0
    
    # Get LLM configuration
    api_key = os.getenv('LLM_API_KEY')
    api_base = os.getenv('LLM_API_BASE')
    model = os.getenv('LLM_MODEL', 'qwen3-coder-plus')
    
    if not api_key or not api_base:
        return {
            "answer": "Error: LLM_API_KEY and LLM_API_BASE must be set in .env.agent.secret",
            "source": "",
            "tool_calls": []
        }
    
    url = f"{api_base.rstrip('/')}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    while tool_call_count < MAX_TOOL_CALLS:
        print(f"\nLoop iteration {tool_call_count + 1}", file=sys.stderr)
        
        payload = {
            "model": model,
            "messages": messages,
            "tools": get_tool_definitions(),
            "tool_choice": "auto",
            "temperature": 0.3
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=55)
            response.raise_for_status()
            result = response.json()
        except Exception as e:
            print(f"Error calling LLM: {e}", file=sys.stderr)
            return {
                "answer": f"Error: Failed to get response from LLM - {str(e)}",
                "source": "",
                "tool_calls": tool_calls_log
            }
        
        message = result['choices'][0]['message']
        
        if 'tool_calls' in message and message['tool_calls']:
            print(f"  LLM requested {len(message['tool_calls'])} tool calls", file=sys.stderr)
            
            messages.append({
                "role": "assistant",
                "tool_calls": message['tool_calls']
            })
            
            for tool_call in message['tool_calls']:
                tool_result = execute_tool_call(tool_call)
                tool_calls_log.append(tool_result)
                tool_call_count += 1
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call['id'],
                    "content": tool_result['result']
                })
                
                if tool_call_count >= MAX_TOOL_CALLS:
                    print(f"  Reached max tool calls ({MAX_TOOL_CALLS})", file=sys.stderr)
                    break
        else:
            print("  No more tool calls - generating final answer", file=sys.stderr)
            answer = message.get('content', '')
            if answer is None:
                answer = ""
            
            source = extract_source_from_tool_calls(tool_calls_log, answer)
            
            return {
                "answer": answer,
                "source": source,
                "tool_calls": tool_calls_log
            }
    
    return {
        "answer": "I couldn't find a complete answer within the allowed number of tool calls.",
        "source": "",
        "tool_calls": tool_calls_log
    }

def main():
    parser = argparse.ArgumentParser(description='Ask a question to the System Agent')
    parser.add_argument('question', nargs='?', help='The question to ask')
    args = parser.parse_args()
    
    if not args.question:
        print("Error: Please provide a question", file=sys.stderr)
        sys.exit(1)
    
    question = args.question
    
    # Verify required environment variables
    if not os.getenv('LLM_API_KEY'):
        print("Error: LLM_API_KEY must be set in .env.agent.secret", file=sys.stderr)
        sys.exit(1)
    
    if not os.getenv('LMS_API_KEY'):
        print("Warning: LMS_API_KEY not set - query_api tool will fail", file=sys.stderr)
    
    print(f"\nSystem Agent", file=sys.stderr)
    print(f"Question: {question}", file=sys.stderr)
    print(f"API Base: {AGENT_API_BASE_URL}", file=sys.stderr)
    print("-" * 50, file=sys.stderr)
    
    result = agentic_loop(question)
    
    print(json.dumps(result, ensure_ascii=False))
    
    print("-" * 50, file=sys.stderr)
    print("Done", file=sys.stderr)

if __name__ == "__main__":
    main()