"""Iterates through .po files in source packages and invokes msgfmt on them."""
import subprocess
from pathlib import Path

print("Building translations...")

for po_path in Path("locales").rglob("*.po"):
    print(po_path)
    output = po_path.with_suffix(".mo")
    subprocess.check_call(["msgfmt", "-o", output, po_path])