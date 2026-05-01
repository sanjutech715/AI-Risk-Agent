"""
tests/conftest.py
─────────────────
Import fixtures from pytesting/conftest.py for tests in this directory.
"""

# Import all fixtures from pytesting/conftest.py
import sys
import os

# Add parent directory to path to import from pytesting
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pytesting.conftest import *  # noqa: F401, F403