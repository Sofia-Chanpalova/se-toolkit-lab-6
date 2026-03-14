# Task 1: LLM Integration Plan

## LLM Provider
- **Provider**: Qwen Code API (self-hosted on VM)
- **Model**: qwen3-coder-plus
- **API Base**: http://10.93.25.182:42005/v1
- **API Key**: From .env.agent.secret

## Agent Structure
- Read configuration from `.env.agent.secret` (python-dotenv)
- Take question as command-line argument
- Make OpenAI-compatible API call to Qwen
- Parse response and output JSON with required fields
- All debug output to stderr, only final JSON to stdout

## Implementation Plan
1. Load environment variables
2. Validate input
3. Prepare API request
4. Call LLM with timeout (55 seconds)
5. Extract answer from response
6. Output JSON with answer and empty tool_calls
7. Handle errors gracefully