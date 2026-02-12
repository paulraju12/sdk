"""Shared fixtures for Unizo SDK unit tests."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace


# ---------------------------------------------------------------------------
# Fake MCP tool objects returned by session.list_tools()
# ---------------------------------------------------------------------------

def _make_tool(name: str, description: str, input_schema: dict):
    """Return a lightweight object that mirrors the MCP Tool shape."""
    tool = SimpleNamespace()
    tool.name = name
    tool.description = description
    tool.inputSchema = input_schema
    return tool


MOCK_TOOLS = [
    _make_tool(
        name="list_services",
        description="List all available services",
        input_schema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    _make_tool(
        name="create_ticket",
        description="Create a new ticket",
        input_schema={
            "type": "object",
            "properties": {
                "ticket_name": {"type": "string", "description": "Ticket name"},
                "ticket_description": {"type": "string", "description": "Ticket description"},
                "ticket_status": {"type": "string", "description": "Ticket status"},
                "ticket_priority": {"type": "string", "description": "Ticket priority"},
                "ticket_type": {"type": "string", "description": "Ticket type"},
                "integration_id": {"type": "string", "description": "Integration ID"},
                "organization_id": {"type": "string", "description": "Organization ID"},
                "collection_id": {"type": "string", "description": "Collection ID"},
            },
            "required": ["ticket_name", "integration_id", "organization_id", "collection_id"],
        },
    ),
    _make_tool(
        name="list_tickets",
        description="List tickets in a collection",
        input_schema={
            "type": "object",
            "properties": {
                "collection_id": {"type": "string", "description": "Collection ID"},
            },
            "required": ["collection_id"],
        },
    ),
    _make_tool(
        name="health_check",
        description="Check server health",
        input_schema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
]


@pytest.fixture
def mock_tools():
    """Return the list of mock MCP tool objects."""
    return MOCK_TOOLS


@pytest.fixture
def mock_list_tools_response():
    """Return a mock response object whose `.tools` attribute is MOCK_TOOLS."""
    response = SimpleNamespace()
    response.tools = MOCK_TOOLS
    return response


@pytest.fixture
def mock_call_tool_result():
    """Return a mock result from session.call_tool()."""
    content_item = SimpleNamespace()
    content_item.text = json.dumps({"status": "ok", "ticket_id": "T-001"})
    result = SimpleNamespace()
    result.structuredContent = None
    result.content = [content_item]
    return result


@pytest.fixture
def mock_session(mock_list_tools_response, mock_call_tool_result):
    """Return an AsyncMock that behaves like a ClientSession."""
    session = AsyncMock()
    session.initialize = AsyncMock()
    session.list_tools = AsyncMock(return_value=mock_list_tools_response)
    session.call_tool = AsyncMock(return_value=mock_call_tool_result)
    return session
