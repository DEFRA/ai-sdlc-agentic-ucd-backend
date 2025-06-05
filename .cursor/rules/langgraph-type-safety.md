---
description: Type Safety in LangGraph
globs: *.py
alwaysApply: false
---
# Type Safety in LangGraph

## Type Safety Principles

1. **Use Pydantic Models**: Define all states, inputs, and outputs as Pydantic models.
2. **Type Annotations**: Use Python's type annotations for all functions and variables.
3. **Validation**: Leverage Pydantic's validation to catch errors early.
4. **Clear Documentation**: Include descriptive field descriptions in all models.

## Pydantic Models for Type Safety

```python
from pydantic import BaseModel, Field, validator, root_validator
from typing import List, Dict, Optional, Any, Union, Literal
from datetime import datetime
from uuid import UUID, uuid4

# Base models with common functionality
class BaseState(BaseModel):
    """Base class for all state models."""
    id: UUID = Field(default_factory=uuid4, description="Unique identifier for this state")
    created_at: datetime = Field(default_factory=datetime.now, description="When this state was created")

    class Config:
        validate_assignment = True  # Validate when attributes are assigned
        extra = "forbid"  # Forbid extra attributes not defined in the model

# Complex nested models
class Document(BaseModel):
    """Represents a document retrieved from a knowledge base."""
    id: str = Field(..., description="Unique identifier for the document")
    content: str = Field(..., description="Text content of the document")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    score: float = Field(default=0.0, description="Relevance score")

    @validator('score')
    def validate_score(cls, v):
        """Ensure score is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Score must be between 0 and 1")
        return v

class ToolCall(BaseModel):
    """Represents a tool call."""
    tool_name: str = Field(..., description="Name of the tool to call")
    tool_args: Dict[str, Any] = Field(..., description="Arguments for the tool")
    call_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique ID for this call")

    @root_validator
    def validate_tool_call(cls, values):
        """Ensure the tool call is valid."""
        tool_name = values.get("tool_name")
        tool_args = values.get("tool_args")

        # Example validation - this would be more complex in practice
        if tool_name == "search" and "query" not in tool_args:
            raise ValueError("Search tool requires a 'query' argument")

        return values

class ToolResult(BaseModel):
    """Represents the result of a tool call."""
    call_id: str = Field(..., description="ID of the original tool call")
    success: bool = Field(..., description="Whether the tool call succeeded")
    result: Any = Field(..., description="Result of the tool call")
    error: Optional[str] = Field(default=None, description="Error message if the call failed")

# Union types for more complex states
class MessageContent(BaseModel):
    """Represents different types of message content."""
    type: Literal["text", "image", "file"] = Field(..., description="Type of content")
    content: Union[str, bytes, Dict[str, Any]] = Field(..., description="Content data")

    @validator('content')
    def validate_content_type(cls, v, values):
        """Ensure content matches the specified type."""
        content_type = values.get('type')
        if content_type == "text" and not isinstance(v, str):
            raise ValueError("Text content must be a string")
        elif content_type == "image" and not isinstance(v, (bytes, str)):
            raise ValueError("Image content must be bytes or a URL string")
        return v

# Enums for better type safety
from enum import Enum, auto

class NodeType(str, Enum):
    """Types of nodes in the graph."""
    REASONING = "reasoning"
    RETRIEVAL = "retrieval"
    TOOL_CALLING = "tool_calling"
    RESPONSE = "response"

class ExecutionStatus(str, Enum):
    """Possible status values for execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
```

## Type-Safe Functions in Nodes

```python
from typing import Tuple, Callable, TypeVar, Generic, cast

# Type variables for generic functions
T = TypeVar('T')
S = TypeVar('S')

# Type-safe node functions
async def retrieve_documents(query: str, top_k: int = 3) -> List[Document]:
    """
    Retrieve documents based on a query.

    Args:
        query: The search query
        top_k: Number of documents to retrieve

    Returns:
        List of retrieved documents
    """
    # Implementation would use a vector store in practice
    docs = [
        Document(
            id=f"doc{i}",
            content=f"Content for document {i}",
            metadata={"source": f"source{i}"},
            score=0.9 - (i * 0.1)
        )
        for i in range(top_k)
    ]
    return docs

# Generic state update function
def update_state_field(state: T, field: str, value: Any) -> T:
    """
    Update a field in a Pydantic model state.

    Args:
        state: The state to update
        field: The field name to update
        value: The new value

    Returns:
        Updated state
    """
    # Using model_copy (previously known as copy) is the preferred
    # way to create an immutable update in Pydantic v2
    return state.model_copy(update={field: value})

# Type-safe node function with proper typing
async def process_rag_node(state: "RAGState") -> "RAGState":
    """
    Process RAG node with type safety.

    Args:
        state: The current RAG state

    Returns:
        Updated RAG state
    """
    # Retrieve documents
    docs = await retrieve_documents(state.query, top_k=5)

    # Process documents to create context
    context = "\n\n".join([f"Document {i+1}: {doc.content}" for i, doc in enumerate(docs)])

    # Return updated state
    return update_state_field(
        update_state_field(state, "retrieved_documents", [doc.model_dump() for doc in docs]),
        "processed_context",
        context
    )
```

## Type-Safe Graph Construction

```python
from langgraph.graph import StateGraph
from typing import Annotated, Literal, get_type_hints

# Define a typed state for the graph
class GraphState(BaseModel):
    """State for the graph execution."""
    query: str = Field(..., description="User query")
    documents: List[Document] = Field(default_factory=list, description="Retrieved documents")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="Tool calls to make")
    tool_results: List[ToolResult] = Field(default_factory=list, description="Results of tool calls")
    response: Optional[str] = Field(default=None, description="Response to user")
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING, description="Current status")

# Type-safe conditional router
def route_after_retrieval(state: GraphState) -> Literal["tool_calling", "response"]:
    """
    Route to the next node after retrieval.

    Args:
        state: The current graph state

    Returns:
        Name of the next node
    """
    # If we need to make tool calls, go to tool_calling
    if "tool" in state.query.lower():
        return "tool_calling"
    # Otherwise, go directly to response
    return "response"

# Type-safe graph construction
def create_typed_graph() -> StateGraph:
    """
    Create a graph with proper typing.

    Returns:
        A compiled state graph
    """
    # Create the graph
    graph = StateGraph(GraphState)

    # Add nodes
    graph.add_node("retrieval", process_rag_node)
    graph.add_node("tool_calling", process_tool_calling)
    graph.add_node("response", generate_response)

    # Add edges
    graph.add_conditional_edges(
        "retrieval",
        route_after_retrieval
    )
    graph.add_edge("tool_calling", "response")

    # Set entry point
    graph.set_entry_point("retrieval")

    # Compile
    return graph.compile()

# Type-safe execution
async def execute_graph(query: str) -> GraphState:
    """
    Execute the graph with a user query.

    Args:
        query: The user's query

    Returns:
        Final graph state
    """
    # Create the graph
    graph = create_typed_graph()

    # Create initial state
    initial_state = GraphState(query=query)

    # Execute the graph
    final_state = await graph.ainvoke(initial_state)

    return final_state
```

## Type-Safe Config and Settings

```python
from pydantic_settings import BaseSettings
from typing import Union, List, Optional

class ModelConfig(BaseModel):
    """Configuration for a language model."""
    provider: Literal["anthropic", "ollama"] = Field(..., description="Model provider")
    model_name: str = Field(..., description="Name of the model")
    api_key: Optional[str] = Field(default=None, description="API key (if needed)")
    base_url: Optional[str] = Field(default=None, description="Base URL (if needed)")
    temperature: float = Field(default=0.7, description="Temperature for generation")
    max_tokens: int = Field(default=1000, description="Maximum tokens to generate")

    @validator('temperature')
    def validate_temperature(cls, v):
        """Ensure temperature is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Temperature must be between 0 and 1")
        return v

class DatabaseConfig(BaseModel):
    """Configuration for the database."""
    host: str = Field(..., description="Database host")
    port: int = Field(..., description="Database port")
    username: str = Field(..., description="Database username")
    password: str = Field(..., description="Database password")
    database: str = Field(..., description="Database name")

    @property
    def connection_string(self) -> str:
        """Get the database connection string."""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

class AppConfig(BaseSettings):
    """Application configuration."""
    app_name: str = Field("LangGraph App", description="Name of the application")
    debug: bool = Field(False, description="Whether to enable debug mode")
    model: ModelConfig = Field(..., description="Model configuration")
    database: DatabaseConfig = Field(..., description="Database configuration")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field("INFO", description="Log level")

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"
```
