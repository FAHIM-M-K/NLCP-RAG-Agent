import asyncio
import json
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager 

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from langchain_core.messages import AIMessage, HumanMessage
from rag_agent import initialize_rag_agent_with_mcp

agent_executor = None
mcp_client = None

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan event handler.
    """
    global agent_executor, mcp_client
    print("FastAPI server starting up... Initializing NLCP_RAG_AGENT.")
    try:
        agent_executor, mcp_client = await initialize_rag_agent_with_mcp()
        if agent_executor and mcp_client:
            print("NLCP_RAG_AGENT initialized successfully.")
        else:
            print("Failed to initialize NLCP_RAG_AGENT. Check rag_agent.py and its dependencies for errors.")
            raise RuntimeError("Agent initialization failed. FastAPI server cannot start.")
    except Exception as e:
        print(f"CRITICAL ERROR during agent initialization in FastAPI startup: {e}")
        agent_executor = None
        mcp_client = None
        raise RuntimeError(f"FastAPI startup failed: {e}")
    
    yield

    print("FastAPI server shutting down... Closing MCP client connections.")
    if mcp_client:
        await mcp_client.close() 
        print("MCP client connections closed.")
    else:
        print("No MCP client to close during shutdown.")


app = FastAPI(
    title="NLCP RAG Agent API",
    description="API for the Wealth Management RAG Agent powered by LangChain and MCP.",
    version="1.0.0",
    lifespan=lifespan 
)

# CORS middleware
origins = [
    "http://localhost",
    "http://localhost:3000",
    "https://nlcp-rag-agent.onrender.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/query")
async def handle_agent_query_fastapi(request: Request):
    global agent_executor

    if not agent_executor:
        return JSONResponse(
            status_code=503,
            content={"error": "NLCP_RAG_AGENT is not initialized. Please check server startup logs."}
        )

    try:
        request_data = await request.json()
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid JSON format in request body."}
        )

    user_message = request_data.get("message")
    chat_history_data = request_data.get("chat_history", []) 

    if not user_message:
        return JSONResponse(
            status_code=400,
            content={"error": "No 'message' provided in the request body."}
        )

    print(f"\nReceived query from frontend: {user_message}")

    formatted_chat_history = []
    for msg_data in chat_history_data:
        msg_type = msg_data.get("type")
        msg_content = msg_data.get("content", "")
        if msg_type == "human":
            formatted_chat_history.append(HumanMessage(content=msg_content))
        elif msg_type == "ai":
            formatted_chat_history.append(AIMessage(content=msg_content))

    try:
        response = await agent_executor.ainvoke(
            {"input": user_message, "chat_history": formatted_chat_history}
        )
        
        agent_output = response.get('output', str(response))

        try:
            parsed_result = json.loads(agent_output)
            return JSONResponse(
                status_code=200,
                content={"response": parsed_result}
            )
        except json.JSONDecodeError:
            return JSONResponse(
                status_code=200,
                content={"response": agent_output}
            )

    except Exception as e:
        print(f"Error during agent execution: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"An internal server error occurred: {e}"}
        )

if __name__ == "__main__":
    if not GOOGLE_API_KEY:
        print("ERROR: GOOGLE_API_KEY not found in .env. Please set it to proceed.")
        import sys; sys.exit(1)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)