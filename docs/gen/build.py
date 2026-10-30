"""Rebuild the generated README animations: python3 docs/gen/build.py (from the repo root).

hero, chat, how-it-works and tools are hand-written SVG; these four are generated so their
timings stay consistent. Edit the matching script, rebuild, and check the result in a browser.
"""

import pathlib
import runpy
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
for script, out in [
    ("wait.py", "wait.svg"),
    ("safety.py", "safety.svg"),
    ("http_roles.py", "http-roles.svg"),
    ("prompts.py", "prompts.svg"),
]:
    sys.argv = [script, str(HERE.parent / out)]
    runpy.run_path(str(HERE / script), run_name="__main__")
    print("wrote", out)
