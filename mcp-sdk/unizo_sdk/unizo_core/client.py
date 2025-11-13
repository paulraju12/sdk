import json
import logging
from typing import List, Dict, Any, Optional
from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.client.sse import sse_client
from .actions import Action
from .exceptions import UnizoError, AuthenticationError, ToolExecutionError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("unizo-core")


class UnizoToolSet:
    def __init__(self, api_key: str, server_url: str = "http://api.unizo.ai/mcp/ticketing"):
        if not api_key:
            logger.error("UNIZO_API_KEY is not provided or empty")
            raise ValueError("UNIZO_API_KEY is required")
        self.api_key = api_key
        self.server_url = server_url
        self.session = None
        self.exit_stack = AsyncExitStack()
        logger.info("UnizoToolSet initialized")

    async def connect(self):
        """Connect to the Unizo MCP server using SSE."""
        logger.debug(f"Connecting to SSE MCP server at {self.server_url}")
        headers = {"apikey": self.api_key}
        self._streams_context = sse_client(url=self.server_url, headers=headers)
        streams = await self._streams_context.__aenter__()
        self._session_context = ClientSession(*streams)
        self.session = await self._session_context.__aenter__()
        await self.session.initialize()
        response = await self.session.list_tools()
        tools = response.tools
        logger.info(f"Connected to Unizo MCP Server. Available tools: {[tool.name for tool in tools]}")

    async def get_tools(self, actions: Optional[List[Action]] = None) -> List[Dict[str, Any]]:
        """Fetch tool schemas from the MCP server."""
        if not self.session:
            await self.connect()
        try:
            response = await self.session.list_tools()
            tools = []
            for tool in response.tools:
                # Parse inputSchema if it's a JSON string
                input_schema = tool.inputSchema
                if isinstance(input_schema, str):
                    try:
                        input_schema = json.loads(input_schema)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse inputSchema for tool {tool.name}: {str(e)}")
                        input_schema = {}
                logger.debug(f"Raw inputSchema for {tool.name}: {input_schema}")

                tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": dict(input_schema) if input_schema else {},
                        "required": input_schema.get("required", []) if input_schema else []
                    }
                })
            if actions:
                action_names = [action.value for action in actions]
                tools = [tool for tool in tools if tool["name"] in action_names]
            logger.info(f"Fetched {len(tools)} tools")
            logger.debug(f"Tool schemas: {tools}")
            return tools
        except Exception as e:
            logger.error(f"Error fetching tools: {str(e)}")
            raise ToolExecutionError(f"Failed to fetch tools: {str(e)}")

    async def execute_action(self, action: Action, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific action directly."""
        if not self.session:
            await self.connect()
        try:
            result = await self.session.call_tool(action.value, params)
            tool_result = result.structuredContent if hasattr(result,
                                                              'structuredContent') and result.structuredContent else [
                json.loads(content.text) for content in result.content if hasattr(content, 'text')
            ]
            logger.info(f"Executed action {action.value} successfully")
            return tool_result[0] if isinstance(tool_result, list) and len(tool_result) == 1 else tool_result
        except Exception as e:
            logger.error(f"Error executing action {action.value}: {str(e)}")
            raise ToolExecutionError(f"Failed to execute action: {str(e)}")

    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()
        if hasattr(self, '_session_context') and self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if hasattr(self, '_streams_context') and self._streams_context:
            await self._streams_context.__aexit__(None, None, None)
        logger.info("UnizoToolSet cleaned up")