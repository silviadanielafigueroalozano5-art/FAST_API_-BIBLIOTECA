"""Alias compatible para ejecutar la suite de pruebas automatizadas."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
resultado = subprocess.run(
    [sys.executable, "-m", "pytest", "-q", "tests/test_auth_api.py"],
    cwd=ROOT,
    check=False,
)
raise SystemExit(resultado.returncode)
