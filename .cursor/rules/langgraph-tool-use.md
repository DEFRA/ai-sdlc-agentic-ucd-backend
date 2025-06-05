---
description: *.py
globs:
alwaysApply: false
---
# LangGraph Tool Use and ReAct Pattern

## Core Principles

1. **Tool Definition**: Define tools using LangChain's `@tool` decorator
2. **Type Safety**: Use Pydantic models for tool inputs and outputs
3. **ReAct Integration**: Use LangGraph's prebuilt ReAct agent for tool orchestration
4. **State Management**: Maintain consistent state handling across tool executions
5. **Error Handling**: Implement robust error handling for tool failures

## Tool Implementation

### Tool Definition
```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field

class WeatherInput(BaseModel):
    """Input schema for weather tool."""
    city: str = Field(..., description="The city to get weather for")

@tool
def get_weather(city: str) -> str:
    """
    Get the weather for a given city.

    Args:
        city: Name of the city to get weather for

    Returns:
        Current weather conditions for the city
    """
    return f"The weather in {city} is sunny."
```

### Tool Collections
```python
# Group related tools into collections
weather_tools = [get_weather]
database_tools = [query_db, update_db]
file_tools = [read_file, write_file]

# Create combined tool sets as needed
all_tools = [*weather_tools, *database_tools, *file_tools]
```

## ReAct Agent Setup

### Model Configuration
```python
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

# Create the system message
system_message = """You are a helpful AI assistant that can use tools.
When a task requires external information or actions, use the appropriate tool.
Always think step by step about which tool to use."""

# Initialize the model with system message
model = ChatAnthropic(
    model="claude-3-5-haiku-20241022",
    temperature=0
).bind(system_message=system_message)

# Create the agent with tools bound to the model
model_with_tools = model.bind_tools(tools)
agent = create_react_agent(model_with_tools, tools)
```

## Node Implementation

### Tool-Using Node
```python
async def tool_node(state: GraphState) -> GraphState:
    """
    Node that uses tools via a ReAct agent.

    Args:
        state: The current state of the workflow

    Returns:
        Updated state with tool execution results
    """
    # Create the message for the agent
    message = HumanMessage(content=state.current_task)

    # Use the agent to execute tools
    response = await agent.ainvoke({"messages": [message]})

    # Extract the final response
    final_message = next(
        (msg for msg in reversed(response["messages"]) if isinstance(msg, AIMessage)),
        None,
    )

    if not final_message:
        return state.model_copy(update={"error": "No response from agent"})

    # Update state with results
    return state.model_copy(update={
        "tool_results": response.get("tool_results", []),
        "response": final_message.content,
        "status": ExecutionStatus.COMPLETED
    })
```

## Error Handling

### Tool Error Management
```python
@tool
def safe_tool_execution(func: Callable, *args, **kwargs) -> Dict[str, Any]:
    """Wrapper for safe tool execution with error handling."""
    try:
        result = func(*args, **kwargs)
        return {
            "success": True,
            "result": result,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "result": None,
            "error": str(e)
        }
```

## State Management

### Tool State Interface
```python
class ToolState(BaseModel):
    """State interface for tool-using nodes."""
    current_task: str = Field(..., description="Current task to execute")
    tool_results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Results from tool executions"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if tool execution failed"
    )
    status: ExecutionStatus = Field(
        default=ExecutionStatus.PENDING,
        description="Current execution status"
    )
```

## Best Practices

1. **Tool Granularity**
   - Keep tools focused on single responsibilities
   - Use clear, descriptive names and documentation
   - Implement input validation using Pydantic models

2. **ReAct Pattern Usage**
   - Use the ReAct pattern for complex tool orchestration
   - Provide clear system messages for agent behavior
   - Implement proper error handling and recovery

3. **State Management**
   - Use immutable state updates with `model_copy`
   - Include all necessary state fields in updates
   - Maintain type safety throughout tool execution

4. **Logging and Monitoring**
   - Log tool executions and results
   - Track tool usage metrics
   - Monitor for tool failures and performance issues
