---
description: langGraph Logging
globs: *.py
alwaysApply: false
---
## Langgraph Logging

- Log the start and end of node execution
- Log important state changes and decisions
- Use consistent logging format
- Log tool calls and their results

```python
logger.log_node_start("Node Name")
logger.log_node_output("Node Name", output, "output_field")
logger.logger.info("Tool call detected: %s", tool_name)
logger.logger.info("Tool result: %s", result)
```
