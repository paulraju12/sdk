"""Unit tests for unizo_core — client, actions, models, and exceptions."""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from types import SimpleNamespace

from unizo_core.client import UnizoToolSet
from unizo_core.actions import Action
from unizo_core.models import (
    TicketData,
    Service,
    Integration,
    Organization,
    Collection,
    TicketSummary,
)
from unizo_core.exceptions import UnizoError, AuthenticationError, ToolExecutionError


# ===================================================================
# UnizoToolSet — initialisation
# ===================================================================


class TestUnizoToolSetInit:
    """Verify constructor validation and attribute assignment."""

    def test_valid_api_key(self):
        ts = UnizoToolSet(api_key="key_abc123")
        assert ts.api_key == "key_abc123"
        assert ts.session is None
        assert "unizo.ai" in ts.server_url  # default URL

    def test_custom_server_url(self):
        ts = UnizoToolSet(api_key="key_abc123", server_url="http://localhost:8080")
        assert ts.server_url == "http://localhost:8080"

    def test_empty_api_key_raises(self):
        with pytest.raises(ValueError, match="UNIZO_API_KEY is required"):
            UnizoToolSet(api_key="")

    def test_none_api_key_raises(self):
        with pytest.raises((ValueError, TypeError)):
            UnizoToolSet(api_key=None)


# ===================================================================
# Action enum
# ===================================================================


class TestAction:
    """Verify every expected enum member exists with the right value."""

    EXPECTED = {
        "LIST_SERVICES": "list_services",
        "LIST_INTEGRATIONS": "list_integrations",
        "LIST_ORGANIZATIONS": "list_organizations",
        "LIST_COLLECTIONS": "list_collections",
        "CONFIRM_TICKET_CREATION": "confirm_ticket_creation",
        "CREATE_TICKET": "create_ticket",
        "LIST_TICKETS": "list_tickets",
        "HEALTH_CHECK": "health_check",
    }

    def test_all_members_present(self):
        for member_name in self.EXPECTED:
            assert hasattr(Action, member_name), f"Missing enum member: {member_name}"

    def test_values(self):
        for member_name, expected_value in self.EXPECTED.items():
            assert Action[member_name].value == expected_value

    def test_total_count(self):
        assert len(Action) == len(self.EXPECTED)


# ===================================================================
# Pydantic models
# ===================================================================


class TestTicketData:
    """Validate TicketData model constraints."""

    def test_minimal_valid(self):
        ticket = TicketData(name="Bug report")
        assert ticket.name == "Bug report"
        assert ticket.description is None
        assert ticket.status is None

    def test_full_valid(self):
        ticket = TicketData(
            name="Bug report",
            description="Something broke",
            status="OPEN",
            priority="High",
            type="Bug",
        )
        assert ticket.priority == "High"

    def test_missing_required_name(self):
        with pytest.raises(Exception):  # Pydantic ValidationError
            TicketData()  # name is required


class TestOtherModels:
    """Spot-check remaining Pydantic models."""

    def test_service(self):
        svc = Service(name="Jira")
        assert svc.name == "Jira"

    def test_integration(self):
        integ = Integration(id="int_1", name="GitHub")
        assert integ.id == "int_1"

    def test_organization(self):
        org = Organization(id="org_1", name="Acme")
        assert org.id == "org_1"

    def test_collection(self):
        col = Collection(id="col_1", name="Sprint 1")
        assert col.description is None

    def test_ticket_summary(self):
        ts = TicketSummary(id="T-1", name="Fix login", type="Bug", status="OPEN")
        assert ts.status == "OPEN"


# ===================================================================
# Exception hierarchy
# ===================================================================


class TestExceptions:
    """Ensure the exception class tree is correct."""

    def test_unizo_error_is_exception(self):
        assert issubclass(UnizoError, Exception)

    def test_authentication_error_inherits(self):
        assert issubclass(AuthenticationError, UnizoError)

    def test_tool_execution_error_inherits(self):
        assert issubclass(ToolExecutionError, UnizoError)

    def test_raise_and_catch_base(self):
        with pytest.raises(UnizoError):
            raise ToolExecutionError("boom")

    def test_message_preserved(self):
        err = AuthenticationError("bad key")
        assert str(err) == "bad key"


# ===================================================================
# get_tools — with a mocked MCP session
# ===================================================================


class TestGetTools:
    """Test UnizoToolSet.get_tools() with a mock session injected."""

    @pytest.fixture(autouse=True)
    def setup_toolset(self, mock_session):
        self.toolset = UnizoToolSet(api_key="test_key")
        # Inject mock session so connect() is never called
        self.toolset.session = mock_session

    @pytest.mark.asyncio
    async def test_returns_all_tools(self):
        tools = await self.toolset.get_tools()
        assert isinstance(tools, list)
        assert len(tools) == 4
        names = {t["name"] for t in tools}
        assert "list_services" in names
        assert "create_ticket" in names

    @pytest.mark.asyncio
    async def test_tool_has_expected_keys(self):
        tools = await self.toolset.get_tools()
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool
            assert tool["parameters"]["type"] == "object"

    @pytest.mark.asyncio
    async def test_filter_by_single_action(self):
        tools = await self.toolset.get_tools(actions=[Action.CREATE_TICKET])
        assert len(tools) == 1
        assert tools[0]["name"] == "create_ticket"

    @pytest.mark.asyncio
    async def test_filter_by_multiple_actions(self):
        tools = await self.toolset.get_tools(
            actions=[Action.CREATE_TICKET, Action.HEALTH_CHECK]
        )
        names = {t["name"] for t in tools}
        assert names == {"create_ticket", "health_check"}

    @pytest.mark.asyncio
    async def test_filter_returns_empty_for_unmatched(self):
        tools = await self.toolset.get_tools(actions=[Action.LIST_INTEGRATIONS])
        # LIST_INTEGRATIONS is not in the mock tools list
        assert tools == []

    @pytest.mark.asyncio
    async def test_json_string_input_schema(self, mock_session):
        """If inputSchema is a JSON string, get_tools should parse it."""
        string_schema_tool = SimpleNamespace()
        string_schema_tool.name = "string_schema_tool"
        string_schema_tool.description = "Tool with JSON-string schema"
        string_schema_tool.inputSchema = json.dumps({
            "type": "object",
            "properties": {"foo": {"type": "string"}},
            "required": ["foo"],
        })
        resp = SimpleNamespace()
        resp.tools = [string_schema_tool]
        mock_session.list_tools.return_value = resp

        tools = await self.toolset.get_tools()
        assert len(tools) == 1
        assert "foo" in tools[0]["parameters"]["properties"]


# ===================================================================
# execute_action — with a mocked MCP session
# ===================================================================


class TestExecuteAction:
    """Test UnizoToolSet.execute_action() with a mock session."""

    @pytest.fixture(autouse=True)
    def setup_toolset(self, mock_session):
        self.toolset = UnizoToolSet(api_key="test_key")
        self.toolset.session = mock_session
        self.mock_session = mock_session

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        result = await self.toolset.execute_action(
            Action.CREATE_TICKET,
            {"ticket_name": "Test", "integration_id": "i1", "organization_id": "o1", "collection_id": "c1"},
        )
        assert result["status"] == "ok"
        assert result["ticket_id"] == "T-001"

    @pytest.mark.asyncio
    async def test_calls_session_call_tool(self):
        await self.toolset.execute_action(Action.HEALTH_CHECK, {})
        self.mock_session.call_tool.assert_awaited_once_with("health_check", {})

    @pytest.mark.asyncio
    async def test_raises_tool_execution_error_on_failure(self):
        self.mock_session.call_tool.side_effect = RuntimeError("connection lost")
        with pytest.raises(ToolExecutionError, match="Failed to execute action"):
            await self.toolset.execute_action(Action.HEALTH_CHECK, {})

    @pytest.mark.asyncio
    async def test_structured_content_preferred(self):
        """When structuredContent is present, it should be returned."""
        structured = {"status": "structured_ok"}
        result_obj = SimpleNamespace()
        result_obj.structuredContent = structured
        result_obj.content = []
        self.mock_session.call_tool.return_value = result_obj

        result = await self.toolset.execute_action(Action.HEALTH_CHECK, {})
        assert result == structured
