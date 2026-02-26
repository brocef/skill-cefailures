import subprocess
import sys
from pathlib import Path

SCRIPT = str(Path(__file__).parent.parent / "scripts" / "install_skill.py")

def test_install_skill_help():
    """Verify the script runs and shows help."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "install" in result.stdout.lower()
