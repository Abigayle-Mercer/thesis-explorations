import sys
from langchain_core.messages import HumanMessage
from agent import run_agent

print("Hello! Welcome to the Notebook Editor Experience 🎉")
print("Type commands into the terminal to edit notebooks in the current directory.")
print("Type 'exit' to quit.")


while True:
    # 🔹 Get user input
    user_input = input("> ").strip()

    # 🔺 Exit condition
    if user_input.lower() in ["exit", "quit"]:
        print("Goodbye! 👋")
        sys.exit(0)

    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "file_path": None,  # Initially, file_path is unknown
    }

    config = {"configurable": {"thread_id": "thread-1"}}

    # 🚀 Process user command step by step
    for step in graph.stream(initial_state, config, subgraphs=True):
        # Pretty-print each step (optional)
        print(step)
        print("----")

    print("✅ Success")  # Notify user when the task is complete