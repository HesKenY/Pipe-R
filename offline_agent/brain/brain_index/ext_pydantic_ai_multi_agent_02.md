# Pydantic AI multi-agent applications (2/2)
source: https://github.com/pydantic/pydantic-ai/blob/main/docs/multi-agent-applications.md
repo: https://github.com/pydantic/pydantic-ai
license: MIT | https://github.com/pydantic/pydantic-ai/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
subgraph find_seat
    seat_preference_agent --> ask_user_seat
    ask_user_seat --> seat_preference_agent
  end

seat_preference_agent --> END
```

## Pydantic Graphs

See the [graph](graph.md) documentation on when and how to use graphs.

## Deep Agents

Deep agents are autonomous agents that combine multiple architectural patterns and capabilities to handle complex, multi-step tasks reliably. These patterns can be implemented using Pydantic AI's built-in features and (third-party) toolsets:

- **Planning and progress tracking** — agents break down complex tasks into steps and track their progress, giving users visibility into what the agent is working on. See [Task Management toolsets](toolsets.md#task-management).
- **File system operations** — reading, writing, and editing files with proper abstraction layers that work across in-memory storage, real file systems, and sandboxed containers. See [File Operations toolsets](toolsets.md#file-operations).
- **Task delegation** — spawning specialized sub-agents for specific tasks, with isolated context to prevent recursive delegation issues. See [Agent Delegation](#agent-delegation) above.
- **Sandboxed code execution** — running AI-generated code in isolated environments (typically Docker containers) to prevent accidents. See [Code Execution toolsets](toolsets.md#code-execution).
- **Context management** — automatic conversation summarization to handle long sessions that would otherwise exceed token limits. See [Processing Message History](message-history.md#processing-message-history).
- **Human-in-the-loop** — approval workflows for dangerous operations like code execution or file deletion. See [Requiring Tool Approval](toolsets.md#requiring-tool-approval).
- **Durable execution** — preserving agent state across transient API failures and application errors or restarts. See [Durable Execution](durable_execution/overview.md).

In addition, the community maintains packages that bring these concepts together in a more opinionated way:

- [`pydantic-deep`](https://github.com/vstorm-co/pydantic-deepagents) by [Vstorm](https://vstorm.co/)

## Observing Multi-Agent Systems

Multi-agent systems can be challenging to debug due to their complexity; when multiple agents interact, understanding the flow of execution becomes essential.

### Tracing Agent Delegation

With [Logfire](logfire.md), you can trace the entire flow across multiple agents:

```python
import logfire

logfire.configure()
logfire.instrument_pydantic_ai()

# Your multi-agent code here...
```

Logfire shows you:

- **Which agent handled which part** of the request
- **Delegation decisions**—when and why one agent called another
- **End-to-end latency** broken down by agent
- **Token usage and costs** per agent
- **What triggered the agent run**—the HTTP request, scheduled job, or user action that started it all
- **What happened inside tool calls**—database queries, HTTP requests, file operations, and any other instrumented code that tools execute

This is essential for understanding and optimizing complex agent workflows. When something goes wrong in a multi-agent system, you'll see exactly which agent failed and what it was trying to do, and whether the problem was in the agent's reasoning or in the backend systems it called.

### Full-Stack Visibility

If your PydanticAI application includes a TypeScript frontend, API gateway, or services in other languages, Logfire can trace them too—Logfire provides SDKs for Python, JavaScript/TypeScript, and Rust, plus compatibility with any OpenTelemetry-instrumented application. See traces from your entire stack in a unified view. For details on sending data from other languages using standard OpenTelemetry, see the [alternative clients guide](https://logfire.pydantic.dev/docs/how-to-guides/alternative-clients/).

PydanticAI's instrumentation is built on [OpenTelemetry](https://opentelemetry.io/), so you can also use any OTel-compatible backend. See the [Logfire integration guide](logfire.md) for details.

## Examples

The following examples demonstrate how to use multi-agent patterns in Pydantic AI:

- [Flight booking](examples/flight-booking.md)
