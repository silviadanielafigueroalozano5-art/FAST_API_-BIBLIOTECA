"""Alias compatible para ejecutar la suite de integración de la API."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
resultado = subprocess.run(
    [sys.executable, "-m", "pytest", "-q"],
    cwd=ROOT,
    check=False,
)
raise SystemExit(resultado.returncode)
