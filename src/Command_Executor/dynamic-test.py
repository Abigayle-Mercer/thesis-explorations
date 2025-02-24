import pytest
import json
import jsonschema
from jsonschema import validate
from agent import get_agent, load_command_schemas
from langchain_core.messages import SystemMessage, HumanMessage
import os

# Load command schemas
commands = load_command_schemas("command_schemas.json")

# Map command names to their JSON schema for validation
command_schemas = {
    cmd["json_schema"]["properties"]["name"]["const"]: cmd["json_schema"]
    for cmd in commands["commands"]
}

# Define dynamic test cases where multiple commands should be executed in sequence
DYNAMIC_TESTS = [
    (
        "Run the cell above this",
        [
            {"name": "notebook:move-cursor-up", "args": {}},
            {"name": "notebook:run-cell", "args": {"activate": True}},
        ],
    ),
    (
        "Run the cell 2 cells above this",
        [
            {"name": "notebook:move-cursor-up", "args": {}},
            {"name": "notebook:move-cursor-up", "args": {}},
            {"name": "notebook:run-cell", "args": {"activate": True}},
        ],
    ),
    (
        "Run the cell 3 cells above this",
        [
            {"name": "notebook:move-cursor-up", "args": {}},
            {"name": "notebook:move-cursor-up", "args": {}},
            {"name": "notebook:move-cursor-up", "args": {}},
            {"name": "notebook:run-cell", "args": {"activate": True}},
        ],
    ),
    (
        "Insert a markdown cell above and start editing",
        [
            {"name": "notebook:insert-cell-above", "args": {"activate": True, "toolbar": False}},
            {"name": "notebook:change-cell-to-markdown", "args": {"activate": True}},
            {"name": "notebook:enter-edit-mode", "args": {"activate": True}},
        ],
    ),
    (
        "run this cell and the next",
        [
            {"name": "notebook:run-cell-and-select-next", "args": {"activate": True}},
            {"name": "notebook:run-cell-and-select-next", "args": {"activate": True}},
        ],
    ),
    (
        "Delete this cell and the next",
        [
            {"name": "notebook:delete-cell", "args": {}},  # Deletes the first cell
            {"name": "notebook:delete-cell", "args": {}},  # Deletes the next cell (already selected)
        ],
    )
]

LOG_FILE = "test_results.log"


@pytest.mark.parametrize("user_input, expected_commands", DYNAMIC_TESTS)
def test_dynamic_agent_responses(user_input, expected_commands):
    """
    Test that the agent correctly maps complex natural language instructions into multiple JupyterLab commands.
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

    # User message
    human_message = HumanMessage(content=user_input)

    # Run agent
    config = {"configurable": {"thread_id": "thread-1"}}
    inputs = {"messages": [system_message, human_message]}
    app = get_agent()

    # Extract last agent message
    messages = app.invoke(inputs, config)["messages"]
    result = messages[-1]  # Last message from agent

    test_passed = True  # Assume success

    print(f"\nTEST INPUT: {user_input}")
    print(f"EXPECTED COMMANDS: {json.dumps(expected_commands, indent=2)}")
    print(f"AGENT RESPONSE: {result}\n")

    # **1. Ensure response is in correct format**
    if isinstance(result, dict):
        result = [result]  # Convert single command to list
    elif not isinstance(result, list):
        print(f"❌ Unexpected response type: {type(result)}")
        print(f"   Expected: List of commands or a single command")
        print(f"   Received: {result}\n")
        
        # **Log this as a failure**
        _write_to_log({
            "input": user_input,
            "expected": expected_commands,
            "received": result,
            "status": "FAIL",
            "error": "Unexpected response format"
        })
        return  # Exit test gracefully

    # **2. Ensure response is not empty**
    if not result or result == [{}]:
        print(f"❌ Empty or malformed response from agent.")
        print(f"   Received: {result}\n")

        # **Log failure with last agent message**
        _write_to_log({
            "input": user_input,
            "expected": expected_commands,
            "received": result,
            "status": "FAIL",
            "error": "Agent returned an empty response",
            "last_message": messages[-2] if len(messages) > 1 else "N/A"
        })
        return  # Exit test gracefully

    # **3. Ensure correct number of commands**
    if len(result) != len(expected_commands):
        print(f"⚠️ Warning: Expected {len(expected_commands)} commands, but got {len(result)}")
        print(f"   Expected: {expected_commands}")
        print(f"   Received: {result}\n")
        test_passed = False

    # **4. Validate each command against the expected schema**
    for i, (actual_command, expected_command) in enumerate(zip(result, expected_commands)):
        if "name" not in actual_command:
            print(f"❌ Missing 'name' key in command: {actual_command}")
            test_passed = False
            continue  # Skip further validation

        if actual_command["name"] != expected_command["name"]:
            print(f"⚠️ Step {i+1}: Expected command {expected_command['name']}, but got {actual_command['name']}")
            test_passed = False

        schema = command_schemas.get(expected_command["name"])
        if not schema:
            print(f"❌ No schema found for command: {expected_command['name']}")
            test_passed = False
            continue  # Skip validation if schema is missing
            
        try:
            validate(instance=actual_command, schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            print(f"❌ Schema validation failed for step {i+1}: {e}")
            test_passed = False

    # **5. Log Results**
    log_entry = {
        "input": user_input,
        "expected": expected_commands,
        "received": result,
        "status": "PASS" if test_passed else "FAIL",
    }

    _write_to_log(log_entry)

    # **6. Print Summary**
    if not test_passed:
        pytest.fail(f"Test failed for input: '{user_input}'")


def _write_to_log(log_entry):
    """Helper function to append test results to a structured JSON file."""
    
    LOG_FILE = "test_results.json"

    # Load existing logs if the file exists
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                logs = json.load(f)
        except json.JSONDecodeError:
            logs = []  # If file is corrupted, reset it
    else:
        logs = []  # If file doesn't exist, start fresh

    # Append the new log entry
    logs.append(log_entry)

    # Write back all logs in a proper JSON array
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)
