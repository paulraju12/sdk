"""Unit tests for the LangChain adapter (unizo_langchain.toolset)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from types import SimpleNamespace

from unizo_core.actions import Action


# ===================================================================
# LangChain StructuredTool conversion
# ===================================================================


class TestLangChainToolConversion:
    """Verify that UnizoLangChainToolSet.get_tools() returns proper
    LangChain StructuredTool instances with correct schemas."""

    @pytest.fixture(autouse=True)
    def setup_toolset(self, mock_session):
        from unizo_langchain.toolset import UnizoLangChainToolSet

        self.toolset = UnizoLangChainToolSet(api_key="test_key")
        self.toolset.session = mock_session

    @pytest.mark.asyncio
    async def test_returns_list(self):
        tools = await self.toolset.get_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

    @pytest.mark.asyncio
    async def test_tool_is_structured_tool(self):
        from langchain_core.tools import StructuredTool

        tools = await self.toolset.get_tools()
        for tool in tools:
            assert isinstance(tool, StructuredTool), (
                f"Expected StructuredTool, got {type(tool).__name__}"
            )

    @pytest.mark.asyncio
    async def test_tool_has_name_and_description(self):
        tools = await self.toolset.get_tools()
        for tool in tools:
            assert tool.name, "Tool name must not be empty"
            assert tool.description, "Tool description must not be empty"

    @pytest.mark.asyncio
    async def test_tool_has_args_schema(self):
        """Each StructuredTool should carry a Pydantic args_schema."""
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
    async def test_filter_actions(self):
        tools = await self.toolset.get_tools(
            actions=[Action.LIST_SERVICES, Action.HEALTH_CHECK]
        )
        names = {t.name for t in tools}
        assert names == {"list_services", "health_check"}

    @pytest.mark.asyncio
    async def test_tool_is_async(self):
        """StructuredTool should have a coroutine set."""
        tools = await self.toolset.get_tools()
        for tool in tools:
            assert tool.coroutine is not None, (
                f"Tool {tool.name} should be async (coroutine set)"
            )


class TestLangChainSchemaGeneration:
    """Test that dynamically generated Pydantic schemas are well-formed."""

    @pytest.fixture(autouse=True)
    def setup_toolset(self, mock_session):
        from unizo_langchain.toolset import UnizoLangChainToolSet

        self.toolset = UnizoLangChainToolSet(api_key="test_key")
        self.toolset.session = mock_session

    @pytest.mark.asyncio
    async def test_schema_json_serialisable(self):
        import json

        tools = await self.toolset.get_tools()
        for tool in tools:
            schema_dict = tool.args_schema.model_json_schema()
            # Should not raise
            json.dumps(schema_dict)

    @pytest.mark.asyncio
    async def test_required_fields_marked(self):
        tools = await self.toolset.get_tools(actions=[Action.CREATE_TICKET])
        schema = tools[0].args_schema
        # Fields listed as required in mock should be required in the Pydantic model
        for field_name in ["ticket_name", "integration_id", "organization_id", "collection_id"]:
            field = schema.model_fields.get(field_name)
            assert field is not None, f"Missing field: {field_name}"
            assert field.is_required(), f"Field {field_name} should be required"

    @pytest.mark.asyncio
    async def test_optional_fields_not_required(self):
        tools = await self.toolset.get_tools(actions=[Action.CREATE_TICKET])
        schema = tools[0].args_schema
        for field_name in ["ticket_description", "ticket_status", "ticket_priority", "ticket_type"]:
            field = schema.model_fields.get(field_name)
            assert field is not None, f"Missing field: {field_name}"
            assert not field.is_required(), f"Field {field_name} should be optional"
