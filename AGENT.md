# System Agent

## Overview
The System Agent is a CLI tool that answers questions about both the project documentation and the live running system. It extends the Documentation Agent from Task 2 with API query capabilities.

## Architecture

### LLM Provider
- **Provider**: Qwen Code API (self-hosted on VM)
- **Model**: `qwen3-coder-plus`
- **API Endpoint**: `http://10.93.25.182:42005/v1`
- **Authentication**: `LLM_API_KEY` from `.env.agent.secret`

### Backend API Connection
- **Base URL**: `AGENT_API_BASE_URL` (default: http://localhost:42002)
- **Authentication**: `LMS_API_KEY` from `.env.docker.secret`
- **Headers**: `X-API-Key: {LMS_API_KEY}`

## Tools

The agent has three tools:

### 1. `list_files`
Lists files and directories in the project.

- **Parameters**: `path` (string) - relative path from project root
- **Examples**: 
  - `list_files(path="wiki")` - discover wiki files
  - `list_files(path="backend")` - explore backend source
  - `list_files(path="")` - list project root

### 2. `read_file`
Reads file contents.

- **Parameters**: `path` (string) - relative file path
- **Examples**:
  - `read_file(path="wiki/git-workflow.md")` - read wiki
  - `read_file(path="backend/main.py")` - read source code
  - `read_file(path="pyproject.toml")` - read config

### 3. `query_api`
Calls the deployed backend API.

- **Parameters**:
  - `method` (string): HTTP method (GET, POST, PUT, DELETE)
  - `path` (string): API endpoint (e.g., "/items/", "/health")
  - `body` (string, optional): JSON request body
- **Examples**:
  - `query_api(method="GET", path="/health")` - check system health
  - `query_api(method="GET", path="/items/")` - get all items
  - `query_api(method="GET", path="/analytics/completion-rate?lab=lab-99")` - get lab stats
- **Returns**: JSON with `status_code` and `body`

## Environment Variables

| Variable | Purpose | Default | Source |
|----------|---------|---------|--------|
| `LLM_API_KEY` | LLM provider authentication | required | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint | required | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `qwen3-coder-plus` | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API authentication | required | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Backend URL | `http://localhost:42002` | optional |

**Important**: The autochecker injects its own values for these variables. Never hardcode them!

## Agentic Loop
User Question

LLM + Tool Definitions

Has tool_calls? ──yes── Execute tools ── Append results
 |
 no
 |
 Back to LLM

Final Answer (source optional)

JSON Output


- Maximum 10 tool calls per question
- 55-second timeout for LLM calls
- 10-second timeout for API calls

## Question Type Strategy

The system prompt guides the LLM to choose appropriate tools:

| Question Type | Strategy | Example Tools |
|--------------|----------|---------------|
| **Wiki/How-to** | `list_files("wiki")` → `read_file` | `read_file(path="wiki/git-workflow.md")` |
| **Code/Architecture** | `list_files("backend")` → `read_file` | `read_file(path="backend/main.py")` |
| **System Facts** | `query_api` to health/status endpoints | `query_api(method="GET", path="/health")` |
| **Data Queries** | `query_api` to data endpoints | `query_api(method="GET", path="/items/")` |
| **Bug Diagnosis** | `query_api` first, then `read_file` on relevant code | Chain: API error → read source |

## Security Features

1. **Path Traversal Prevention**: All file paths validated against `PROJECT_ROOT`
2. **File Size Limit**: 1MB maximum file size
3. **API Key Separation**: LLM and backend keys are separate
4. **Environment Variables**: No hardcoded credentials
5. **Error Handling**: Graceful failure with informative messages


## Lessons Learned

1. **Tool Descriptions Matter**: The LLM needs clear, specific descriptions of when to use each tool. Vague descriptions lead to wrong tool choices.

2. **API Error Handling**: The agent must parse API error responses and use them to guide next steps. A 404 might mean "try a different endpoint", while a 500 might mean "check the code".

3. **Multi-step Chains**: The hardest questions require chaining tools: query API → get error → read relevant code → suggest fix. The system prompt needs explicit strategies for these cases.

4. **Null Content Handling**: LLMs sometimes return `"content": null` when making tool calls. Code must handle this gracefully with `message.get('content', '') or ''`.

5. **Environment Variables**: Never hardcode URLs or keys. The autochecker runs with different values, and hardcoding guarantees failure.

6. **Source Field Flexibility**: For pure API responses, source is optional. For wiki/code answers, it's required. The agent handles both.

## Benchmark Results
- **Local evaluation**: 10/10 questions passed
- **Key improvements made**:
  - Fixed authentication handling for API calls
  - Improved system prompt for analytics questions
  - Added proper error handling for edge cases