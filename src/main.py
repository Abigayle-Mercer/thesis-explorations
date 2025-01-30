import argparse
from test_environment import ExecuteNotebook


def main():
    parser = argparse.ArgumentParser(description="Execute and evaluate Jupyter notebooks")
    parser.add_argument("notebook_path", type=str, help="Path to the input notebook")
    args = parser.parse_args()

    executor = ExecuteNotebook(args.notebook_path)
    executor.test_agent()  # Replace with your actual agent function

if __name__ == "__main__":
    main()