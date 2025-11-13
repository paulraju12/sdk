import json
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from unizo_core import UnizoToolSet, Action
from unizo_core.exceptions import ToolExecutionError

logger = logging.getLogger("unizo-openai")

class UnizoOpenAIToolSet(UnizoToolSet):
    def __init__(self, api_key: str, openai_api_key: str, server_url: str = "http://api.unizo.ai/mcp/ticketing"):
        super().__init__(api_key, server_url)
        self.openai = AsyncOpenAI(api_key=openai_api_key)

    async def get_tools(self, actions: Optional[List[Action]] = None) -> List[Dict[str, Any]]:
        """Convert MCP tools to OpenAI-compatible function schemas."""
        tools = await super().get_tools(actions)
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.get("name"),
                    "description": tool.get("description", f"Execute {tool.get('name')}"),
                    "parameters": tool.get("parameters", {"type": "object", "properties": {}})
                }
            }
            for tool in tools
        ]
        logger.info(f"Converted {len(openai_tools)} tools for OpenAI")
        return openai_tools

    async def process_query(self, query: str, previous_messages: List[Dict[str, Any]] = None, model: str = "gpt-4o") -> tuple[str, List[Dict[str, Any]]]:
        """Process a query using OpenAI with tool calling."""
        if not self.session:
            await self.connect()
        messages = previous_messages.copy() if previous_messages else []
        messages.append({"role": "user", "content": query})
        tools = await self.get_tools()

        try:
            response = await self.openai.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=1000
            )
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise ToolExecutionError(f"OpenAI API error: {str(e)}")

        final_text = []
        choice = response.choices[0]
        if choice.message.content:
            final_text.append(choice.message.content)
            messages.append({"role": "assistant", "content": choice.message.content})

        if choice.message.tool_calls:
            tool_calls = []
            for tool_call in choice.message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                try:
                    result = await self.execute_action(Action[tool_name.upper()], tool_args)
                    final_text.append(f"[Tool {tool_name} result: {result}]")
                    tool_calls.append({
                        "id": tool_call.id,
                        "type": "function",
                        "function": {"name": tool_name, "arguments": json.dumps(tool_args)}
                    })
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": tool_calls
                    })
                    messages.append({
                        "role": "tool",
                        "content": json.dumps(result),
                        "tool_call_id": tool_call.id
                    })
                except Exception as e:
                    logger.error(f"Tool call error for {tool_name}: {e}")
                    final_text.append(f"[Error calling tool {tool_name}: {str(e)}]")
                    continue

                # Follow-up call
                try:
                    next_response = await self.openai.chat.completions.create(
                        model=model,
                        messages=messages,
                        tools=tools,
                        tool_choice="auto",
                        max_tokens=1000
                    )
                    next_content = next_response.choices[0].message.content
                    if next_content:
                        final_text.append(next_content)
                        messages.append({"role": "assistant", "content": next_content})
                except Exception as e:
                    logger.error(f"OpenAI follow-up API error: {e}")
                    final_text.append(f"[Error in follow-up response: {str(e)}]")

        return "\n".join(final_text), messages