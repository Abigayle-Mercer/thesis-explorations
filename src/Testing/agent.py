from typing_extensions import TypedDict
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolInvocation
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, FunctionMessage
from langgraph.checkpoint.memory import MemorySaver
from langchain_community.chat_models import ChatOpenAI
from langchain_community.tools import format_tool_to_openai_function
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode 
from dotenv import load_dotenv
import os
import json

# Import tools
from tools.tools_2 import delete_cell, add_cell, write_to_cell, read_cell, cell_count, read_notebook



load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = api_key

# Set up LLM
llm = ChatOpenAI(api_key=api_key, model="gpt-4-turbo", temperature=0)

### === Define State === ###
class State(TypedDict):
    messages: list
    file_path: str

memory = MemorySaver()




def get_directory_contents():
    """Lists all Jupyter Notebook files in the current directory."""
    try:
        files = [f for f in os.listdir() if f.endswith(".ipynb")]
        return json.dumps(files, indent=2)
    except Exception as e:
        return f"❌ Error listing files: {str(e)}"




tools = [delete_cell, add_cell, write_to_cell, read_cell, cell_count, read_notebook]
model = llm.bind_tools(tools)
tool_node = ToolNode(tools=tools)



from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt import ToolInvocation



def command_parser_node(state):
    """Extracts notebook file path from user input using LLM + `get_directory_contents`."""
    messages = state["messages"]
    file_path = state["file_path"]

    if file_path != "": 
        return {"messages": messages + [HumanMessage(content=f"📁 You are editing notebook: {file_path}. Always include `file_path` in tool calls")], "file_path": file_path}


    # 🔍 Get list of available notebooks
    dir_response = get_directory_contents()
    possible_files = json.loads(dir_response)  

    # ✅ LLM determines which file the user referred to
    prompt = f"""
    You are an AI that maps a user command to the correct Jupyter Notebook file.

    Available notebooks:
    {json.dumps(possible_files, indent=2)}

    User command:
    "{messages[-1].content}"

    Based on the user's intent, pick the **most likely** file name and respond with only the file name.
    If no match is found, respond with "unknown".
    """

    response = llm.invoke([HumanMessage(content=prompt)])
    parsed_file = response.content.strip().replace('"', '')  

    if parsed_file == "unknown":
        return {"messages": messages + [HumanMessage(content="❌ No file match found. Please specify.")], "file_path": ""}

    print(f"✅ Detected Notebook: {parsed_file}")
    return {"messages": messages + [HumanMessage(content=f"📁 You are editing notebook: {parsed_file}. Always include `file_path` in tool calls")], "file_path": parsed_file}

    


def notebook_editor_node(state):
    """Executes notebook editing tasks and delegates decision-making to `should_continue`."""
    messages = state["messages"]
    file_path = state["file_path"]

    # 🔥 Inject the file_path so the LLM **always knows it**

    # 🚀 Let the LLM decide what needs to be done
    result = model.invoke(messages)


    return {"messages": messages + [result], "file_path": file_path}  # Append latest LLM response
        


def should_continue(state):
    """Determines if there are pending tool calls."""
    last_message = state["messages"][-1]

    # Check if 'tool_calls' exist in the last message (for bind_tools)
    if "tool_calls" in last_message.additional_kwargs and last_message.additional_kwargs["tool_calls"]:
        return "continue"  # Proceed to tool execution

    return "end"  # No more tool calls, end execution



def call_tool(state):
    """Executes tool calls using ToolNode correctly."""
    messages = state["messages"]
    file_path = state["file_path"]

    # 🔍 Ensure last message exists
    if not messages:
        print("❌ ERROR: No messages found in state.")
        return {"messages": messages, "file_path": file_path}

    last_message = messages[-1]
    print("CALLING TOOL: ", last_message.additional_kwargs["tool_calls"][0]["function"])

    # 🔍 Ensure last message is an AIMessage with tool_calls
    if "tool_calls" not in last_message.additional_kwargs or not last_message.additional_kwargs["tool_calls"]:
        print("❌ ERROR: No tool calls found in last AIMessage.")
        return {"messages": messages, "file_path": file_path}


    # ✅ Fix: Pass only the messages list
    tool_results = tool_node.invoke({"messages": messages})  # ToolNode expects this format

    # 🔥 Fix: Ensure tool_results is a list of messages
    if isinstance(tool_results, dict):  
        tool_results = tool_results.get("messages", [])

    # ✅ Append results to messages and return updated state
    return {"messages": messages + tool_results, "file_path": file_path}




# 🔧 Construct the Graph
builder = StateGraph(State)

# nodes: 
builder.add_node("notebook_editor", notebook_editor_node)
builder.add_node("command_parser", command_parser_node)
builder.add_node("call_tool", call_tool)


# 1️⃣ Start by parsing the command
builder.add_edge(START, "command_parser")

# 2️⃣ Notebook editor processes commands
builder.add_edge("command_parser", "notebook_editor")

# 3️⃣ Decide whether to continue or stop
builder.add_conditional_edges("notebook_editor", should_continue, {"continue": "call_tool", "end": END})  # ✅ Proper conditional routing

# 4️⃣ Execute tools when needed
builder.add_edge("call_tool", "notebook_editor")  # Return to editor after tool call

# 5️⃣ End condition (already handled in conditional)

graph = builder.compile(checkpointer=memory)



def get_agent(): 
    return graph



def run_agent(user_input, config):
    """Runs the agent with an educational system message included."""
    
    # 📖 Education message about indexing
    system_message = HumanMessage(
        content=(
            "You are a notebook editing agent. Take in a natural a langeuage command "
            "and infer meaning to operate on the notebook using your available tools "
            "Note: When referring to notebook cells, terms like 'first cell' always means index 0. "
            "Or 'eleventh cell' actualy means cell at index 10 "
            "However, 'cell at index 1' explicitly refers to index 1. "
            "Ensure all operations correctly interpret these references."
        )
    )

    # 🚀 Inject the system message before user input
    state = {"messages": [system_message, HumanMessage(content=user_input)], "file_path": ""}
    
    return graph.invoke(state, config)


def run_agent_with_file(user_input, config, file_path):
    """Runs the agent with an educational system message included."""
    
    # 📖 Education message about indexing
    system_message = HumanMessage(
        content=(
            "You are a notebook editing agent. Take in a natural a langeuage command "
            "and infer meaning to operate on the notebook using your available tools "
            "Note: When referring to notebook cells, terms like 'first cell' always means index 0. "
            "Or 'eleventh cell' actualy means cell at index 10 "
            "However, 'cell at index 1' explicitly refers to index 1. "
            "Ensure all operations correctly interpret these references."
        )
    )

    # 🚀 Inject the system message before user input
    state = {"messages": [system_message, HumanMessage(content=user_input)], "file_path": file_path}
    
    return graph.invoke(state, config)
