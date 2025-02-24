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

COMMANDS_FILE = "commands.txt"
config = {"configurable": {"thread_id": "thread-1"}}



# Memory saver for workflow
memory = MemorySaver()

class AgentState(TypedDict):
    messages: Sequence[BaseMessage]


# Load command schema from a JSON file
def load_command_schemas(file_path="command_schemas.json"):
    """Load the available command schemas from a JSON file."""
    with open(file_path, "r") as file:
        return json.load(file)


tools = []
tool_executor = ToolExecutor(tools)
functions = [format_tool_to_openai_function(t) for t in tools]
model = llm


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
        tool_input={**json.loads(last_message.additional_kwargs["function_call"]["arguments"])}
    )

    response = tool_executor.invoke(action)  # Fix typo here, should be `tool_executor`
    function_message = FunctionMessage(content=str(response), name=action.tool)
    return {"messages": messages + [function_message]}


def extract_json(state):
    """Extracts the JSON command from the agent's response."""
    messages = state["messages"]
    last_message = messages[-1].content  # Get the latest response from the agent

    print("LAST MESSAGE: ", last_message)
    # Extract JSON using regex (handles multiple formats)
    match = re.search(r'```json\n(.*?)\n```', last_message, re.DOTALL)
    if match:
        extracted_json = match.group(1)  # Capture JSON inside triple backticks
    else:
        extracted_json = last_message  # Fallback if not wrapped in ```json```

    # Try to parse the extracted JSON
    try:
        parsed_json = json.loads(extracted_json)
        print(f"Extracted JSON: {parsed_json}")
    except json.JSONDecodeError:
        print("Failed to parse JSON. Returning empty object.")
        parsed_json = {}

    return {"messages": messages + [parsed_json]}



workflow = StateGraph(AgentState)

# Define nodes
workflow.add_node("agent", agent)
workflow.add_node("action", call_tool)
workflow.add_node("extract_json", extract_json)  # New node!

# Set entry point
workflow.set_entry_point("agent")

# Conditional edges:
workflow.add_conditional_edges("agent", should_continue, {
    "continue": "action",  # If more actions needed, call tools
    "end": "extract_json"  # If response is ready, extract JSON before finishing
})

# Ensure action results are processed again by the agent
workflow.add_edge("action", "agent")

# Extract JSON before final output
workflow.add_edge("extract_json", END)

# Compile workflow
app = workflow.compile(checkpointer=memory)


# Export the workflow
def get_agent():
    return app