#!/usr/bin/env python3
"""
Simple CLI agent that calls an LLM and returns a JSON response.
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv
import argparse

# Load environment variables
load_dotenv('.env.agent.secret')

def main():
    # Parse command line argument
    parser = argparse.ArgumentParser(description='Ask a question to the LLM')
    parser.add_argument('question', nargs='?', help='The question to ask')
    args = parser.parse_args()
    
    # Check if question is provided
    if not args.question:
        print("Error: Please provide a question", file=sys.stderr)
        sys.exit(1)
    
    question = args.question
    
    # Get LLM configuration
    api_key = os.getenv('LLM_API_KEY')
    api_base = os.getenv('LLM_API_BASE')
    model = os.getenv('LLM_MODEL', 'qwen3-coder-plus')
    
    if not api_key or not api_base:
        print("Error: LLM_API_KEY and LLM_API_BASE must be set in .env.agent.secret", file=sys.stderr)
        sys.exit(1)
    
    # Prepare API request
    url = f"{api_base.rstrip('/')}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": question}
        ],
        "temperature": 0.7
    }
    
    # Debug info to stderr
    print(f"Calling LLM with question: {question}", file=sys.stderr)
    print(f"Model: {model}", file=sys.stderr)
    print(f"API Base: {api_base}", file=sys.stderr)
    
    try:
        # Make API call with timeout
        response = requests.post(url, headers=headers, json=payload, timeout=55)
        response.raise_for_status()
        
        # Parse response
        result = response.json()
        answer = result['choices'][0]['message']['content']
        
        # Output JSON to stdout
        output = {
            "answer": answer,
            "tool_calls": []
        }
        print(json.dumps(output))
        
    except requests.exceptions.Timeout:
        print("Error: Request timed out after 55 seconds", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error calling LLM API: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Error parsing LLM response: {e}", file=sys.stderr)
        print(f"Raw response: {result if 'result' in locals() else 'N/A'}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()