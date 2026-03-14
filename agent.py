#!/usr/bin/env python3
"""
Documentation Agent with tool-calling capabilities.
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

def list_files(path=""):
    """
    List files and directories at the given path.
    
    Args:
        path (str): Relative directory path from project root
        
    Returns:
        str: Newline-separated listing of entries or error message
    """
    try:
        # Security: prevent directory traversal
        full_path = os.path.abspath(os.path.join(PROJECT_ROOT, path))
        if not full_path.startswith(PROJECT_ROOT):
            return "Error: Cannot access paths outside project directory"
        
        if not os.path.exists(full_path):
            return f"Error: Path '{path}' does not exist"
        
        if not os.path.isdir(full_path):
            return f"Error: '{path}' is not a directory"
        
        entries = os.listdir(full_path)
        # Filter out hidden files and sort
        entries = [e for e in entries if not e.startswith('.')]
        entries.sort()
        
        # Add trailing slash to directories
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
    """
    Read a file from the project repository.
    
    Args:
        path (str): Relative file path from project root
        
    Returns:
        str: File contents or error message
    """
    try:
        # Security: prevent directory traversal
        full_path = os.path.abspath(os.path.join(PROJECT_ROOT, path))
        if not full_path.startswith(PROJECT_ROOT):
            return "Error: Cannot access paths outside project directory"
        
        if not os.path.exists(full_path):
            return f"Error: File '{path}' does not exist"
        
        if not os.path.isfile(full_path):
            return f"Error: '{path}' is not a file"
        
        # Check file size (limit to 1MB to avoid huge files)
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

def get_tool_definitions():
    """Return the tool definitions for function calling."""
    return [
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories at a given path. Use this to discover what files are in the wiki.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path from project root (e.g., 'wiki' or '')"
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
                "description": "Read a file from the project repository. Use this to read wiki files and find answers.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative file path from project root (e.g., 'wiki/git-workflow.md')"
                        }
                    },
                    "required": ["path"]
                }
            }
        }
    ]

def execute_tool_call(tool_call):
    """
    Execute a tool call and return the result.
    
    Args:
        tool_call: Tool call object from LLM response
        
    Returns:
        dict: Tool call result with tool, args, and result
    """
    tool_name = tool_call['function']['name']
    args = json.loads(tool_call['function']['arguments'])
    
    print(f"  Executing tool: {tool_name} with args: {args}", file=sys.stderr)
    
    if tool_name == 'list_files':
        result = list_files(**args)
    elif tool_name == 'read_file':
        result = read_file(**args)
    else:
        result = f"Error: Unknown tool '{tool_name}'"
    
    return {
        "tool": tool_name,
        "args": args,
        "result": result
    }

def extract_source_from_tool_calls(tool_calls, final_answer):
    """
    Extract source reference from tool calls.
    Looks for read_file calls that likely contain the answer.
    """
    # Find the last read_file call that was successful
    for tc in reversed(tool_calls):
        if tc['tool'] == 'read_file' and not tc['result'].startswith('Error'):
            file_path = tc['args']['path']
            return file_path
    return "wiki/unknown.md"

def agentic_loop(question):
    """
    Main agentic loop that processes the question with tool calls.
    
    Args:
        question (str): User question
        
    Returns:
        dict: Final output with answer, source, and tool_calls
    """
    messages = [
        {
            "role": "system",
            "content": """You are a documentation agent that helps users find information in the project wiki.
You have access to two tools:
- list_files: Discover what files are in the wiki
- read_file: Read wiki files to find answers

Strategy:
1. First, use list_files with path="wiki" to see what documentation is available
2. Then, use read_file on relevant files to find the answer
3. When you find the answer, respond with it and include the source file path

Important: The source should be the file path where you found the answer."""
        },
        {"role": "user", "content": question}
    ]
    
    tool_calls_log = []
    tool_call_count = 0
    
    # Get LLM configuration
    api_key = os.getenv('LLM_API_KEY')
    api_base = os.getenv('LLM_API_BASE')
    model = os.getenv('LLM_MODEL', 'qwen3-coder-plus')
    
    url = f"{api_base.rstrip('/')}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    while tool_call_count < MAX_TOOL_CALLS:
        print(f"\nLoop iteration {tool_call_count + 1}", file=sys.stderr)
        
        # Prepare request
        payload = {
            "model": model,
            "messages": messages,
            "tools": get_tool_definitions(),
            "tool_choice": "auto",
            "temperature": 0.3
        }
        
        # Make API call
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
        
        # Check for tool calls
        if 'tool_calls' in message and message['tool_calls']:
            print(f"  LLM requested {len(message['tool_calls'])} tool calls", file=sys.stderr)
            
            # Add assistant message with tool calls to history
            messages.append({
                "role": "assistant",
                "tool_calls": message['tool_calls']
            })
            
            # Execute each tool call
            for tool_call in message['tool_calls']:
                tool_result = execute_tool_call(tool_call)
                tool_calls_log.append(tool_result)
                tool_call_count += 1
                
                # Add tool result message
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
            answer = message['content']
            source = extract_source_from_tool_calls(tool_calls_log, answer)
            
            return {
                "answer": answer,
                "source": source,
                "tool_calls": tool_calls_log
            }
    
    # If we hit max tool calls without getting answer
    print(f"  Max tool calls reached ({MAX_TOOL_CALLS})", file=sys.stderr)
    return {
        "answer": "I couldn't find a complete answer within the allowed number of tool calls.",
        "source": "",
        "tool_calls": tool_calls_log
    }

def main():
    # Parse command line argument
    parser = argparse.ArgumentParser(description='Ask a question to the Documentation Agent')
    parser.add_argument('question', nargs='?', help='The question to ask')
    args = parser.parse_args()
    
    # Check if question is provided
    if not args.question:
        print("Error: Please provide a question", file=sys.stderr)
        sys.exit(1)
    
    question = args.question
    
    # Verify LLM configuration
    api_key = os.getenv('LLM_API_KEY')
    api_base = os.getenv('LLM_API_BASE')
    
    if not api_key or not api_base:
        print("Error: LLM_API_KEY and LLM_API_BASE must be set in .env.agent.secret", file=sys.stderr)
        sys.exit(1)
    
    print(f"\nDocumentation Agent", file=sys.stderr)
    print(f"Question: {question}", file=sys.stderr)
    print("-" * 50, file=sys.stderr)
    
    # Run agentic loop
    result = agentic_loop(question)
    
    # Output JSON to stdout
    print(json.dumps(result, ensure_ascii=False))
    
    print("-" * 50, file=sys.stderr)
    print("Done", file=sys.stderr)

if __name__ == "__main__":
    main()