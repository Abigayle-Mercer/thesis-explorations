
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

