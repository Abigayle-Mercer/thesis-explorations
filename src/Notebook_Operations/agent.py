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




# TOOLS: 

@tool("cut_cell", return_direct=True)
def cut_cell(file_path: str, id: int) -> str:
    """
    Removes a cell from the notebook at the given ID and returns the cut cell's content.
    """
    try:
        # Load notebook
        with open(file_path, "r", encoding="utf-8") as f:
            notebook = json.load(f)

        # Ensure valid cell index
        if 0 <= id < len(notebook["cells"]):
            cut_cell = notebook["cells"].pop(id)
            
            # Save updated notebook
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(notebook, f, indent=2)

            return f"✅ Cut cell {id}: {cut_cell['source']}"
        else:
            return f"❌ Invalid cell ID: {id}"

    except Exception as e:
        return f"❌ Error cutting cell: {str(e)}"


@tool("add_cell", return_direct=True)
def add_cell(file_path: str, id: int, cell_type: str = "code") -> str:
    """
    Adds a new empty cell (code or markdown) at the specified position.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            notebook = json.load(f)

        print("CELL TYPE: ", cell_type)
        # Define new cell structure
        new_cell = {
            "cell_type": cell_type,
            "metadata": {},
            "source": [],
            "outputs": [] if cell_type == "code" else None
        }

        # Ensure index is within range
        id = max(0, min(id, len(notebook["cells"])))  # Clamp ID within range
        notebook["cells"].insert(id, new_cell)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(notebook, f, indent=2)

        return f"✅ Added {cell_type} cell at position {id}."

    except Exception as e:
        return f"❌ Error adding cell: {str(e)}"


@tool("write_to_cell", return_direct=True)
def write_to_cell(file_path: str, id: int, content: str) -> str:
    """
    Writes content to a cell at a given ID.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            notebook = json.load(f)

        if 0 <= id < len(notebook["cells"]):
            notebook["cells"][id]["source"] = content.split("\n")  # Split into list for Jupyter format
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(notebook, f, indent=2)

            return f"✅ Updated cell {id} with content:\n{content}"
        else:
            return f"❌ Invalid cell ID: {id}"

    except Exception as e:
        return f"❌ Error writing to cell: {str(e)}"

@tool("read_cell", return_direct=True)
def read_cell(file_path: str, id: int) -> str:
    """
    Reads the full content of a specific cell in a notebook, including its type, execution count, metadata, outputs, and source code.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            notebook = json.load(f)

        if 0 <= id < len(notebook["cells"]):
            cell_data = notebook["cells"][id]
            return json.dumps(cell_data, indent=2)  # Return full cell as JSON-formatted string
        else:
            return f"❌ Invalid cell ID: {id}"

    except Exception as e:
        return f"❌ Error reading cell: {str(e)}"
    
    
@tool("get_max_cell_index", return_direct=True)
def get_max_cell_index(file_path: str) -> str:
    """
    Returns the total number of cells in the Jupyter notebook, allowing the agent to determine the last cell index.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            notebook = json.load(f)

        max_index = len(notebook["cells"]) - 1  # Last cell index
        return f"✅ The last cell index is {max_index}."

    except Exception as e:
        return f"❌ Error getting max cell index: {str(e)}"




@tool("read_file", return_direct=True)
def read_file(file_path: str) -> str:
    """
    Reads the entire content of a Jupyter notebook file.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            notebook = json.load(f)

        # Extract all cells as text
        cells_content = [
            f"Cell {i} ({cell['cell_type']}):\n{''.join(cell['source'])}"
            for i, cell in enumerate(notebook["cells"])
        ]

        return "\n\n".join(cells_content)

    except Exception as e:
        return f"❌ Error reading notebook: {str(e)}"



def get_directory_contents():
    """Lists all Jupyter Notebook files in the current directory."""
    try:
        files = [f for f in os.listdir() if f.endswith(".ipynb")]
        return json.dumps(files, indent=2)
    except Exception as e:
        return f"❌ Error listing files: {str(e)}"




tools = [cut_cell, add_cell, write_to_cell, read_cell, get_max_cell_index]
model = llm.bind_tools(tools)
tool_node = ToolNode(tools=tools)



from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt import ToolInvocation



def command_parser_node(state):
    """Extracts notebook file path from user input using LLM + `get_directory_contents`."""
    messages = state["messages"]

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

    print("DEBUG: notebook_editor_agent result:", result)


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

    # 🔍 Ensure last message is an AIMessage with tool_calls
    if "tool_calls" not in last_message.additional_kwargs or not last_message.additional_kwargs["tool_calls"]:
        print("❌ ERROR: No tool calls found in last AIMessage.")
        return {"messages": messages, "file_path": file_path}

    print("DEBUG: Passing messages to ToolNode:", {"messages": messages})

    # ✅ Fix: Pass only the messages list
    tool_results = tool_node.invoke({"messages": messages})  # ToolNode expects this format

    print("DEBUG: ToolNode output:", tool_results)

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


