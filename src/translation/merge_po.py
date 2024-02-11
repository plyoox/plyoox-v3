"""Re-invokes xgettext on source packages and merges them into .po/.pot files."""
import subprocess
from contextlib import nullcontext
from pathlib import Path

pot_files = tuple(Path("locales").glob("*.pot"))

for package_path in Path("locales").iterdir():
    if not package_path.is_dir():
        continue

    po_paths: list[Path] = []
    po_paths.extend(package_path.rglob("*.po"))

    merging_po_cm = nullcontext(pot_files[0])
    print(f"Merging from {pot_files[0]}...")

    with merging_po_cm as merging_po:
        for po_path in po_paths:
            print(po_path)
            subprocess.check_call(["msgmerge", po_path, merging_po, "-o", po_path])
