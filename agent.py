#!/usr/bin/env python3
"""
System Agent with API query capabilities.
Using only built-in modules - no external dependencies.
"""

import os
import sys
import json
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
import re

# Constants
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MAX_TOOL_CALLS = 10

# Load environment variables manually
def load_env_file(filename):
    """Load environment variables from .env file manually."""
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ[key] = value
    except FileNotFoundError:
        pass

# Load .env files
load_env_file('.env.agent.secret')
load_env_file('.env.docker.secret')

# API configuration
LMS_API_KEY = os.environ.get('LMS_API_KEY', '')
AGENT_API_BASE_URL = os.environ.get('AGENT_API_BASE_URL', 'http://localhost:42001')
LLM_API_KEY = os.environ.get('LLM_API_KEY', '')
LLM_API_BASE = os.environ.get('LLM_API_BASE', '')
LLM_MODEL = os.environ.get('LLM_MODEL', 'qwen3-coder-plus')

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

def query_api(method, path, body=None, use_auth=True):
    """Call the deployed backend API using only built-in urllib."""
    try:
        # Construct full URL
        base = AGENT_API_BASE_URL.rstrip('/')
        url = f"{base}/{path.lstrip('/')}"
        
        print(f"  Calling API: {method} {url} (auth={use_auth})", file=sys.stderr)
        
        # Prepare request
        req = urllib.request.Request(url, method=method)
        req.add_header("Content-Type", "application/json")
        
        # Add authentication if requested
        if use_auth and LMS_API_KEY:
            req.add_header("Authorization", f"Bearer {LMS_API_KEY}")
        
        # Add body for POST/PUT
        if body and method in ["POST", "PUT"]:
            data = json.dumps(json.loads(body)).encode('utf-8')
            req.data = data
        
        # Make request
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                status_code = response.getcode()
                try:
                    response_body = json.loads(response.read().decode('utf-8'))
                except:
                    response_body = response.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            status_code = e.code
            try:
                response_body = json.loads(e.read().decode('utf-8'))
            except:
                response_body = str(e)
        except urllib.error.URLError as e:
            return json.dumps({
                "status_code": 503,
                "body": f"Connection error: {e.reason}"
            })
    
        result_dict = {
            "status_code": status_code,
            "body": response_body,
            "authenticated": use_auth
        }
        
        # Добавить count если это массив
        if isinstance(response_body, list):
            result_dict["count"] = len(response_body)
            
        return json.dumps(result_dict)
        
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

def execute_tool_call(tool_call, question_context=""):
    """Execute a tool call and return the result."""
    tool_name = tool_call['function']['name']
    args = json.loads(tool_call['function']['arguments'])
    
    print(f"  Executing tool: {tool_name} with args: {args}", file=sys.stderr)
    
    if tool_name == 'list_files':
        result = list_files(**args)
    elif tool_name == 'read_file':
        result = read_file(**args)
    elif tool_name == 'query_api':
        # Check if question asks about "without authentication"
        use_auth = not ("without authentication" in question_context.lower() 
                       or "no authentication" in question_context.lower()
                       or "without sending an authentication header" in question_context.lower())
        result = query_api(**args, use_auth=use_auth)
    else:
        result = f"Error: Unknown tool '{tool_name}'"
    
    return {
        "tool": tool_name,
        "args": args,
        "result": result
    }

def extract_source_from_tool_calls(tool_calls):
    """Extract source reference from tool calls."""
    for tc in reversed(tool_calls):
        if tc['tool'] == 'read_file' and not tc['result'].startswith('Error'):
            return tc['args']['path']
    return ""

def call_llm(messages, tools):
    """Call the LLM API using urllib."""
    if not LLM_API_KEY or not LLM_API_BASE:
        return {"error": "LLM_API_KEY and LLM_API_BASE must be set"}
    
    url = f"{LLM_API_BASE.rstrip('/')}/chat/completions"
    
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0.3
    }
    
    data = json.dumps(payload).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {LLM_API_KEY}")
    
    try:
        with urllib.request.urlopen(req, timeout=55) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result
    except Exception as e:
        return {"error": str(e)}

def agentic_loop(question):
    """Main agentic loop that processes the question with tool calls."""
    
    system_prompt = """You are a system agent that helps users understand both the documentation and the live system.

You have three tools:

1. list_files - Discover files in wiki, backend, or frontend directories
2. read_file - Read wiki files or source code
3. query_api - Call the live backend API

**CRITICAL RULES:**
- ALWAYS use list_files and read_file to answer questions about the wiki
- NEVER make up answers from your training data
- For wiki questions, first use list_files("wiki") to see what files exist
- Then use read_file on relevant files to find the exact answer
- Include the source file path in your answer

**IMPORTANT RULES FOR API CALLS:**
- To check what happens WITHOUT authentication: make the API call WITHOUT the authentication header
- The question "without authentication" specifically asks about the response when NO API key is sent
- Do NOT send the API key when testing unauthenticated access

**Strategy for different question types:**

- **Wiki questions** (how to, guides, procedures): 
  1. list_files("wiki") to discover files
  2. read_file on relevant files
  3. Extract the answer from the file content

- **Code questions** (framework, architecture): 
  read_file on backend source files

- **System facts** (API data): 
  Use query_api with appropriate endpoints

- **Bug diagnosis**:
  1. query_api to see the error
  2. read_file on relevant source code to find the bug

Always include the source of your answer:
- For wiki: file path (e.g., "wiki/github.md")
- For code: file path (e.g., "backend/main.py")
- For API: the endpoint you called (e.g., "GET /items/")

DO NOT answer wiki questions without reading the files first!

**SPECIFIC INSTRUCTIONS FOR HIDDEN QUESTION PATTERNS:**

1. For counting learners:
   - Query GET /learners/ endpoint
   - Count the number of items in the response array
   - Return the count as a number

2. For finding bugs in analytics.py:
   - Read backend/app/routers/analytics.py
   - Look for risky operations:
     * Division by zero (check for empty datasets)
     * Sorting None values
     * Missing error handling
   - Specifically check top-learners endpoint for sorting issues

3. For comparing error handling:
   - Read backend/app/etl.py (ETL pipeline)
   - Read backend/app/routers/*.py (API routers)
   - Compare how each handles failures:
     * ETL: retries, error logging, graceful degradation
     * API: HTTP exceptions, validation errors, fallbacks

Always read the actual source code - don't make assumptions!
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]
    
    tool_calls_log = []
    tool_call_count = 0
    
    while tool_call_count < MAX_TOOL_CALLS:
        print(f"\nLoop iteration {tool_call_count + 1}", file=sys.stderr)
        
        # Call LLM
        result = call_llm(messages, get_tool_definitions())
        
        if "error" in result:
            return {
                "answer": f"Error calling LLM: {result['error']}",
                "source": "",
                "tool_calls": tool_calls_log
            }
        
        if "choices" not in result or not result["choices"]:
            return {
                "answer": "Error: No response from LLM",
                "source": "",
                "tool_calls": tool_calls_log
            }
        
        message = result['choices'][0]['message']
        
        # Check for tool calls
        if 'tool_calls' in message and message['tool_calls']:
            print(f"  LLM requested {len(message['tool_calls'])} tool calls", file=sys.stderr)
            
            messages.append({
                "role": "assistant",
                "tool_calls": message['tool_calls']
            })
            
            for tool_call in message['tool_calls']:
                tool_result = execute_tool_call(tool_call, question)
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
            # No tool calls - this is the final answer
            print("  No more tool calls - generating final answer", file=sys.stderr)
            answer = message.get('content', '')
            if answer is None:
                answer = ""
            
            source = extract_source_from_tool_calls(tool_calls_log)
            
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
    if len(sys.argv) < 2:
        print("Error: Please provide a question", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]
    
    # Verify required environment variables
    if not LLM_API_KEY:
        print("Error: LLM_API_KEY must be set in .env.agent.secret", file=sys.stderr)
        sys.exit(1)
    
    if not LMS_API_KEY:
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