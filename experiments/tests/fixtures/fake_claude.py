"""A mocked `claude -p` process for the batch tests. It never contacts any service.

Usage: python fake_claude.py <scenario.json>

The scenario lists stream-json lines to print (one per line, flushed), an optional delay
between lines, an optional hang at the end (to test the time limit), text for standard
error, and the exit code. The event shapes follow Claude Code 2.1.319's real output; every
value is synthetic.
"""

import json
import sys
import time
from pathlib import Path

scenario = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
sys.stderr.write(scenario.get("stderr", ""))
sys.stderr.flush()
for line in scenario["lines"]:
    sys.stdout.write(line + "\n")
    sys.stdout.flush()
    time.sleep(scenario.get("delay", 0.0))
time.sleep(scenario.get("hang", 0.0))
sys.exit(scenario.get("exit_code", 0))
