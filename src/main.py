# src/main.py
import sys
import os
import tkinter as tk

# Try package-relative import first (when run with `python -m src.main`).
try:
    from .ui import ArtDealerUI
except Exception:
    # Fallback: adjust sys.path so that running `python src/main.py` from
    # project root still finds the `src` package modules.
    this_dir = os.path.dirname(__file__)
    project_root = os.path.normpath(os.path.join(this_dir, '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    # import the module as a top-level module
    from src.ui import ArtDealerUI


def main():
    root = tk.Tk()
    root.geometry("800x600")
    app = ArtDealerUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
