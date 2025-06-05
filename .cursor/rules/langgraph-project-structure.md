---
description: LangGraph Project Structure
globs: *.py
alwaysApply: false
---
# LangGraph Project Structure

## Directory Structure

```python
my_langgraph_app/
├── pyproject.toml
├── .env
├── README.md
├── src/
│   ├── __init__.py
│   ├── main.py              # Main application entry point
│   ├── config.py            # Configuration management
│   ├── api/                 # API endpoints
│   │   ├── __init__.py
│   │   └── v1/              # API v1 routes
│   ├── models/              # Data models
│   │   ├── __init__.py
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   ├── repositories/        # Data access
│   │   ├── __init__.py
│   ├── database/            # Database operations
│   │   ├── __init__.py
│   ├── agents/              # LangGraph AI agents
│   │   ├── __init__.py
│   │   ├── states/          # State definitions
│   │   │   ├── __init__.py
│   │   │   ├── input_state.py   # Input state schemas
│   │   │   ├── internal_state.py # Internal state schemas
│   │   │   └── output_state.py  # Output state schemas
│   │   ├── nodes/           # Graph node definitions
│   │   │   ├── __init__.py
│   │   │   ├── reasoning.py     # Reasoning nodes
│   │   │   ├── tools.py         # Tool calling nodes
│   │   │   └── rag.py           # RAG implementation nodes
│   │   ├── subgraphs/       # Subgraph definitions
│   │   │   ├── __init__.py
│   │   │   ├── planning.py      # Planning subgraph
│   │   │   └── execution.py     # Execution subgraph
│   │   ├── tools/           # Custom tools
│   │   │   ├── __init__.py
│   │   │   └── custom_tools.py  # Custom tool implementations
│   │   └── memory/          # Memory implementations
│   │       ├── __init__.py
│   │       ├── short_term.py    # Checkpoint-based short-term memory
│   │       └── long_term.py     # Long-term memory
│   └── utils/               # Utility functions
│       ├── __init__.py
│       └── helpers.py       # Helper utilities
└── tests/                   # Test directory
    ├── __init__.py
    └── conftest.py          # Test fixtures
```
