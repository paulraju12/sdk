import asyncio
import os


from dotenv import load_dotenv
load_dotenv()

apikey=os.getenv("UNIZO_API_KEY")
openapi_key=os.getenv("OPENAI_API_KEY")

import asyncio
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from unizo_crewai import UnizoCrewAIToolSet
from unizo_core import Action

async def main():
    toolset = UnizoCrewAIToolSet(api_key=apikey)
    await toolset.connect()
    try:
        llm = ChatOpenAI(api_key=openapi_key)
        tools = await toolset.get_tools([
            Action.LIST_SERVICES,
            Action.LIST_INTEGRATIONS,
            Action.LIST_ORGANIZATIONS,
            Action.LIST_COLLECTIONS,
            Action.CONFIRM_TICKET_CREATION,
            Action.CREATE_TICKET,
            Action.LIST_TICKETS
        ])

        agent = Agent(
            role="Ticketing Agent",
            goal="Manage tickets in Unizo ticketing system",
            backstory="You are an AI agent responsible for creating and managing tickets.",
            verbose=True,
            tools=tools,
            llm=llm
        )
        task = Task(
            description="Create a ticket in a Jira collection with these parameters: integration_id='int_123', organization_id='org_456', collection_id='col_789', ticket_name='Fix Bug #123', ticket_description='Test ticket', ticket_status='OPEN', ticket_priority='High', ticket_type='Task'",
            agent=agent,
            expected_output="Ticket creation status"
        )
        crew = Crew(agents=[agent], tasks=[task])
        result = await crew.kickoff_async()  # Use async kickoff
        print("CrewAI Result:", result)
    except Exception as e:
        print(f"CrewAI Test Error: {str(e)}")
    finally:
        await toolset.cleanup()

if __name__ == "__main__":
    asyncio.run(main())