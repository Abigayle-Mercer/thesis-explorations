
from typing import Literal
from typing_extensions import TypedDict
from langgraph.types import Command
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt.tool_executor import ToolExecutor
from langchain_community.chat_models import ChatOpenAI
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
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
def cut_cell(input: str, file_path: str, id: int) -> str:
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
def add_cell(input: str, file_path: str, id: int, cell_type: str = "code") -> str:
    """
    Adds a new empty cell (code or markdown) at the specified position.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            notebook = json.load(f)

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
def write_to_cell(input: str, file_path: str, id: int, content: str) -> str:
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
def read_cell(input: str, file_path: str, id: int) -> str:
    """
    Reads the content of a specific cell in a notebook.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            notebook = json.load(f)

        if 0 <= id < len(notebook["cells"]):
            return f"📖 Cell {id} content:\n{''.join(notebook['cells'][id]['source'])}"
        else:
            return f"❌ Invalid cell ID: {id}"

    except Exception as e:
        return f"❌ Error reading cell: {str(e)}"


@tool("read_file", return_direct=True)
def read_file(input: str, file_path: str) -> str:
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


tools = [cut_cell, add_cell, write_to_cell, read_cell]
tool_executor = ToolExecutor(tools)


notebook_editor_llm = llm.with_config({"system": "You are a Jupyter notebook editing agent. Perform operations on the notebook based on user instructions."})

notebook_editor_agent = create_react_agent(
    notebook_editor_llm, 
    tools=tools
)




def supervisor_node(state: State) -> Command[Literal["command_parser", "notebook_editor", "__end__"]]:
    """Decides the next step based on whether the file path is set and operations are completed."""
    messages = state["messages"]
    file_path = state.get("file_path", None)
    last_message = messages[-1].content.lower()

    # 1️⃣ If file_path is missing, we need to determine the correct notebook file
    if not file_path:
        return Command(goto="command_parser")

    # 2️⃣ If file_path is set but we're not done, proceed to notebook editing
    if "✅" not in last_message and "error" not in last_message:
        return Command(goto="notebook_editor")

    # 3️⃣ If the last message contains a ✅ (indicating a successful operation), we finish
    return Command(goto=END)





def command_parser_node(state: State) -> Command[Literal["supervisor"]]:
    """Extracts notebook file path from user input using LLM + `get_directory_contents`."""
    messages = state["messages"]

    dir_response = get_directory_contents()
    possible_files = json.loads(dir_response)  # Convert JSON response to list

    # ✅ If successful, ask LLM to determine the notebook file
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
    parsed_file = response.content.strip().replace('"', '')  # Ensure clean file name

    if parsed_file == "unknown":
        return Command(
            update={"messages": messages + [HumanMessage(content="❌ No file match found. Please specify.")]},
            goto="supervisor",
        )

    print(parsed_file)  # Debugging: See what file was detected
    return Command(
        update={"messages": messages + [HumanMessage(content=f"📁 Detected notebook: {parsed_file}")], "file_path": parsed_file},
        goto="supervisor",
    )




def notebook_editor_node(state: State) -> Command[Literal["supervisor"]]:
    """Executes notebook editing tasks, allowing LLM to call multiple tools before returning to supervisor."""
    messages = state["messages"]
    file_path = state["file_path"]  # Ensure the agent has access to the notebook path

    # 🔥 Inject the file_path into the conversation so the LLM **always knows it**
    system_message = HumanMessage(content=f"📁 You are editing notebook: {file_path}. Use the correct tools accordingly.")

    # 🚀 Let the LLM internally decide which tools to call
    result = notebook_editor_agent.invoke({"messages": messages + [system_message]})


    return Command(
        update={
            "messages": [
                HumanMessage(content=result["messages"][-1].content, name="notebook_editor")
            ],
            "file_path": file_path
        },
        goto="supervisor",
    )


builder = StateGraph(State)
builder.add_edge(START, "supervisor")
builder.add_node("supervisor", supervisor_node)
builder.add_node("command_parser", command_parser_node)
builder.add_node("notebook_editor", notebook_editor_node)  # Ensure consistency
graph = builder.compile(checkpointer=memory)


def run_agent(user_input):
    state = {"messages": [HumanMessage(content=user_input)], "file_path": ""}
    return graph.invoke(state)