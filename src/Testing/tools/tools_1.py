# tools.py
import json
from langchain_core.tools import tool


@tool("delete_cell", return_direct=True)
def delete_cell(file_path: str, cell_id: int) -> str:
    """
    Remove a cell.
    """
    try:
        # Load notebook
        with open(file_path, "r", encoding="utf-8") as f:
            notebook = json.load(f)

        # Ensure valid cell index
        if 0 <= cell_id < len(notebook["cells"]):
            cut_cell = notebook["cells"].pop(cell_id)
            
            # Save updated notebook
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(notebook, f, indent=2)

            return f"✅ Cut cell {cell_id}: {cut_cell['source']}"
        else:
            return f"❌ Invalid cell ID: {cell_id}"

    except Exception as e:
        return f"❌ Error cutting cell: {str(e)}"


@tool("add_cell", return_direct=True)
def add_cell(file_path: str, cell_id: int, cell_type: str = "code") -> str:
    """
    Add a new cell (code or markdown).
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
        id = max(0, min(cell_id, len(notebook["cells"])))  # Clamp ID within range
        notebook["cells"].insert(id, new_cell)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(notebook, f, indent=2)

        return f"✅ Added {cell_type} cell at position {id}."

    except Exception as e:
        return f"❌ Error adding cell: {str(e)}"


@tool("write_to_cell", return_direct=True)
def write_to_cell(file_path: str, cell_id: int, content: str) -> str:
    """
    Write content to a cell.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            notebook = json.load(f)

        if 0 <= cell_id < len(notebook["cells"]):
            notebook["cells"][cell_id]["source"] = content.split("\n")  # Split into list for Jupyter format
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(notebook, f, indent=2)

            return f"✅ Updated cell {cell_id} with content:\n{content}"
        else:
            return f"❌ Invalid cell ID: {cell_id}"

    except Exception as e:
        return f"❌ Error writing to cell: {str(e)}"

#    Read the full content of a specific cell in a notebook, including its type, execution count, metadata, outputs, and source code.


@tool("read_cell", return_direct=True)
def read_cell(file_path: str, cell_id: int) -> str:
    """
    Read the content of a cell.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            notebook = json.load(f)

        if 0 <= cell_id < len(notebook["cells"]):
            cell_data = notebook["cells"][cell_id]
            return json.dumps(cell_data, indent=2)  # Return full cell as JSON-formatted string
        else:
            return f"❌ Invalid cell ID: {cell_id}"

    except Exception as e:
        return f"❌ Error reading cell: {str(e)}"
    
    
#     Return the total number of cells in the Jupyter notebook.

@tool("cell_count", return_direct=True)
def cell_count(file_path: str) -> str:
    """
    Return the total number of cells.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            notebook = json.load(f)

        max_index = len(notebook["cells"]) - 1  # Last cell index
        return f"✅ The last cell index is {max_index}."

    except Exception as e:
        return f"❌ Error getting max cell index: {str(e)}"


# Retrieve all cells from a Jupyter notebook. This includes 
#    all of the cells and their order in the notebook, their content, 
#    output, cell type, execution count, and other metadata.
@tool("read_notebook", return_direct=True)
def read_notebook(file_path: str) -> str:
    """
    Retrieve all cells.
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

