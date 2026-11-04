import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "draw-anything" / "scripts"
sys.path.insert(0, str(SCRIPTS))


@pytest.fixture
def run(tmp_path):
    """Run a skill script in tmp_path. Fail with the script output if the exit code is not 0."""
    def _run(script, *args):
        p = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                           cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
        assert p.returncode == 0, p.stdout + p.stderr
        return p.stdout
    return _run
