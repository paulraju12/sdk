"""Unit tests for the OpenAI adapter (unizo_openai.toolset)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from types import SimpleNamespace

from unizo_core.actions import Action


# ===================================================================
# OpenAI tool schema conversion
# ===================================================================


class TestOpenAIToolConversion:
    """Verify that UnizoOpenAIToolSet.get_tools() produces schemas that
    conform to the OpenAI function-calling specification."""

    @pytest.fixture(autouse=True)
    def setup_toolset(self, mock_session):
        # Patch AsyncOpenAI so we never hit the real API
        with patch("unizo_openai.toolset.AsyncOpenAI"):
            from unizo_openai.toolset import UnizoOpenAIToolSet

            self.toolset = UnizoOpenAIToolSet(
                api_key="unizo_test_key",
                openai_api_key="sk-test",
            )
            self.toolset.session = mock_session

    @pytest.mark.asyncio
    async def test_returns_list_of_dicts(self):
        tools = await self.toolset.get_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

    @pytest.mark.asyncio
    async def test_each_tool_has_type_function(self):
        """OpenAI spec requires every entry to have `type: 'function'`."""
        tools = await self.toolset.get_tools()
        for tool in tools:
            assert tool["type"] == "function", f"Tool missing type=function: {tool}"

    @pytest.mark.asyncio
    async def test_function_key_structure(self):
        """Each tool must have a `function` dict with name, description, parameters."""
        tools = await self.toolset.get_tools()
        for tool in tools:
            func = tool["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func

    @pytest.mark.asyncio
    async def test_parameters_is_object_type(self):
        tools = await self.toolset.get_tools()
        for tool in tools:
            params = tool["function"]["parameters"]
            assert params.get("type") == "object"

    @pytest.mark.asyncio
    async def test_create_ticket_has_required_fields(self):
        tools = await self.toolset.get_tools(actions=[Action.CREATE_TICKET])
        assert len(tools) == 1
        func = tools[0]["function"]
        assert func["name"] == "create_ticket"
        props = func["parameters"].get("properties", {})
        assert "ticket_name" in props

    @pytest.mark.asyncio
    async def test_filter_actions(self):
        tools = await self.toolset.get_tools(actions=[Action.HEALTH_CHECK])
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "health_check"

    @pytest.mark.asyncio
    async def test_no_extra_top_level_keys(self):
        """OpenAI spec only allows 'type' and 'function' at top level."""
        tools = await self.toolset.get_tools()
        allowed_keys = {"type", "function"}
        for tool in tools:
            assert set(tool.keys()) <= allowed_keys, (
                f"Unexpected keys: {set(tool.keys()) - allowed_keys}"
            )


class TestOpenAIToolSetInit:
    """Test that UnizoOpenAIToolSet correctly initialises both API keys."""

    def test_requires_both_keys(self):
        with patch("unizo_openai.toolset.AsyncOpenAI"):
            from unizo_openai.toolset import UnizoOpenAIToolSet

            ts = UnizoOpenAIToolSet(api_key="unizo_key", openai_api_key="sk-key")
            assert ts.api_key == "unizo_key"

    def test_empty_unizo_key_raises(self):
        with patch("unizo_openai.toolset.AsyncOpenAI"):
            from unizo_openai.toolset import UnizoOpenAIToolSet

            with pytest.raises(ValueError):
                UnizoOpenAIToolSet(api_key="", openai_api_key="sk-key")
