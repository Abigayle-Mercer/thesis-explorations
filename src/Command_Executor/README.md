# JupyterLab Agent Testing Suite

## Description
A series of **natural language prompts** for the agent to infer **intent** from and return a series of **expected JupyterLab commands** for execution.

---

## Unit Tests

The following tests check **single-step** commands.

1. **Running Cells**
   - `"Run the current cell"` → `notebook:run-cell`
   - `"Run this cell and move to the next"` → `notebook:run-cell-and-select-next`

2. **Cutting a Cell**
   - `"Cut the current cell"` → `notebook:cut-cell`

3. **Adding Cells**
   - `"Add a cell below"` → `notebook:insert-cell-below`
   - `"Add a cell above"` → `notebook:insert-cell-above`

4. **Deleting Cells**
   - `"Delete the current cell"` → `notebook:delete-cell`

5. **Copying and Pasting Cells**
   - `"Copy the current cell"` → `notebook:copy-cell`
   - `"Paste below"` → `notebook:paste-cell-below`
   - `"Paste above"` → `notebook:paste-cell-above`

6. **Moving Cells**
   - `"Move this cell up"` → `notebook:move-cell-up`
   - `"Move this cell down"` → `notebook:move-cell-down`
   - `"Swap this cell with the one below it"` → `notebook:move-cell-down`
   - `"Swap this cell with the one above it"` → `notebook:move-cell-up`

7. **Undo/Redo Actions**
   - `"Undo the last cell action"` → `notebook:undo-cell-action`
   - `"Redo the last cell action"` → `notebook:redo-cell-action`

8. **Running Multiple Cells**
   - `"Run all cells"` → `notebook:run-all-cells`

9. **Kernel Operations**
   - `"Restart the kernel"` → `notebook:restart-kernel`
   - `"Restart the kernel and run all"` → `notebook:restart-run-all`

10. **Markdown Cell Conversion**
   - `"Make this cell markdown"` → `notebook:change-cell-to-markdown`

11. **Merging Cells**
   - `"Merge selected cells"` → `notebook:merge-cells`
   - `"Merge this cell with the one above"` → `notebook:merge-cell-above`
   - `"Merge this cell with the one below"` → `notebook:merge-cell-below`

12. **Notebook Creation**
   - `"Create a new notebook"` → `notebook:create-new`

13. **Selecting Cells**
   - `"Move up"`, `"Select the cell above"`, `"Go to the previous cell"` → `notebook:move-cursor-up`
   - `"Move down"`, `"Select the cell below"`, `"Go to the next cell"` → `notebook:move-cursor-down`

---

## Dynamic Tests

The following tests check **multi-step** command execution.

1. **Navigating and Running Cells**
   - `"Run the cell above this"`
     ```json
     [
       {"name": "notebook:move-cursor-up", "args": {}},
       {"name": "notebook:run-cell", "args": {"activate": true}}
     ]
     ```
   - `"Run the cell 2 cells above this"`
     ```json
     [
       {"name": "notebook:move-cursor-up", "args": {}},
       {"name": "notebook:move-cursor-up", "args": {}},
       {"name": "notebook:run-cell", "args": {"activate": true}}
     ]
     ```
   - `"Run the cell 3 cells above this"`
     ```json
     [
       {"name": "notebook:move-cursor-up", "args": {}},
       {"name": "notebook:move-cursor-up", "args": {}},
       {"name": "notebook:move-cursor-up", "args": {}},
       {"name": "notebook:run-cell", "args": {"activate": true}}
     ]
     ```

2. **Inserting and Editing a Markdown Cell**
   - `"Insert a markdown cell above and start editing"`
     ```json
     [
       {"name": "notebook:insert-cell-above", "args": {"activate": true, "toolbar": false}},
       {"name": "notebook:change-cell-to-markdown", "args": {"activate": true}},
       {"name": "notebook:enter-edit-mode", "args": {"activate": true}}
     ]
     ```

3. **Running Multiple Cells**
   - `"Run this cell and the next"`
     ```json
     [
       {"name": "notebook:run-cell-and-select-next", "args": {"activate": true}},
       {"name": "notebook:run-cell-and-select-next", "args": {"activate": true}}
     ]
     ```

4. **Deleting Multiple Cells**
   - `"Delete this cell and the next"`
     ```json
     [
       {"name": "notebook:delete-cell", "args": {}},
       {"name": "notebook:delete-cell", "args": {}}
     ]
     ```

---

## Running the Tests

To run the unit tests:

```bash
pytest unit-test.py
