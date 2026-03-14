#!/usr/bin/env python3
"""
Regression test for agent.py
"""

import subprocess
import json
import sys
import os

def test_agent_basic():
    """Test that agent.py returns valid JSON with answer and tool_calls"""
    
    # Run agent with a simple question
    result = subprocess.run(
        [sys.executable, "agent.py", "What is 2+2?"],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    # Check exit code
    assert result.returncode == 0, f"Agent failed with exit code {result.returncode}"
    
    # Parse stdout
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"Stdout: {result.stdout}", file=sys.stderr)
        print(f"Stderr: {result.stderr}", file=sys.stderr)
        assert False, f"Invalid JSON output: {e}"
    
    # Check required fields
    assert "answer" in output, "Missing 'answer' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be a list"
    assert len(output["tool_calls"]) == 0, "'tool_calls' should be empty for Task 1"
    
    # Check that answer is not empty
    assert output["answer"], "'answer' should not be empty"
    
    print("Test passed!")
    return True

if __name__ == "__main__":
    test_agent_basic()