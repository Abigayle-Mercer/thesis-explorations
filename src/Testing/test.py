import pytest
import json
import shutil
from agent import get_agent
from collections import defaultdict

# work on a single cell
# implemetn rest of cell
# multiple cells, - context, debug
# full notebook tasks - read through all cells and add markdown descriptions
# - spell check all markdown cells
# run time issue

# non prompted tests
# take in notebook state, decide what to do - 
    # tools that drive ui

# come up with a set of high level tasks 

# repeat prompts 
# what makes prompts good or 'bad'
# fix documentation when needed 


# Paths for resetting the notebook
ORIGINAL_NOTEBOOK = "test_notebook.ipynb"
BACKUP_NOTEBOOK = "test_notebook_backup.ipynb"

# Create a backup of the original notebook before tests
shutil.copy(ORIGINAL_NOTEBOOK, BACKUP_NOTEBOOK)

# Load test cases from JSON
with open("tests.json", "r") as f:
    TEST_CASES = json.load(f)

# Initialize the agent
app = get_agent()

# Tracking precision & recall per category
category_metrics = defaultdict(lambda: {"TP": 0, "FP": 0, "FN": 0})
system_metrics = {"TP": 0, "FP": 0, "FN": 0}

@pytest.mark.parametrize("category, test_case", [
    (category, test) for category, cases in TEST_CASES.items() for test in cases
])
@pytest.mark.langsmith
def test_agent_tool_calls(category, test_case):
    """
    Runs agent on each command and evaluates precision & recall.
    """
    command = test_case["command"]
    expected_tools = set(test_case["expected_tools"])  # Convert to set

    # Run agent
    config = {"configurable": {"thread_id": "thread-1"}}
    state = {"messages": [{"role": "user", "content": command}], "file_path": ORIGINAL_NOTEBOOK}
    output_state = app.invoke(state, config)

    # Extract tools called by the agent
    messages = output_state["messages"]
    actual_tools = set()
    
    for msg in messages:
        additional_kwargs = getattr(msg, "additional_kwargs", {})
        if "tool_calls" in additional_kwargs:
            for tool_call in additional_kwargs["tool_calls"]:
                actual_tools.add(tool_call["function"]["name"])

    # Compute True Positives (TP), False Positives (FP), False Negatives (FN)
    TP = len(expected_tools & actual_tools)
    FP = len(actual_tools - expected_tools)
    FN = len(expected_tools - actual_tools)

    # Store per-category metrics
    category_metrics[category]["TP"] += TP
    category_metrics[category]["FP"] += FP
    category_metrics[category]["FN"] += FN

    # Store system-wide metrics
    system_metrics["TP"] += TP
    system_metrics["FP"] += FP
    system_metrics["FN"] += FN

    # Calculate Precision & Recall
    precision = TP / (TP + FP) if (TP + FP) > 0 else 0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0

    # Log results
    print(f"\n🔹 Category: {category}")
    print(f"🔍 Command: '{command}'")
    print(f"✅ Expected Tools: {expected_tools}")
    print(f"🚀 Actual Tools: {actual_tools}")
    print(f"📊 TP={TP}, FP={FP}, FN={FN}")
    print(f"🎯 Precision: {precision:.2f}, Recall: {recall:.2f}")

    # Assert correctness: We pass if Precision & Recall are above 0.5
    assert precision > 0.5 or recall > 0.5, f"❌ Low Precision/Recall for '{command}'"

    # Restore notebook to original state after test
    shutil.copy(BACKUP_NOTEBOOK, ORIGINAL_NOTEBOOK)

@pytest.fixture(scope="session", autouse=True)
def summarize_results():
    """
    After all tests are run, calculate and print overall precision & recall.
    """
    yield  # Ensures this runs **after** all tests complete

    print("\n🔷🔷🔷 CATEGORY-WISE PRECISION & RECALL 🔷🔷🔷")
    for category, metrics in category_metrics.items():
        TP, FP, FN = metrics["TP"], metrics["FP"], metrics["FN"]
        precision = TP / (TP + FP) if (TP + FP) > 0 else 0
        recall = TP / (TP + FN) if (TP + FN) > 0 else 0
        print(f"\n📌 {category.upper()} - Precision: {precision:.2f}, Recall: {recall:.2f}")

    print("\n🔷🔷🔷 OVERALL SYSTEM PRECISION & RECALL 🔷🔷🔷")
    TP, FP, FN = system_metrics["TP"], system_metrics["FP"], system_metrics["FN"]
    precision = TP / (TP + FP) if (TP + FP) > 0 else 0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0
    print(f"\n🚀 SYSTEM PRECISION: {precision:.2f}, SYSTEM RECALL: {recall:.2f}")

    # Ensure the final results don't have catastrophically low performance
    assert precision > 0.5 or recall > 0.5, "❌ System Precision/Recall is too low!"
