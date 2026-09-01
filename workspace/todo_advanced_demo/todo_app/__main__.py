"""Entry point for running the todo app as a module: python -m todo_app"""

import sys
from .cli import run

sys.exit(run())
