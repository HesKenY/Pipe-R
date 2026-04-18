# Pydantic AI message history (2/2)
source: https://github.com/pydantic/pydantic-ai/blob/main/docs/message-history.md
repo: https://github.com/pydantic/pydantic-ai
license: MIT | https://github.com/pydantic/pydantic-ai/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
avoid surprises:

- Preserve `run_id` on existing messages.
    - When creating new messages in a processor that should be part of the current run, use a
      [context-aware processor](#runcontext-parameter) and set `run_id=ctx.run_id` on the new message.
    - Reordering or removing messages may shift the boundary between "old" and "new" messages, test
      with [`new_messages()`][pydantic_ai.agent.AgentRunResult.new_messages] to verify the behavior
      matches your expectations.

### Usage

The `history_processors` is a list of callables that take a list of
[`ModelMessage`][pydantic_ai.messages.ModelMessage] and return a modified list of the same type.

Each processor is applied in sequence, and processors can be either synchronous or asynchronous.

```python {title="simple_history_processor.py"}
from pydantic_ai import (
    Agent,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

def filter_responses(messages: list[ModelMessage]) -> list[ModelMessage]:
    """Remove all ModelResponse messages, keeping only ModelRequest messages."""
    return [msg for msg in messages if isinstance(msg, ModelRequest)]

# Create agent with history processor
agent = Agent('openai:gpt-5.2', history_processors=[filter_responses])

# Example: Create some conversation history
message_history = [
    ModelRequest(parts=[UserPromptPart(content='What is 2+2?')]),
    ModelResponse(parts=[TextPart(content='2+2 equals 4')]),  # This will be filtered out
]

# When you run the agent, the history processor will filter out ModelResponse messages
# result = agent.run_sync('What about 3+3?', message_history=message_history)
```

#### Keep Only Recent Messages

You can use the `history_processor` to only keep the recent messages:

```python {title="keep_recent_messages.py"}
from pydantic_ai import Agent, ModelMessage

async def keep_recent_messages(messages: list[ModelMessage]) -> list[ModelMessage]:
    """Keep only the last 5 messages to manage token usage."""
    return messages[-5:] if len(messages) > 5 else messages

agent = Agent('openai:gpt-5.2', history_processors=[keep_recent_messages])

# Example: Even with a long conversation history, only the last 5 messages are sent to the model
long_conversation_history: list[ModelMessage] = []  # Your long conversation history here
# result = agent.run_sync('What did we discuss?', message_history=long_conversation_history)
```

!!! warning "Be careful when slicing the message history"
    When slicing the message history, you need to make sure that tool calls and returns are paired, otherwise the LLM may return an error. For more details, refer to [this GitHub issue](https://github.com/pydantic/pydantic-ai/issues/2050#issuecomment-3019976269).

#### `RunContext` parameter

History processors can optionally accept a [`RunContext`][pydantic_ai.tools.RunContext] parameter to access
additional information about the current run, such as dependencies, model information, and usage statistics:

```python {title="context_aware_processor.py"}
from pydantic_ai import Agent, ModelMessage, RunContext

def context_aware_processor(
    ctx: RunContext[None],
    messages: list[ModelMessage],
) -> list[ModelMessage]:
    # Access current usage
    current_tokens = ctx.usage.total_tokens

# Filter messages based on context
    if current_tokens > 1000:
        return messages[-3:]  # Keep only recent messages when token usage is high
    return messages

agent = Agent('openai:gpt-5.2', history_processors=[context_aware_processor])
```

This allows for more sophisticated message processing based on the current state of the agent run.

#### Summarize Old Messages

Use an LLM to summarize older messages to preserve context while reducing tokens.

```python {title="summarize_old_messages.py"}
from pydantic_ai import Agent, ModelMessage

# Use a cheaper model to summarize old messages.
summarize_agent = Agent(
    'openai:gpt-5-mini',
    instructions="""
Summarize this conversation, omitting small talk and unrelated topics.
Focus on the technical discussion and next steps.
""",
)

async def summarize_old_messages(messages: list[ModelMessage]) -> list[ModelMessage]:
    # Summarize the oldest 10 messages
    if len(messages) > 10:
        oldest_messages = messages[:10]
        summary = await summarize_agent.run(message_history=oldest_messages)
        # Return the last message and the summary
        return summary.new_messages() + messages[-1:]

return messages

agent = Agent('openai:gpt-5.2', history_processors=[summarize_old_messages])
```

!!! warning "Be careful when summarizing the message history"
    When summarizing the message history, you need to make sure that tool calls and returns are paired, otherwise the LLM may return an error. For more details, refer to [this GitHub issue](https://github.com/pydantic/pydantic-ai/issues/2050#issuecomment-3019976269), where you can find examples of summarizing the message history.

### Testing History Processors

You can test what messages are actually sent to the model provider using
[`FunctionModel`][pydantic_ai.models.function.FunctionModel]:

```python {title="test_history_processor.py"}
import pytest

from pydantic_ai import (
    Agent,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

@pytest.fixture
def received_messages() -> list[ModelMessage]:
    return []

@pytest.fixture
def function_model(received_messages: list[ModelMessage]) -> FunctionModel:
    def capture_model_function(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        # Capture the messages that the provider actually receives
        received_messages.clear()
        received_messages.extend(messages)
        return ModelResponse(parts=[TextPart(content='Provider response')])

return FunctionModel(capture_model_function)

def test_history_processor(function_model: FunctionModel, received_messages: list[ModelMessage]):
    def filter_responses(messages: list[ModelMessage]) -> list[ModelMessage]:
        return [msg for msg in messages if isinstance(msg, ModelRequest)]

agent = Agent(function_model, history_processors=[filter_responses])

message_history = [
        ModelRequest(parts=[UserPromptPart(content='Question 1')]),
        ModelResponse(parts=[TextPart(content='Answer 1')]),
    ]

agent.run_sync('Question 2', message_history=message_history)
    assert received_messages == [
        ModelRequest(parts=[UserPromptPart(content='Question 1')]),
        ModelRequest(parts=[UserPromptPart(content='Question 2')]),
    ]
```

### Multiple Processors

You can also use multiple processors:

```python {title="multiple_history_processors.py"}
from pydantic_ai import Agent, ModelMessage, ModelRequest

def filter_responses(messages: list[ModelMessage]) -> list[ModelMessage]:
    return [msg for msg in messages if isinstance(msg, ModelRequest)]

def summarize_old_messages(messages: list[ModelMessage]) -> list[ModelMessage]:
    return messages[-5:]

agent = Agent('openai:gpt-5.2', history_processors=[filter_responses, summarize_old_messages])
```

In this case, the `filter_responses` processor will be applied first, and the
`summarize_old_messages` processor will be applied second.

## Examples

For a more complete example of using messages in conversations, see the [chat app](examples/chat-app.md) example.
