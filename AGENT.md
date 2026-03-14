# Documentation Agent

## Overview
The Documentation Agent is a CLI tool that answers questions about the project by reading the wiki documentation. It uses an LLM with tool-calling capabilities to discover and read relevant files.

## Architecture

### LLM Provider
- **Provider**: Qwen Code API (self-hosted on VM)
- **Model**: `qwen3-coder-plus`
- **API Endpoint**: `http://10.93.25.182:42005/v1`
- **Authentication**: API key from `.env.agent.secret`

## Tools

The agent has two tools for interacting with the wiki:

### 1. `list_files`
Lists files and directories in the wiki.

- **Parameters**: `path` (string) - relative path from project root
- **Example**: `list_files(path="wiki")`
- **Returns**: Newline-separated list of files/directories
- **Security**: Cannot list directories outside project root

### 2. `read_file`
Reads the contents of a wiki file.

- **Parameters**: `path` (string) - relative file path from project root
- **Example**: `read_file(path="wiki/git-workflow.md")`
- **Returns**: File contents or error message
- **Security**: 
  - Cannot read files outside project root
  - Limited to 1MB file size
  - Text files only

## Agentic Loop

The agent follows this loop to answer questions:

User Question

LLM + Tool Definitions

Has tool_calls? ──yes── Execute tools ── Append results
 no 
 Back to LLM
Final Answer with source

JSON Output


### Implementation Details

1. **Initial Request**: Send user question + tool definitions to LLM
2. **Tool Execution**: If LLM requests tools, execute them
3. **History**: Append tool results as new messages
4. **Termination**: Stop when LLM returns text (no tool calls)
5. **Safety Limit**: Maximum 10 tool calls per question

## System Prompt

SYSTEM_PROMPT = """You are a documentation agent that helps users find information in the project wiki.
You have access to two tools:
- list_files: Discover what files are in the wiki
- read_file: Read wiki files to find answers

Strategy:
1. First, use list_files with path="wiki" to see what documentation is available
2. Then, use read_file on relevant files to find the answer
3. When you find the answer, respond with it and include the source file path

Important: The source should be the file path where you found the answer."""