# Pydantic AI tools (2/2)
source: https://github.com/pydantic/pydantic-ai/blob/main/docs/tools.md
repo: https://github.com/pydantic/pydantic-ai
license: MIT | https://github.com/pydantic/pydantic-ai/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
[`TestModel.last_model_request_parameters`][pydantic_ai.models.test.TestModel.last_model_request_parameters] to inspect the tool schema that would be passed to the model.

```python {title="single_parameter_tool.py"}
from pydantic import BaseModel

from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

agent = Agent()

class Foobar(BaseModel):
    """This is a Foobar"""

x: int
    y: str
    z: float = 3.14

@agent.tool_plain
def foobar(f: Foobar) -> str:
    return str(f)

test_model = TestModel()
result = agent.run_sync('hello', model=test_model)
print(result.output)
#> {"foobar":"x=0 y='a' z=3.14"}
print(test_model.last_model_request_parameters.function_tools)
"""
[
    ToolDefinition(
        name='foobar',
        parameters_json_schema={
            'properties': {
                'x': {'type': 'integer'},
                'y': {'type': 'string'},
                'z': {'default': 3.14, 'type': 'number'},
            },
            'required': ['x', 'y'],
            'title': 'Foobar',
            'type': 'object',
        },
        description='This is a Foobar',
    )
]
"""
```

_(This example is complete, it can be run "as is")_

!!! tip "Debugging Tool Calls"
    Understanding tool behavior is crucial for agent development. By instrumenting your agent with [Logfire](logfire.md), you can see:

- What arguments were passed to each tool
    - What each tool returned
    - How long each tool took to execute
    - Any errors that occurred

This visibility helps you understand why an agent made specific decisions and identify issues in tool implementations.

## See Also

For more tool features and integrations, see:

- [Advanced Tool Features](tools-advanced.md) - Custom schemas, dynamic tools, tool execution and retries
- [Toolsets](toolsets.md) - Managing collections of tools
- [Builtin Tools](builtin-tools.md) - Native tools provided by LLM providers
- [Common Tools](common-tools.md) - Ready-to-use tool implementations
- [Third-Party Tools](third-party-tools.md) - Integrations with MCP, LangChain, ACI.dev and other tool libraries
- [Deferred Tools](deferred-tools.md) - Tools requiring approval or external execution
