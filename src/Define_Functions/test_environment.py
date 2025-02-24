import nbformat
import itertools
import os
import subprocess
import glob
from agent import get_agent
import json
import re
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage, FunctionMessage

from nbclient import NotebookClient, execute

class ModifyNotebook:
    def __init__(self, notebook_path):
        self.notebook_path = notebook_path
        self.output_dir = "../test_data/modify_notebooks/"
        os.makedirs(self.output_dir, exist_ok=True)

    def parse_notebook(self):
        """ Reads a Jupyter Notebook and extracts code cells. """
        with open(self.notebook_path, "r", encoding="utf-8") as f:
            self.nb = nbformat.read(f, as_version=4)
        self.code_cells = [cell for cell in self.nb.cells if cell.cell_type == "code"]
    
    def get_functions(self):
        """ Extract function definitions from code cells, ignoring test cases. """
        # Ensure notebook is parsed before accessing code_cells
        if not hasattr(self, 'code_cells'):
            self.parse_notebook()
        
        self.functions = {}  # {function_name: (cell_index, function_code)}
        for i, cell in enumerate(self.code_cells):
            lines = cell.source.split("\n")
            inside_test_class = False
            for j, line in enumerate(lines):
                if line.strip().startswith("class Test"):  # Detects test class
                    inside_test_class = True
                if inside_test_class and line.strip() == "":
                    inside_test_class = False  # Stop ignoring functions outside test class
                if line.strip().startswith("def ") and not inside_test_class:  
                    func_name = line.split("(")[0].replace("def ", "").strip()
                    self.functions[func_name] = (i, j)  # Store function location
        return len(self.functions)  # Return function count

    def remove_function_body(self, level):
        """ Create modified notebooks by removing function bodies based on level. """
        self.parse_notebook()
        num_functions = self.get_functions()
        
        if num_functions == 0:
            print("No functions found to modify.")
            return
        
        all_functions = list(self.functions.keys())

        # Generate all possible function removal combinations at this level
        for funcs_to_remove in itertools.combinations(all_functions, level):
            modified_nb = nbformat.from_dict(self.nb)  # Copy notebook structure

            for func in funcs_to_remove:
                cell_idx, line_idx = self.functions[func]
                cell = modified_nb.cells[cell_idx]

                lines = cell.source.split("\n")
                if "pass" in lines[line_idx]:  # Function already empty
                    continue
                
                # Replace function body with `pass`
                for k in range(line_idx + 1, len(lines)):
                    if not lines[k].startswith(" "):  # End of function body
                        break
                    lines[k] = "    pass" if k == line_idx + 1 else ""  # Replace first line with `pass`
                
                modified_nb.cells[cell_idx].source = "\n".join(lines)
            
            # Save modified notebook
            filename = f"level_{level}_remove_{'_'.join(funcs_to_remove)}.ipynb"
            output_path = os.path.join(self.output_dir, filename)
            with open(output_path, "w", encoding="utf-8") as f:
                nbformat.write(modified_nb, f)
                
        print(f"Generated modified notebooks for level {level}.")

class ExecuteNotebook:
    def __init__(self, notebook_path):
        self.notebook_path = notebook_path
        self.output_dir = "../test_data/modify_notebooks/"
        os.makedirs(self.output_dir, exist_ok=True)
        self.successes = 0
        self.total = 0

    def test_agent(self):
        """ Calls ModifyNotebook at each level, runs the agent, and executes test cases. """
        # Initialize the notebook modifier
        mf = ModifyNotebook(self.notebook_path)

        # Get the number of levels from the number of removable functions
        levels = mf.get_functions()
        if levels == 0:
            print("No functions to remove, skipping.")
            return

        # Iterate over all levels of function removal
        for i in range(1, levels + 1):
            self.successes = 0
            self.total = 0
            print(f"Processing level {i}...")
            mf.remove_function_body(i)

            # Get all test notebooks from directory
            test_notebooks = glob.glob(os.path.join(self.output_dir, "*.ipynb"))

            for notebook in test_notebooks:
                # Step 1: Run the agent to fix missing functions
                fixed_notebook = notebook.replace(".ipynb", "_fixed.ipynb")
                
                self.fix_notebook_code_cells(notebook, fixed_notebook)

                # Step 2: Execute notebook and check results
                success = self.run_notebook_and_check_tests(fixed_notebook)

                if success:
                    self.successes += 1
                self.total += 1

            # Print success rate per level
            percent = (self.successes / self.total) * 100 if self.total else 0
            print(f"At level {i}, the agent was {percent:.2f}% successful.")

            # Clear test data directory for next iteration
            self.clear_test_data_dir()
    def run_notebook_and_check_tests(self, notebook_path):
        """ Executes a notebook and checks the last cell for test results. """
        try:
            # print(f"Loading notebook: {notebook_path}")  
            with open(notebook_path, 'r', encoding='utf-8') as f:
                nb = nbformat.read(f, as_version=4)
    
            # Execute notebook and print each cell's execution
            # print("Executing notebook...")
            client = NotebookClient(nb, timeout=30, allow_errors=True)
            client.execute()
    
            # print("Execution complete. Checking executed cells:")
           # for i, cell in enumerate(nb.cells):
           #     if cell.cell_type == "code":
                    #print(f"Cell {i} executed. Source:\n{cell.source}\n")
            #        if "outputs" in cell and cell.outputs:
                        #print(f"Outputs for Cell {i}: {cell.outputs}\n")
    
            # Extract last cell
            last_cell = nb.cells[-1]
            
    
            for entry in last_cell.outputs:
                if 'OK' in entry.get('text', ''):
                    #print("OK  in entry")
                    return True
                #print("Entry: ", entry.get('text', ''))
      
            return False
    
        except Exception as e:
            print(f"Execution failed for {notebook_path}: {e}")
            return False
    
    
    
        
    def clear_test_data_dir(self):
        """ Removes all notebooks from the test directory. """
        files = glob.glob(os.path.join(self.output_dir, "*.ipynb"))
        for f in files:
            os.remove(f)
        print("Cleared modified notebooks.")

    def extract_code_blocks(self, content):
        """
        Extracts code blo cks from the response content.
        """
        code_blocks = re.findall(r'```python\n(.*?)```', content, re.DOTALL)
        return "\n".join(code_blocks) if code_blocks else content


    def fix_notebook_code_cells(self, input_path, output_path):
        with open(input_path, "r") as f:
            notebook_data = json.load(f)
    
        cells = notebook_data.get("cells", [])
        processed_cells = []
    
        for idx, cell in enumerate(cells):
            if cell["cell_type"] == "code":
                code = "".join(cell.get("source", "")).strip()
                if code:
                    config = {"configurable": {"thread_id": "thread-1"}}
    
                    system_message = SystemMessage(
                        content="You are an AI assistant for completing Python notebooks."
                    )
                    human_message = HumanMessage(
                        content=f"Cell {idx}: {code}\n\nCheck for unwritten functions. If there are any, search for context to fill in the bodies. Otherwise, return the original code."
                    )
                    
                    inputs = {"messages": [system_message, human_message], "file_path": input_path}
    
                    # call the agent: 
                    app = get_agent()
                    # Pass the file path into the workflow
                    result = app.invoke(inputs, config)
    
                   
                   
                    
                    fixed_code = result["messages"][-1].content
                    fixed_code = self.extract_code_blocks(fixed_code)
                    cell["source"] = [fixed_code]
                
                processed_cells.append(cell)
            elif cell["cell_type"] == "markdown":
                processed_cells.append(cell)
    
        notebook_data["cells"] = processed_cells
    
        with open(output_path, "w") as f:
            json.dump(notebook_data, f, indent=4)
    
        # print(f"Updated notebook saved to {output_path}")

