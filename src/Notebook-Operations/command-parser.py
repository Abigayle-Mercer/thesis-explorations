# an agent to parse commands to and call the notebook editing agent 
"""
    extract: 
    - notebook path
    - natural language command

    tools: 
    - get current directory file names
    
    # goal: 
    - figure out the name of the file the command is referring to, and the command
"""


from dotenv import load_dotenv
from langchain.tools import BaseTool, Tool, tool
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage, FunctionMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt.tool_executor import ToolExecutor
from langgraph.prebuilt import ToolInvocation
from typing import TypedDict, Sequence
from langchain_community.chat_models import ChatOpenAI
from langchain_community.tools import format_tool_to_openai_function
from langchain_openai import ChatOpenAI
import re

import json

import os

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = api_key

# Set up LLM
llm = ChatOpenAI(api_key=api_key, model="gpt-4", temperature=0, streaming=True)

# Memory saver for workflow
memory = MemorySaver()

class AgentState(TypedDict):
    messages: Sequence[BaseMessage]



# Define Tools

@tool("get-directory-contents", return_direct=True)
def get_directory_contents(input: str) -> str:
    """Returns a list of files in the current directory."""
    return json.dumps(os.listdir("."))  # Returns a JSON string of file names



# Setup agent
tools = []
tool_executor = ToolExecutor(tools)
functions = [format_tool_to_openai_function(t) for t in tools]
model = llm.bind_functions(functions)

def agent(state):
    messages = state["messages"]
    response = model.invoke(messages)
    return {"messages": messages + [response]}


def should_continue(state):
    last_message = state["messages"][-1]
    return "continue" if "function_call" in last_message.additional_kwargs else "end"

def call_tool(state):
    messages = state["messages"]
    last_message = messages[-1]


    action = ToolInvocation(
        tool=last_message.additional_kwargs["function_call"]["name"],
        tool_input={**json.loads(last_message.additional_kwargs["function_call"]["arguments"])} # need to figure out this workflow
    )

    response = tool_executor.invoke(action)  # Fix typo here, should be `tool_executor`
    function_message = FunctionMessage(content=str(response), name=action.tool)
    return {"messages": messages + [function_message]}


# Build workflow
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent)
workflow.add_node("action", call_tool)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"continue": "action", "end": END})
workflow.add_edge("action", "agent")
app = workflow.compile(checkpointer=memory)

# Export the workflow
def get_agent():
    return app
