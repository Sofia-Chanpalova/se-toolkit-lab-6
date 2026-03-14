# Task 2: Documentation Agent Plan

## Project Structure Analysis
Based on the project structure, we have:
- `wiki/` directory containing documentation files
- Existing `agent.py` from Task 1
- Test infrastructure in `tests/`

## Tool Schemas

### 1. list_files
- **Purpose**: Discover available documentation files
- **Parameters**: `path` (string) - relative path from project root
- **Expected paths**: "wiki", "wiki/subdirectories"
- **Returns**: Newline-separated list of files/directories
- **Security**: Validate path is within PROJECT_ROOT

### 2. read_file
- **Purpose**: Read wiki files to find answers
- **Parameters**: `path` (string) - relative file path from project root
- **Expected files**: `wiki/git-workflow.md`, `wiki/index.md`, etc.
- **Returns**: File contents or error message
- **Security**: Prevent directory traversal, limit file size to 1MB

## Agentic Loop Implementation

```python
# Pseudocode
messages = [system_prompt, user_question]
tool_calls_log = []

while tool_calls_count < 10:
    response = call_llm(messages, tools)
    
    if response.has_tool_calls():
        for tool_call in response.tool_calls:
            result = execute_tool(tool_call)
            tool_calls_log.append({"tool": tool_name, "args": args, "result": result})
            messages.append({"role": "tool", "content": result})
        tool_calls_count += len(response.tool_calls)
    else:
        # Final answer
        return {
            "answer": response.content,
            "source": extract_source(tool_calls_log),
            "tool_calls": tool_calls_log
        }