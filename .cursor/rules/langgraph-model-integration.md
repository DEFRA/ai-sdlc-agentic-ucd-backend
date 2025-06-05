---
description: Model Integration in LangGraph
globs: *.py
alwaysApply: false
---
# Model Integration in LangGraph

## General Principles

- Always use LangChain interfaces for LLM calls, not native APIs
- Maintain consistent model configuration across the application
- Use structured output parsers for predictable responses

## LLM Integration

### Model Initialization

- Use LangChain's model wrappers instead of direct API calls
- Configure models with consistent parameters
- Store API keys securely using environment variables

```python
# ✅ DO: Use LangChain wrappers
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

# Initialize Claude model
claude_model = ChatAnthropic(
    model="claude-3-5-haiku-20241022",
    anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
    temperature=0,
)

# Initialize OpenAI model
openai_model = ChatOpenAI(
    model="gpt-4o",
    openai_api_key=os.environ.get("OPENAI_API_KEY"),
    temperature=0,
)

# ❌ DON'T: Use native APIs directly
# import anthropic
# client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
# response = client.messages.create(...)
```

### Structured Output

- Use LangChain's output parsers for structured responses
- Define Pydantic models for expected outputs
- Use JSON mode when available for more reliable parsing

```python
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# Define the expected output structure
class MathSolution(BaseModel):
    steps: list[str] = Field(description="Step-by-step solution process")
    answer: str = Field(description="Final answer to the problem")
    confidence: float = Field(description="Confidence score between 0 and 1")

# Create a parser
parser = JsonOutputParser(pydantic_object=MathSolution)

# Bind the parser to the model
structured_model = model.with_structured_output(MathSolution)
```

### Prompt Templates

- Use LangChain's prompt templates for consistent prompting
- Define reusable templates at the module level
- Include clear instructions and examples

```python
from langchain_core.prompts import ChatPromptTemplate

template = """You are a math problem solver.

Problem: {problem}

Solve this step by step and provide your final answer.
"""

prompt = ChatPromptTemplate.from_template(template)

# Chain the prompt and model
chain = prompt | model | parser
```

### Tool Integration

- Use LangChain's Tool class for defining tools
- Bind tools to models using LangChain's methods
- Provide clear descriptions and examples for each tool

```python
from langchain_core.tools import Tool

calculator_tool = Tool.from_function(
    func=calculate,
    name="calculator",
    description="Useful for performing arithmetic calculations",
    args_schema=CalculatorInput,
)

# Bind tools to the model
model_with_tools = model.bind_tools([calculator_tool])
```

### Streaming

- Use LangChain's streaming capabilities for real-time responses
- Implement proper handlers for streaming events
- Handle streaming errors gracefully

```python
from langchain_core.callbacks import StreamingStdOutCallbackHandler

# Set up streaming
callbacks = [StreamingStdOutCallbackHandler()]

# Use streaming in chain
response = chain.invoke({"problem": user_query}, callbacks=callbacks)
```

### Caching

- Implement LangChain's caching mechanisms to reduce API calls
- Configure appropriate TTL for cached responses
- Use Redis or SQLite for persistent caching

```python
from langchain_community.cache import RedisCache
from langchain_core.globals import set_llm_cache

# Set up Redis cache
set_llm_cache(RedisCache(redis_url="redis://localhost:6379"))
```

## Error Handling

- Implement proper error handling for LLM calls
- Provide fallback mechanisms for API failures
- Log detailed error information

```python
try:
    response = chain.invoke({"problem": user_query})
except Exception as e:
    logger.error(f"Error in LLM call: {e}")
    # Implement fallback mechanism
    response = fallback_response(user_query)
```

## Testing

- Create mock LLMs for testing using LangChain's FakeListLLM
- Test edge cases and error scenarios
- Validate output structures match expectations

```python
from langchain_core.language_models.fake import FakeListLLM

# Create a fake LLM for testing
fake_llm = FakeListLLM(responses=["fake response 1", "fake response 2"])

# Test chain with fake LLM
test_chain = prompt | fake_llm | parser
result = test_chain.invoke({"problem": "test problem"})
```
