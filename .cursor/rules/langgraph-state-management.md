---
description: LangGraph State Management
globs: *.py
alwaysApply: false
---
# LangGraph State Management

## State Design Principles

1. **Separation of Concerns**: Divide state into input, internal, and output components.
2. **Immutability**: Treat state as immutable by returning new state objects rather than modifying existing ones.
3. **Type Safety**: Use Pydantic models for all state definitions.
4. **Clear Ownership**: Each node should own specific parts of the state.

- Use Pydantic models for structured state management
- Define clear state interfaces between nodes
- Extend `MessagesState` for conversation-based agents

```python
class GraphState(BaseModel):
    """Type definition for the graph state."""

    field1: str
    field2: list
    field3: bool
```

For conversation-based agents, extend `MessagesState`:

```python
from langgraph.graph.message import MessagesState

class AgentState(MessagesState):
    """State for the agent with message history."""
    pass
```
