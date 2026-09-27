import os
import sys

# Make ``src`` importable when running `python -m unittest discover -s tests`
# without requiring an editable install.
_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
