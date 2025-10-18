import os
import sys

def get_asset_path(*parts: str) -> str:
    """Return an absolute path to an asset inside the project.

    When running under PyInstaller --onefile the files are extracted into
    sys._MEIPASS; otherwise the project layout is used (parent of src/).
    Usage: get_asset_path('assets', 'cards', 'hearts_A.png')
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS
    else:
        # base is project root (one level up from this src/ folder)
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return os.path.normpath(os.path.join(base, *parts))
