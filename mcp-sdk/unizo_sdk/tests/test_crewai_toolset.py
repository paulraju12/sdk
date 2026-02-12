"""Unit tests for the CrewAI adapter (unizo_crewai.toolset)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from types import SimpleNamespace

from unizo_core.actions import Action


# ===================================================================
# CrewAI BaseTool conversion
# ===================================================================


class TestCrewAIToolConversion:
    """Verify that UnizoCrewAIToolSet.get_tools() returns proper
    CrewAI BaseTool instances."""

    @pytest.fixture(autouse=True)
    def setup_toolset(self, mock_session):
        from unizo_crewai.toolset import UnizoCrewAIToolSet

        self.toolset = UnizoCrewAIToolSet(api_key="test_key")
        self.toolset.session = mock_session

    @pytest.mark.asyncio
    async def test_returns_list(self):
        tools = await self.toolset.get_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

    @pytest.mark.asyncio
    async def test_tool_is_base_tool(self):
        from crewai.tools import BaseTool

        tools = await self.toolset.get_tools()
        for tool in tools:
            assert isinstance(tool, BaseTool), (
                f"Expected BaseTool, got {type(tool).__name__}"
            )

    @pytest.mark.asyncio
    async def test_tool_has_name_and_description(self):
        tools = await self.toolset.get_tools()
        for tool in tools:
            assert tool.name, "Tool name must not be empty"
            assert tool.description, "Tool description must not be empty"

    @pytest.mark.asyncio
    async def test_tool_has_args_schema(self):
        """Each CrewAI BaseTool should carry a Pydantic args_schema."""
        tools = await self.toolset.get_tools()
        for tool in tools:
            assert tool.args_schema is not None, (
                f"Tool {tool.name} missing args_schema"
            )

    @pytest.mark.asyncio
    async def test_create_ticket_schema_fields(self):
        tools = await self.toolset.get_tools(actions=[Action.CREATE_TICKET])
        assert len(tools) == 1
        schema = tools[0].args_schema
        field_names = set(schema.model_fields.keys())
        assert "ticket_name" in field_names
        assert "integration_id" in field_names

    @pytest.mark.asyncio
    async def test_filter_by_actions(self):
        tools = await self.toolset.get_tools(
            actions=[Action.LIST_SERVICES, Action.HEALTH_CHECK]
        )
        names = {t.name for t in tools}
        assert names == {"list_services", "health_check"}

    @pytest.mark.asyncio
    async def test_tool_count_matches_mock(self):
        tools = await self.toolset.get_tools()
        # The mock provides 4 tools
        assert len(tools) == 4

    @pytest.mark.asyncio
    async def test_has_run_method(self):
        """CrewAI tools must implement _run."""
        tools = await self.toolset.get_tools()
        for tool in tools:
            assert hasattr(tool, "_run"), f"Tool {tool.name} missing _run method"


class TestCrewAIToolSchema:
    """Deeper inspection of the dynamic Pydantic schema on CrewAI tools."""

    @pytest.fixture(autouse=True)
    def setup_toolset(self, mock_session):
        from unizo_crewai.toolset import UnizoCrewAIToolSet

        self.toolset = UnizoCrewAIToolSet(api_key="test_key")
        self.toolset.session = mock_session

    @pytest.mark.asyncio
    async def test_schema_json_serialisable(self):
        import json

        tools = await self.toolset.get_tools()
        for tool in tools:
            schema_dict = tool.args_schema.model_json_schema()
            json.dumps(schema_dict)  # must not raise

    @pytest.mark.asyncio
    async def test_health_check_has_no_required_fields(self):
        tools = await self.toolset.get_tools(actions=[Action.HEALTH_CHECK])
        assert len(tools) == 1
        schema = tools[0].args_schema
        # health_check has no properties in the mock
        required = [
            name for name, field in schema.model_fields.items() if field.is_required()
        ]
        assert required == []

    @pytest.mark.asyncio
    async def test_create_ticket_required_fields(self):
        tools = await self.toolset.get_tools(actions=[Action.CREATE_TICKET])
        schema = tools[0].args_schema
        for field_name in ["ticket_name", "integration_id", "organization_id", "collection_id"]:
            field = schema.model_fields.get(field_name)
            assert field is not None, f"Missing field: {field_name}"
            assert field.is_required(), f"Field {field_name} should be required"
