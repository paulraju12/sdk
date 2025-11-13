import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, create_model
from langchain_core.tools import StructuredTool
from unizo_core import UnizoToolSet, Action
from unizo_core.exceptions import ToolExecutionError

logger = logging.getLogger("unizo-langchain")

class UnizoLangChainToolSet(UnizoToolSet):
    async def get_tools(self, actions: Optional[List[Action]] = None) -> List[StructuredTool]:
        """Convert MCP tools to LangChain-compatible tools."""
        tools = await super().get_tools(actions)
        langchain_tools = []
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

            async def tool_func(**params: Dict[str, Any]) -> Dict[str, Any]:
                logger.debug(f"Tool {name} called with raw params: {params}")
                # Handle JSON string input
                actual_params = params
                if "properties" in params:
                    try:
                        actual_params = json.loads(params["properties"])
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse properties: {str(e)}")
                        raise ToolExecutionError(f"Invalid JSON in properties: {str(e)}")
                logger.debug(f"Tool {name} executing with params: {actual_params}")
                # Validate against schema
                try:
                    args_schema(**actual_params)
                except Exception as e:
                    logger.error(f"Schema validation failed for {name}: {str(e)}")
                    raise ToolExecutionError(f"Invalid parameters for {name}: {str(e)}")
                return await self.execute_action(Action[name.upper()], actual_params)

            langchain_tools.append(StructuredTool.from_function(
                func=None,
                coroutine=tool_func,
                name=name,
                description=description,
                args_schema=args_schema
            ))
        logger.info(f"Converted {len(langchain_tools)} tools for LangChain")
        return langchain_tools