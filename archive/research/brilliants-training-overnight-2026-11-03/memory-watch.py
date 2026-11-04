"""Read-only memory checks for this overnight study; no process control."""
import datetime
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
deadline = datetime.datetime.fromisoformat(
    json.loads((ROOT / 'PLAN.json').read_text())['deadline_utc'].replace('Z', '+00:00')
).timestamp() + 120
previous = object()
while time.time() < deadline and not (ROOT / 'STOP_MEMORY').exists():
    check = subprocess.run(
        ['/usr/sbin/sysctl', '-n', 'kern.memorystatus_vm_pressure_level'],
        capture_output=True, text=True, timeout=5,
    )
    try:
        level = int(check.stdout.strip()) if check.returncode == 0 else None
    except ValueError:
        level = None
    state = {
        'updated_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'unix_time': time.time(), 'level': level,
        'normal': level == 1, 'pid': __import__('os').getpid(),
        'scope': 'Study-only read-only check; stale >15 seconds means unknown.',
    }
    output = ROOT / 'MEMORY-STATE.json'
    temporary = output.with_suffix('.tmp')
    temporary.write_text(json.dumps(state) + '\n')
    temporary.replace(output)
    if level != previous:
        print(json.dumps(state), flush=True)
        previous = level
    time.sleep(5)
