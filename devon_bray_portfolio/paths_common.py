"""
Locations of common files within this repo.
"""

import os
from pathlib import Path

_CURRENT_DIRECTORY = Path(os.path.dirname(os.path.abspath(__file__)))

CONTENT_ROOT = _CURRENT_DIRECTORY.joinpath("portfolio_content")
