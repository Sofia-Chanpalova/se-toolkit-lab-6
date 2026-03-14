# CLI Agent for LLM Integration

## Overview
This agent (`agent.py`) is a simple CLI tool that connects to an LLM and returns structured JSON answers. It serves as the foundation for more complex agents with tools and agentic loops.

## LLM Provider
- **Provider**: Qwen Code API (self-hosted)
- **Model**: `qwen3-coder-plus`
- **API Endpoint**: Self-hosted on VM at `http://10.93.25.182:42005/v1`
- **Authentication**: API key from `.env.agent.secret`

## Setup

### 1. Install dependencies
```bash
pip install python-dotenv requests