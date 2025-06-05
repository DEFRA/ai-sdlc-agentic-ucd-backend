---
description: LangGraph async programming patterns
globs: *.py
alwaysApply: false
---
# Async Patterns in LangGraph

## Core Principles
1. **Async by Default**: Make all graph nodes async functions to enable concurrent execution.
2. **Proper Awaiting**: Always await async operations and never block the event loop.
3. **Concurrent Execution**: Use asyncio primitives to run operations concurrently when possible.
4. **Resource Management**: Properly manage async resources like connection pools.
5. **Error Handling**: Implement proper error handling for async operations.

## Async Node Implementation
```python
import asyncio
from typing import Dict, Any, List

async def async_node(state: AppState) -> AppState:
    """Basic async node example."""
    # Perform an async operation
    await asyncio.sleep(0.1)  # Simulate an I/O operation
    return state

async def concurrent_operations_node(state: AppState) -> AppState:
    """Node that performs multiple operations concurrently."""
    # Define async operations
    async def operation1():
        await asyncio.sleep(0.2)
        return "Result 1"

    # Run operations concurrently
    results = await asyncio.gather(
        operation1(),
        operation2(),
        operation3()
    )

    # Update state with results
    return state.model_copy(update={"concurrent_results": results})
```

## Parallel Model Calls
```python
async def parallel_reasoning_node(state: AppState) -> AppState:
    """Performs parallel reasoning with an LLM."""
    query = state.input.query
    model_provider = ModelFactory.get_default_provider()

    # Define parallel reasoning tasks
    async def summarize_query():
        messages = [
            ModelMessage(role="system", content="Summarize user queries concisely."),
            ModelMessage(role="user", content=f"Summarize this query: {query}")
        ]
        response = await model_provider.chat(messages)
        return response.content

    # Run reasoning tasks concurrently
    summary, entities, category = await asyncio.gather(
        summarize_query(),
        identify_entities(),
        categorize_query()
    )

    # Update state with reasoning results
    return state.model_copy(update={
        "planning": PlanningState(
            objective=summary,
            plan=[f"Process {query} as a {category} query"],
            is_complete=True
        ),
        "entities": entities
    })
```

## Error Handling
```python
async def safe_async_node(state: AppState) -> AppState:
    """Node with proper async error handling."""
    try:
        result = await risky_async_operation(state.input.query)
        return state.model_copy(update={"result": result})
    except Exception as e:
        logging.error(f"Error in async operation: {e}")
        return state.model_copy(update={
            "error": str(e),
            "error_type": type(e).__name__
        })

async def retry_async_operation(operation, max_retries=3, delay=0.5):
    """Retry an async operation with exponential backoff."""
    retries = 0
    last_exception = None

    while retries <= max_retries:
        try:
            return await operation()
        except Exception as e:
            last_exception = e
            retries += 1

            if retries <= max_retries:
                await asyncio.sleep(delay * (2 ** (retries - 1)))
            else:
                break

    raise last_exception
```

## Async Graph Execution
```python
async def run_graph_async(graph: StateGraph, query: str, parameters=None) -> AppState:
    """Run a graph asynchronously."""
    initial_state = AppState(
        input=UserInput(query=query, parameters=parameters or {})
    )
    return await graph.ainvoke(initial_state)

async def execute_with_timeout(graph: StateGraph, state: AppState, timeout=30.0) -> AppState:
    """Execute a graph with a timeout."""
    try:
        return await asyncio.wait_for(graph.ainvoke(state), timeout=timeout)
    except asyncio.TimeoutError:
        return state.model_copy(update={
            "error": "Execution timed out",
            "error_type": "TimeoutError"
        })

async def process_multiple_queries(graph: StateGraph, queries: List[str]) -> List[AppState]:
    """Process multiple queries concurrently."""
    tasks = [graph.ainvoke(AppState(input=UserInput(query=query))) for query in queries]
    return await asyncio.gather(*tasks)
```

## Streaming and Monitoring
```python
async def stream_graph_execution(graph: StateGraph, query: str) -> AsyncGenerator[AppState, None]:
    """Stream graph execution, yielding states after each node."""
    initial_state = AppState(input=UserInput(query=query))
    streaming_graph = graph.astream()

    async for state in streaming_graph.astream(initial_state):
        yield state

async def monitor_execution_progress(graph: StateGraph, query: str, progress_callback) -> AppState:
    """Execute a graph with progress monitoring."""
    initial_state = AppState(input=UserInput(query=query))
    streaming_graph = graph.astream()

    visited_nodes = set()
    total_nodes = len(graph.nodes)

    final_state = None
    async for state in streaming_graph.astream(initial_state):
        if hasattr(state, 'current_node'):
            visited_nodes.add(state.current_node)
            progress = len(visited_nodes) / total_nodes
            await progress_callback(progress, state)

        final_state = state

    return final_state
```
