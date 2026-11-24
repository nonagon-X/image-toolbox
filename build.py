"""
Builds dist/Toolbox.exe: one file with Python, the libraries and all modules inside.
People can run it on any Windows 10/11 PC without installing Python.

    python build.py        (or double-click build.bat)

Needs:  pip install pyinstaller pillow pypdfium2
"""

import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODULES = ROOT / "modules"


def module_imports():
    """Modules are loaded at runtime, so PyInstaller can't see what they import. List it for it."""
    names = set()
    for f in MODULES.glob("*.py"):
        names.add(f.stem)
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names.add(node.module)
    names.discard("pillow_heif")  # optional extra, not bundled
    return sorted(names)


def main():
    if not (ROOT / "assets" / "toolbox.ico").exists():
        subprocess.check_call([sys.executable, str(ROOT / "assets" / "make_icon.py")])

    sep = ";" if sys.platform == "win32" else ":"
    cmd = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--onefile", "--windowed", "--name", "Toolbox",
        "--icon", str(ROOT / "assets" / "toolbox.ico"),
        "--add-data", f"{MODULES}{sep}modules",
        "--add-data", f"{ROOT / 'assets' / 'toolbox.ico'}{sep}assets",
        "--paths", str(MODULES),
        "--collect-all", "pypdfium2", "--collect-all", "pypdfium2_raw",
        "--exclude-module", "pillow_heif",
    ]
    for name in module_imports():
        cmd += ["--hidden-import", name]
    cmd.append(str(ROOT / "toolbox.pyw"))

    print("Building Toolbox.exe…")
    subprocess.check_call(cmd, cwd=ROOT)
    exe = ROOT / "dist" / "Toolbox.exe"
    print(f"\nDone: {exe}  ({exe.stat().st_size / 1048576:.0f} MB)")


if __name__ == "__main__":
    main()
