import os

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

apikey=os.getenv("UNIZO_API_KEY")
openapi_key=os.getenv("OPENAI_API_KEY")

import asyncio
import json
from typing import Dict, Any
from langchain_core.tools import Tool
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain import hub
from unizo_langchain import UnizoLangChainToolSet
from unizo_core import Action
from pydantic import BaseModel


async def main():
    toolset = UnizoLangChainToolSet(api_key=apikey)
    await toolset.connect()
    try:
        # Fetch all available tools
        tools = await toolset.get_tools([
            Action.LIST_SERVICES,
            Action.LIST_INTEGRATIONS,
            Action.LIST_ORGANIZATIONS,
            Action.LIST_COLLECTIONS,
            Action.CONFIRM_TICKET_CREATION,
            Action.CREATE_TICKET,
            Action.LIST_TICKETS
        ])
        llm = ChatOpenAI(api_key=openapi_key)
        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a ticketing agent. Use the create_ticket tool with the exact parameters provided as a dictionary."),
            ("human", "create a ticket of jira: {params}")
        ])
        agent = create_openai_tools_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        ticket_params = {
            "integration_id": "your-integration-id",
            "organization_id": "your-organization-id",
            "collection_id": "your-collection-id",
            "ticket_name": "Fix Bug #123",
            "ticket_description": "Test ticket created via Unizo SDK",
            "ticket_status": "OPEN",
            "ticket_priority": "High",
            "ticket_type": "Task"
        }
        result = await agent_executor.ainvoke({
            "params": json.dumps(ticket_params)
        })
        print("Agent Result:", result)
    except Exception as e:
        print(f"LangChain Test Error: {str(e)}")
    finally:
        await toolset.cleanup()


if __name__ == "__main__":
    asyncio.run(main())