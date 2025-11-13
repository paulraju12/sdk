import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, create_model
from crewai.tools import BaseTool
from unizo_core import UnizoToolSet, Action
from unizo_core.exceptions import ToolExecutionError

logger = logging.getLogger("unizo-crewai")

class UnizoCrewAITool(BaseTool):
    """Custom CrewAI tool for Unizo actions."""
    def __init__(self, name: str, description: str, toolset: 'UnizoCrewAIToolSet', action: Action, args_schema: BaseModel):
        super().__init__(name=name, description=description, args_schema=args_schema)
        self._toolset = toolset
        self._action = action
        logger.debug(f"Created tool: {name}, {description}")

    async def _async_run(self, **params: Any) -> Dict[str, Any]:
        """Execute the tool asynchronously with timeout."""
        try:
            logger.debug(f"Tool {self.name} called with params: {params}")
            return await asyncio.wait_for(
                self._toolset.execute_action(self._action, params),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            logger.error(f"Tool {self.name} timed out")
            return {"error": f"Tool {self.name} timed out after 30 seconds"}
        except Exception as e:
            logger.error(f"Error executing tool {self.name}: {str(e)}")
            return {"error": f"Failed to execute {self.name}: {str(e)}"}

    def _run(self, **params: Any) -> Dict[str, Any]:
        """Execute the tool synchronously."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return loop.run_until_complete(self._async_run(**params))
            else:
                return asyncio.run(self._async_run(**params))
        except Exception as e:
            logger.error(f"Error in _run for tool {self.name}: {str(e)}")
            return {"error": f"Failed to execute {self.name}: {str(e)}"}

class UnizoCrewAIToolSet(UnizoToolSet):
    async def get_tools(self, actions: Optional[List[Action]] = None) -> List[BaseTool]:
        """Convert MCP tools to CrewAI-compatible tools."""
        tools = await super().get_tools(actions)
        crewai_tools = []
        for tool in tools:
            name = tool.get("name")
            description = tool.get("description", f"Execute {name}")
            schema = tool.get("parameters", {"type": "object", "properties": {}, "required": []})

            # Create fields for Pydantic model
            fields = {}
            for prop_name, prop_schema in schema.get("properties", {}).items():
                prop_type = str
                if isinstance(prop_schema, dict):
                    schema_type = prop_schema.get("type")
                    if schema_type == "integer":
                        prop_type = int
                    elif schema_type == "boolean":
                        prop_type = bool
                fields[prop_name] = (prop_type, None if prop_name not in schema.get("required", []) else ...)

            args_schema = create_model(
                f"{name}Schema",
                __config__={"arbitrary_types_allowed": True},
                **fields
            )

            crewai_tools.append(UnizoCrewAITool(
                name=name,
                description=description,
                toolset=self,
                action=Action[name.upper()],
                args_schema=args_schema
            ))
        logger.info(f"Converted {len(crewai_tools)} tools for CrewAI")
        return crewai_tools