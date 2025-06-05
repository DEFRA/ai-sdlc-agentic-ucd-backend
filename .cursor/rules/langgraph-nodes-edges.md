---
description: LangGraph Nodes & Edges
globs: *.py
alwaysApply: false
---
# LangGraph Nodes & Edges

## Node Implementation

- Define nodes as functions that take and return state
- Use clear docstrings explaining the node's purpose
- Log node execution and outputs
- Return complete state (including unchanged fields)

```python
def example_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process input and update state.

    Args:
        state: The current graph state

    Returns:
        Updated state
    """
    logger.log_node_start("Node Name")

    # Process input and generate output
    result = process_input(state)

    logger.log_node_output("Node Name", result, "result_field")

    # Return complete updated state
    return {
        "field1": result,
        "field2": state.get("field2", []),
        "field3": state.get("field3", False)
    }
```

## Edge Implementation

- Use LangGraph's prebuilt conditions when possible
- Create wrapper functions for custom logging or behavior if necessary
- Return values should match LangGraph conventions (`"tools"`, `"__end__"`)

### Configuring Conditional Edges

```python
# Add conditional edges
graph.add_conditional_edges(
    "agent",
    tools_condition_with_logging,
    {
        "tools": "tools",  # Route to tools node when tools are called
        "__end__": END,    # End the graph when no tools are called
    },
)
```

### Graph Definition

- Create graphs using the `StateGraph` class
- Always include START and END nodes from LangGraph
- Define nodes, edges, and conditional edges explicitly
- Set a clear entry point
- Use descriptive names for nodes and edge conditions

```python
from langgraph.graph import START, END, StateGraph

def create_graph() -> StateGraph:
    """Create the graph with nodes and edges."""
    # Create the graph with state type
    graph = StateGraph(GraphState)

    # Add nodes
    graph.add_node("node_name", node_function)
    graph.add_node("process_data", process_data_node)

    # Add edges starting from START
    graph.add_edge(START, "node_name")
    graph.add_edge("node_name", "process_data")

    # Add conditional edges that may lead to END
    graph.add_conditional_edges(
        "process_data",
        condition_function,
        {
            "continue": "next_node",
            "__end__": END,  # Use END for terminal states
        },
    )

    # Set entry point (first node after START)
    graph.set_entry_point("node_name")

    return graph
```
