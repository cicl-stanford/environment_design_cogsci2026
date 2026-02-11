# project_code/python/utils/paths.py
from pathlib import Path
import os

def get_project_root() -> Path:
    """Finds the project root by searching for a .project_root marker file."""
    current_path = Path(__file__).resolve()
    while current_path != current_path.parent:
        if (current_path / ".project_root").exists():
            return current_path
        current_path = current_path.parent
    raise FileNotFoundError("Could not find project root. Make sure a .project_root file exists.")

# Define key project paths once
PROJECT_ROOT = get_project_root()
DATA_DIR = PROJECT_ROOT / "data"
STIMULI_DIR = PROJECT_ROOT / "stimuli"
GYM_COOKING_DIR = PROJECT_ROOT / "gym-cooking"
CODE_DIR = PROJECT_ROOT / "project_code"
FIGURES_DIR = PROJECT_ROOT / "figures"

# For HPC environments, allow an environment variable to override the output directory.
# The default is a new 'output' directory in the project root.
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", PROJECT_ROOT / "output"))
