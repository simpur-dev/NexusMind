"""
Compatibility wrapper for Reddit simulation.
Delegates execution to run_parallel_simulation.py with --reddit-only.
"""

import os
import sys
from pathlib import Path

HELP_TEXT = """usage: run_reddit_simulation.py --config CONFIG [--max-rounds N] [--start-round N] [--no-wait] [--no-world-model]

Compatibility wrapper around run_parallel_simulation.py --reddit-only mode.

options:
  --config CONFIG       Path to simulation_config.json
  --max-rounds N        Optional maximum simulation rounds
  --start-round N       Optional resume start round
  --no-wait             Close environment immediately after completion
  --no-world-model      Disable world-model feedback loop
"""


def _bootstrap_paths():
    scripts_dir = Path(__file__).resolve().parent
    backend_dir = scripts_dir.parent
    for path in (backend_dir, scripts_dir):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)
    return scripts_dir


def _target_args(platform_flag):
    scripts_dir = _bootstrap_paths()
    parallel_script = scripts_dir / "run_parallel_simulation.py"
    if not parallel_script.exists():
        print(f"Error: target script not found: {parallel_script}")
        sys.exit(1)

    passthrough = [arg for arg in sys.argv[1:] if arg != platform_flag]
    return [sys.executable, str(parallel_script), platform_flag] + passthrough


def main():
    if any(arg in {"-h", "--help"} for arg in sys.argv[1:]):
        print(HELP_TEXT)
        return
    os.execv(sys.executable, _target_args("--reddit-only"))


if __name__ == "__main__":
    main()
