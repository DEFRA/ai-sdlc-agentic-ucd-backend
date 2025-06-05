---
description: Python Project Overview
globs: *.*
alwaysApply: false
---
# Python Project Overview

## Stack
- Python
- FastAPI
- LangGraph
- LangChain

## Directory Structure
```
src/
├── api/v1/      # Routing and HTTP endpoints
├── services/    # Business logic
├── repositories/# Data access
├── agents/      # LangGraph AI agents
├── utils/       # Utility functions
├── config/      # Configuration
├── database/    # Database operations
└── models/      # Data models
```

## Key Principles
- Security-first approach
- Clean code practices
- Async by default

## Git Commits
- Use conventional commit prefixes (feat:, fix:, etc.)
- Keep messages concise and reference issues

## Security
- No secrets in code
- Validate inputs
- Encrypt sensitive data
