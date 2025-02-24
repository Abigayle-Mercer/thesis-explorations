import pytest
import json
import jsonschema
from jsonschema import validate
from agent import get_agent, load_command_schemas
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage, FunctionMessage


# Load command schemas
commands = load_command_schemas("command_schemas.json")

# Map command names to their JSON schema for validation
command_schemas = {cmd["json_schema"]["properties"]["name"]["const"]: cmd["json_schema"] for cmd in commands["commands"]}

# Test cases: each contains a user prompt and the expected command
UNIT_TESTS = [
    # running the current cell
    ("Run the current cell", "notebook:run-cell"),
    ("Run this cell and move to the next", "notebook:run-cell-and-select-next")


    # cutting a cell
    ("Cut the current cell", "notebook:cut-cell"),


    # adding cells
    ("Add a cell below", "notebook:insert-cell-below"),
    ("Add a cell above", "notebook:insert-cell-above"),


    # deleting a cell
    ("Delete the current cell", "notebook:delete-cell"),


    # copy a cell
    ("Copy the current cell", "notebook:copy-cell"),


    # pasting cells
    ("Paste below", "notebook:paste-cell-below"),
    ("Paste above", "notebook:paste-cell-above"),


    # moving cells
    ("Move this cell up", "notebook:move-cell-up"),
    ("Move this cell down", "notebook:move-cell-down"),
    ("Swap this cell with the one below it", "notebook:move-cell-down"),
    ("Swap this cell with the one above it", "notebook:move-cell-up"),



    # undo and redo actions
    ("Undo the last cell action", "notebook:undo-cell-action"),
    ("Redo the last cell action", "notebook:redo-cell-action"),
    

    # running all cells
    ("Run all cells", "notebook:run-all-cells"),


    # restarting the kernal
    ("Restart the kernel", "notebook:restart-kernel"),


    # resrating the kernal and running all cells
    ("Restart the kernel and run all", "notebook:restart-run-all"),


    # making cell a markdown
    ("Make this cell markdown", "notebook:change-cell-to-markdown"),


    # merging cells
    ("Merge selected cells", "notebook:merge-cells"),
    ("Merge this cell with the one above", "notebook:merge-cell-above"),
    ("Merge this cell with the one below", "notebook:merge-cell-below"),


    # create a new notebook
    ("Create a new notebook", "notebook:create-new"),


    # selecting cells 
    ("Move up", "notebook:move-cursor-up"),
    ("Select the cell above", "notebook:move-cursor-up"),
    ("Go to the previous cell", "notebook:move-cursor-up"),
    ("Move down", "notebook:move-cursor-down"),
    ("Select the cell below", "notebook:move-cursor-down"),
    ("Go to the next cell", "notebook:move-cursor-down")
]

@pytest.mark.parametrize("user_input, expected_command", UNIT_TESTS)
def test_agent_responses(user_input, expected_command):
    """
    Test that the agent correctly maps natural language to JupyterLab commands.
    """
    # Create input messages for the agent
   

    system_message = SystemMessage(
    content=f"""You are an agent designed to take natural language prompts, infer intent, and map that intent
    to corresponding JupyterLab commands in JSON structure, following the correct execution order.

    Below is a list of valid JupyterLab commands. Each command includes:
      - A **title** (short name)
      - A **description** (what it does)
      - **Example phrases** (possible user inputs)
      - The **expected JSON structure** to execute the command

    Reference this list when constructing valid JupyterLab command responses:
    ```json
    {json.dumps(commands, indent=2)}
    ```
    Ensure that all responses strictly follow the JSON schema definitions.
    """
    )
    # Example user message
    human_message = HumanMessage(
        content=user_input
    )

   
    # Run agent
    config = {"configurable": {"thread_id": "thread-1"}}

    inputs = {"messages": [system_message, human_message]}
    app = get_agent()
    
    result = app.invoke(inputs, config)["messages"][-1]  # Extract last agent message

    # Extract JSON response
    try:
        response_json = result  # Ensure valid JSON response
    except json.JSONDecodeError:
        pytest.fail(f"Agent response is not valid JSON: {result}")

    # Check that the command name matches expected
    assert response_json.get("name") == expected_command, f"Expected {expected_command}, got {response_json.get('name')}"

    # Validate the entire response against the schema
    schema = command_schemas.get(expected_command)
    assert schema is not None, f"No schema found for command: {expected_command}"

    try:
        validate(instance=response_json, schema=schema)
    except jsonschema.exceptions.ValidationError as e:
        pytest.fail(f"Response does not conform to schema: {e}")

