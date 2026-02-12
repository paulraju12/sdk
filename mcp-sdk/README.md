# Unizo MCP SDK -- Multi-Framework AI Integration SDK

A Python SDK that bridges **Unizo ticketing** with three leading AI agent frameworks -- **CrewAI**, **LangChain**, and **OpenAI** -- through the Model Context Protocol (MCP) over Server-Sent Events (SSE).

---

## Architecture

```
+------------------+       +-------------------+       +-----------------+       +---------------+
|                  |       |                   |       |                 |       |               |
|  AI Framework    +------>+  SDK Adapter      +------>+  MCP Protocol   +------>+  Unizo Server |
|  (CrewAI /       |       |  (unizo_crewai /  |       |  (SSE Client)   |       |  (Ticketing)  |
|   LangChain /    |       |   unizo_langchain |       |                 |       |               |
|   OpenAI)        |       |   / unizo_openai) |       |                 |       |               |
+------------------+       +-------------------+       +-----------------+       +---------------+
                                    |
                                    v
                           +-------------------+
                           |   unizo_core      |
                           |   - client.py     |
                           |   - actions.py    |
                           |   - models.py     |
                           |   - exceptions.py |
                           +-------------------+
```

**Data flow:** Your application creates a framework-specific toolset (e.g. `UnizoCrewAIToolSet`). The toolset inherits from `UnizoToolSet`, which opens an SSE connection to the Unizo MCP server using the `mcp` library. Tool schemas are fetched over MCP and converted into the format each AI framework expects. When the AI agent invokes a tool, the call travels back through the adapter, across MCP, and into Unizo's ticketing backend.

---

## Supported Frameworks

| Framework  | Adapter Module      | Output Type                   | Sync / Async |
|------------|---------------------|-------------------------------|--------------|
| CrewAI     | `unizo_crewai`      | `crewai.tools.BaseTool`       | Both         |
| LangChain  | `unizo_langchain`   | `langchain_core.StructuredTool` | Async      |
| OpenAI     | `unizo_openai`      | OpenAI function-calling dict  | Async        |

---

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/unizo-sdk.git
cd unizo-sdk/mcp-sdk/unizo_sdk

# Install dependencies
pip install -r requirements.txt

# Or install as a package in development mode
pip install -e .
```

### Environment variables

Copy the example file and fill in your keys:

```bash
cp .env.example .env
```

```
UNIZO_API_KEY=your_unizo_api_key_here
OPENAI_API_KEY=your_openai_api_key_here     # only needed for OpenAI adapter
```

---

## Quick Start

### CrewAI

```python
import asyncio
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from unizo_crewai import UnizoCrewAIToolSet
from unizo_core import Action

async def main():
    toolset = UnizoCrewAIToolSet(api_key="YOUR_UNIZO_KEY")
    await toolset.connect()

    tools = await toolset.get_tools([
        Action.LIST_SERVICES,
        Action.CREATE_TICKET,
        Action.LIST_TICKETS,
    ])

    agent = Agent(
        role="Ticketing Agent",
        goal="Manage tickets in Unizo",
        backstory="You are an AI agent for ticket management.",
        tools=tools,
        llm=ChatOpenAI(api_key="YOUR_OPENAI_KEY"),
    )

    task = Task(
        description="Create a high-priority bug ticket.",
        agent=agent,
        expected_output="Ticket creation status",
    )

    crew = Crew(agents=[agent], tasks=[task])
    result = await crew.kickoff_async()
    print(result)

    await toolset.cleanup()

asyncio.run(main())
```

### LangChain

```python
import asyncio
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from unizo_langchain import UnizoLangChainToolSet
from unizo_core import Action

async def main():
    toolset = UnizoLangChainToolSet(api_key="YOUR_UNIZO_KEY")
    await toolset.connect()

    tools = await toolset.get_tools([
        Action.LIST_SERVICES,
        Action.CREATE_TICKET,
    ])

    llm = ChatOpenAI(api_key="YOUR_OPENAI_KEY")
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a ticketing agent."),
        ("human", "{input}"),
    ])

    agent = create_openai_tools_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    result = await executor.ainvoke({"input": "List all services"})
    print(result)

    await toolset.cleanup()

asyncio.run(main())
```

### OpenAI (function calling)

```python
import asyncio
from unizo_openai import UnizoOpenAIToolSet
from unizo_core import Action

async def main():
    toolset = UnizoOpenAIToolSet(
        api_key="YOUR_UNIZO_KEY",
        openai_api_key="YOUR_OPENAI_KEY",
    )

    # process_query handles the full tool-calling loop
    response, messages = await toolset.process_query(
        "List all available services"
    )
    print(response)

    await toolset.cleanup()

asyncio.run(main())
```

---

## Available Actions

| Action Enum                  | MCP Tool Name              | Description                       |
|------------------------------|----------------------------|-----------------------------------|
| `Action.LIST_SERVICES`       | `list_services`            | List all available services       |
| `Action.LIST_INTEGRATIONS`   | `list_integrations`        | List configured integrations      |
| `Action.LIST_ORGANIZATIONS`  | `list_organizations`       | List organizations                |
| `Action.LIST_COLLECTIONS`    | `list_collections`         | List collections (projects)       |
| `Action.CONFIRM_TICKET_CREATION` | `confirm_ticket_creation` | Confirm before creating a ticket |
| `Action.CREATE_TICKET`       | `create_ticket`            | Create a new ticket               |
| `Action.LIST_TICKETS`        | `list_tickets`             | List tickets in a collection      |
| `Action.HEALTH_CHECK`        | `health_check`             | Check server health               |

---

## Running Tests

The project contains two kinds of tests:

- **Unit tests** (`tests/test_core.py`, `tests/test_openai_toolset.py`, `tests/test_langchain_toolset.py`, `tests/test_crewai_toolset.py`) -- mock the MCP session, no network required.
- **Integration tests** (`tests/test_crewai.py`, `tests/test_langchain.py`) -- hit real APIs, require valid keys.

### Run unit tests

```bash
cd mcp-sdk/unizo_sdk

# Install test dependencies
pip install pytest pytest-asyncio

# Run all unit tests
python -m pytest tests/test_core.py tests/test_openai_toolset.py tests/test_langchain_toolset.py tests/test_crewai_toolset.py -v
```

### CI

A GitHub Actions workflow is included at `.github/workflows/ci.yml`. It runs unit tests and an optional mypy lint pass on every push and pull request to `main`.

---

## Project Structure

```
mcp-sdk/
  unizo_sdk/
    unizo_core/           # Shared base layer
      client.py           # UnizoToolSet -- SSE connection, get_tools, execute_action
      actions.py          # Action enum
      models.py           # Pydantic models (TicketData, Service, etc.)
      exceptions.py       # UnizoError, AuthenticationError, ToolExecutionError
    unizo_crewai/         # CrewAI adapter
      toolset.py          # UnizoCrewAIToolSet -> List[BaseTool]
    unizo_langchain/      # LangChain adapter
      toolset.py          # UnizoLangChainToolSet -> List[StructuredTool]
    unizo_openai/         # OpenAI adapter
      toolset.py          # UnizoOpenAIToolSet -> List[dict] (function schemas)
    tests/                # Unit and integration tests
    requirements.txt
    setup.py
  .github/workflows/ci.yml
  README.md
```

---

## Design Decisions

### Why MCP (Model Context Protocol)?

MCP provides a **standardised, transport-agnostic interface** between AI clients and tool servers. By using MCP rather than a bespoke REST client the SDK gains:

- A single protocol to learn regardless of the downstream ticketing provider.
- Built-in schema discovery (`list_tools`) so the SDK never hard-codes tool definitions.
- Streaming via SSE, which avoids repeated HTTP handshakes during long agent runs.

### Why the Adapter Pattern?

Each AI framework defines its own tool abstraction (`BaseTool`, `StructuredTool`, OpenAI function-calling dicts). A thin adapter layer lets the core MCP client remain **framework-agnostic** while each adapter handles only the conversion logic specific to its framework. Adding a new framework means writing a single new adapter module without touching `unizo_core`.

### Why Async-First?

AI agent loops are inherently I/O-bound (network calls to both the MCP server and the LLM provider). An async-first design lets the event loop multiplex these calls efficiently. The CrewAI adapter additionally provides a synchronous `_run` fallback for compatibility with older CrewAI versions that do not support async tools natively.

---

## Tradeoffs

| Decision | Benefit | Cost |
|---|---|---|
| **Single SSE connection per toolset** | Simple lifecycle; no connection pool to manage | Cannot parallelise independent MCP calls within one toolset instance |
| **Dynamic Pydantic schema generation** | Schemas always match the server; zero hard-coding | Slight runtime overhead; harder to type-check statically |
| **Adapter inheritance (subclassing UnizoToolSet)** | Adapters get `connect`, `execute_action` for free | Tight coupling to `UnizoToolSet` internals; harder to swap transport |
| **JSON-string fallback in `inputSchema`** | Handles servers that return schemas as strings | Extra branch to test; masks upstream serialisation bugs |
| **No retry / backoff on MCP calls** | Keeps the SDK thin and predictable | Transient network errors surface immediately to callers |

---

## Future Improvements

- **Additional framework adapters** -- e.g., AutoGen, Haystack, or a generic adapter that returns plain Python callables.
- **Connection pooling** -- allow multiple concurrent MCP sessions for high-throughput agent workloads.
- **Retry strategies** -- configurable exponential backoff with jitter for transient SSE / network errors.
- **Caching of tool schemas** -- avoid repeated `list_tools` calls when the server schema has not changed.
- **Streaming tool results** -- surface partial results from long-running MCP tool calls back to the agent in real time.
- **Observability hooks** -- emit OpenTelemetry spans for every MCP call so users can trace end-to-end latency.

---

## License

See [LICENSE](LICENSE) for details.
