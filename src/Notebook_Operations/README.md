
# Jupyter Notebook Editor Agent

This agent processes natural language commands to edit Jupyter notebooks, utilizing LangChain and LangGraph to parse user input and execute operations such as reading, writing, adding, and deleting cells.

## Features
- **Read Cells:** Retrieve the content of any cell.
- **Write to Cells:** Modify existing cell content.
- **Add Cells:** Insert new code or markdown cells at any index.
- **Remove Cells:** Delete specific cells.
- **Fetch Notebook Metadata:** Get the number of cells to determine valid indices.

## Usage
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
2. Set up your environment:
    ```bash
    Create a .env file and add your OpenAI API key:
    OPENAI_API_KEY="your_api_key"
3. Run the agent:
    ```bash
    % python main.py

Note: When entering commands, make sure to refer to the notebook you want edited by name, the agent is capable of inferring which one you are referring to, but does need something to work off of, for example: 
- "in the test notebook there is a bug in the second cell, please fix it then remove the first cell"
- "give the lab7 notebook a markdown cell at the bottom describing the overall notebook"


Testing Questions: 
- multiple ways to evaluate correctness
- could be structural comparison, i.e. the right # of cells, order of cells, etc.
- could be logical comparison, i.e. is length = 20 the same as length = int("20")


