import shutil
import os
import argparse
import json
import logging
from agent import run_agent_with_file
from langchain_core.messages import HumanMessage

# File paths (inside TESTS/ directory)
TEST_DIR = "TESTS"
TEST_FILE = os.path.join(TEST_DIR, "test_temp.ipynb")
EXPECTED_FILES = {
    "0": os.path.join(TEST_DIR, "test_0_key.ipynb"),
    "1": os.path.join(TEST_DIR, "test_1_key.ipynb"),  # Fixing a bug
    "2": os.path.join(TEST_DIR, "test_2_key.ipynb"),  # Adding markdown summaries
}
NUM_RUNS = 10  # Number of times to test

MESSAGES = {
    "0": "in the test notebook there is a bug in the second cell, please fix it",
    "1": "In the test notebook, there is a bug in the second cell. Please fix it.",
    "2": "Under each code cell, put a markdown cell describing what the cell does.",
}

# does a given model know to use a tool when it should and shouldn't 
# how do you make a good tool?
# name of paramter
# function signature is important
# 
# agent to put a markdown description above each code cell
# add doc string to all funcs and classes

def ensure_test_dir():
    """Ensures the TESTS directory exists."""
    os.makedirs(TEST_DIR, exist_ok=True)


def create_temp(test_case):
    """Creates TEMP_FILE as a copy of the test-specific input file."""
    test_input = os.path.join(TEST_DIR, f"test_{test_case}.ipynb")
    shutil.copy(test_input, TEST_FILE)


def run(user_input):
    """Runs the agent on TEST_FILE."""
    config = {"configurable": {"thread_id": "thread-1"}}
    run_agent_with_file(user_input, config, TEST_FILE)


def load_notebook(file_path):
    """Loads a Jupyter notebook from a file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def compare_cells(cell1, cell2):
    """Compares two cells, ignoring leading/trailing whitespace in each line."""
    source1 = [line.strip() for line in cell1.get("source", [])]
    source2 = [line.strip() for line in cell2.get("source", [])]
    return source1 == source2


def correctness(test_case):
    """Compares the generated notebook with the expected output."""
    temp_nb = load_notebook(TEST_FILE)
    expected_nb = load_notebook(EXPECTED_FILES[test_case])

    temp_cells = temp_nb.get("cells", [])
    expected_cells = expected_nb.get("cells", [])

    if len(temp_cells) != len(expected_cells):
        logging.error(f"❌ Mismatch in number of cells! {len(temp_cells)} vs {len(expected_cells)}")
        return False

    if test_case == "2":
        return check_markdown_below_code(temp_cells)
    
    # Default check (strict equality for function repair tests)
    for i, (temp_cell, expected_cell) in enumerate(zip(temp_cells, expected_cells)):
        if not compare_cells(temp_cell, expected_cell):
            logging.error(f"❌ Cell {i} does not match!")
            return False

    logging.info("✅ All cells match!")
    return True


def check_markdown_below_code(cells):
    """Ensures each code cell has a markdown cell directly below it."""
    for i in range(len(cells) - 1):
        if cells[i]["cell_type"] == "code" and cells[i + 1]["cell_type"] != "markdown":
            logging.error(f"❌ Code cell at index {i} does not have a markdown cell below it!")
            return False

    logging.info("✅ Markdown descriptions are correctly placed below code cells.")
    return True


def delete_temp():
    """Deletes TEST_FILE after all tests are done."""
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)


def main():
    parser = argparse.ArgumentParser(description="Run notebook tests.")
    parser.add_argument("test_case", choices=["0", "1", "2"], help="Select the test case to run.")
    args = parser.parse_args()

    ensure_test_dir()
    create_temp(args.test_case)

    success_count = 0

    for i in range(NUM_RUNS):
        print(f"🔄 Running test {i+1}/{NUM_RUNS}...")

        # Run the agent with the selected test case
        run(MESSAGES[args.test_case])

        # Check correctness
        if correctness(args.test_case):
            print("✅ Test PASSED")
            success_count += 1
        else:
            print("❌ Test FAILED")

        # Reset the temp file for the next run
        create_temp(args.test_case)

    # Delete TEMP_FILE after all tests are done
    delete_temp()

    # Print final success rate
    print(f"\n🎯 Success Rate: {success_count}/{NUM_RUNS} ({(success_count / NUM_RUNS) * 100:.2f}%)")


if __name__ == "__main__":
    main()
