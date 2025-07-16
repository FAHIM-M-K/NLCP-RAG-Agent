import os
import asyncio
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage 


from langchain_mcp_adapters.client import MultiServerMCPClient
from mcp.client.stdio import StdioServerParameters 

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set.")

async def initialize_rag_agent_with_mcp():
    """
    Initializes and returns a LangChain AgentExecutor configured with
    Google Gemini and tools loaded from MCP Servers.
    """
    # 1. initialize llm (gemini)
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.0)
    
    print("Connecting to MCP servers and loading tools...")
    # mcp_client = MultiServerMCPClient(
    #     {
    #         # DIRECTLY define the server configurations as dictionaries here:
    #         "mongodb": {
    #             "transport": "stdio",
    #             "command": "python",
    #             "args": ["mongodb_tools.py"]
    #         },
    #         "mysql": {
    #             "transport": "stdio",
    #             "command": "python",
    #             "args": ["mysql_tools.py"]
    #         }
    #     }
    # )


    #modified----------
    mcp_client = MultiServerMCPClient(
        { 
            "mongodb": StdioServerParameters( 
                name="mongodb", 
                command="python",
                args=["mongodb_tools.py"],
                env=os.environ.copy()
            ),
            "mysql": StdioServerParameters( 
                name="mysql", 
                command="python",
                args=["mysql_tools.py"],
                env=os.environ.copy()
            )
        }
    )

    #-------------

    # 3. load tools from mcp clients
    tools = await mcp_client.get_tools() 
    print(f"Successfully loaded {len(tools)} tools from MCP servers.")

    # print tool names
    for tool_obj in tools:
        print(f"- {tool_obj.name}")


    #4 prompt template for agent
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", """
            You are a sophisticated Financial Data Analyst AI named NLCP_RAG_AGENT.
            Your primary role is to assist users by querying internal financial databases
            (MongoDB for client profiles, MySQL for transaction data).

            When a user asks a question, determine which tool(s) are necessary.
            If a query requires information from one database (e.g., MySQL) and then details from another (e.g., MongoDB),
            you MUST perform the database lookups sequentially. For example, if you get a client_id from a MySQL query,
            you can then use a MongoDB tool like `get_client_profile_by_id` to retrieve their name or other profile details.
            Carefully consider the arguments required by each tool and extract them precisely from the user's query or from the output of a previous tool.
            If you need a client's profile by their ID, use `get_client_profile_by_id`.

            Always try to provide a concise and helpful answer based on the tool outputs.
            If a tool returns no data or an error, inform the user clearly.
            If a date range is requested for transactions, ensure the dates are in YYYY-MM-DD format.
            """),
            MessagesPlaceholder(variable_name="chat_history"), # For conversational memory
            ("human", "{input}"), # User's current input
            MessagesPlaceholder(variable_name="agent_scratchpad"), # Agent's internal thoughts and tool outputs
        ]
    )

    #5 creating the langchain agent
    agent = create_tool_calling_agent(llm, tools, prompt)

    #6 agent executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True, 
        handle_parsing_errors=True
    )

    return agent_executor, mcp_client # Return both for use in api_server.py

# if __name__ == "__main__":
#     asyncio.run(main())