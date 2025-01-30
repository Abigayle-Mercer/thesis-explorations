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
    file_path: str

# Define tools
@tool("previous_cell", return_direct=True)
def previous_cell(input: str, file_path: str) -> str:
    """Fetch the content of the previous cell given its index. 
    This can potentially help provide more context to write the body of the function"""
    try:
        idx = int(input)
        with open(file_path, "r") as f:
            notebook_data = json.load(f)
            cells = notebook_data.get("cells", [])
            if 0 <= idx < len(cells) and cells[idx]["cell_type"] == "code":
                return "".join(cells[idx]["source"]).strip()
            return "No code found or invalid index."
    except Exception as e:
        return f"Error fetching previous cell: {str(e)}"


        
@tool("check_for_unwritten_function", return_direct=True)
def check_for_unwritten_function(code: str, file_path: str):
    """
    Given the code from a cell, determine if there are any function definitions whose body still 
    needs to be written in that cell, return their names if there are any.
    """
    unwritten_functions = []
    error = None

    # Split the code by newlines and analyze each line
    lines = code.split("\n")

    # Regex to match function definitions
    func_pattern = re.compile(r"def (\w+)\s?\(")

    for idx, line in enumerate(lines):
        match = func_pattern.match(line.strip())
        if match:
            func_name = match.group(1)
            # Check the next lines for the body of the function
            body_lines = lines[idx + 1:]  # Body starts from the next line after "def"
            
            # Identify the body of the function
            body = ""
            for body_line in body_lines:
                body += body_line.strip() + "\n"
            
            # Check the function body for unwritten elements: 'pass', comment-only, or empty
            if 'pass' in body.strip() or all(line.lstrip().startswith('#') for line in body_lines):
                unwritten_functions.append(func_name)

    result = {
        "unwritten_functions": unwritten_functions,
        "error": error
    }

    return json.dumps(result)


@tool("find_function_calls", return_direct=True)
def find_function_calls(input: str, file_path: str) -> str:
    """Finds all cells in the notebook where the unwritten function is called. Returns a list of cell content."""
    try:
        func_name = input
        with open(file_path, "r") as f:
            notebook_data = json.load(f)
            cells = notebook_data.get("cells", [])
            return json.dumps(
                [
                    "".join(cell["source"])
                    for cell in cells
                    if cell["cell_type"] == "code" and func_name in "".join(cell["source"])
                ]
            )
    except Exception as e:
        return f"Error searching for function calls: {str(e)}"


# Setup agent
tools = [previous_cell, check_for_unwritten_function, find_function_calls]
tool_executor = ToolExecutor(tools)
functions = [format_tool_to_openai_function(t) for t in tools]
model = llm.bind_functions(functions)

def agent(state):
    messages = state["messages"]
    file_path = state["file_path"]  # Ensure file path is included in state
    response = model.invoke(messages)
    return {"messages": messages + [response], "file_path": file_path}


def should_continue(state):
    last_message = state["messages"][-1]
    return "continue" if "function_call" in last_message.additional_kwargs else "end"

def call_tool(state):
    messages = state["messages"]
    last_message = messages[-1]
    file_path = state["file_path"]

    action = ToolInvocation(
        tool=last_message.additional_kwargs["function_call"]["name"],
        tool_input={**json.loads(last_message.additional_kwargs["function_call"]["arguments"]), "file_path": file_path}
    )

    response = tool_executor.invoke(action)  # Fix typo here, should be `tool_executor`
    function_message = FunctionMessage(content=str(response), name=action.tool)
    return {"messages": messages + [function_message], "file_path": file_path}

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
