"""
Installs Toolbox: checks Python libraries and creates Desktop + Start Menu shortcuts.
Run once:  python install.py   (or double-click install.bat)
"""

import os
import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
MAIN = APP_DIR / "toolbox.pyw"


PACKAGES = [("PIL", "pillow"), ("pypdfium2", "pypdfium2")]  # (import name, pip name)


def ensure_packages():
    for module, package in PACKAGES:
        try:
            __import__(module)
            print(f"{package}: already installed")
        except ImportError:
            print(f"Installing {package}…")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", package])


def pythonw_path():
    exe = Path(sys.executable)
    cand = exe.with_name("pythonw.exe")
    return str(cand if cand.exists() else exe)


def make_shortcut(link_path, target, args, workdir):
    ps = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:LNK);"
        "$s.TargetPath=$env:TGT;$s.Arguments=$env:ARGS;$s.WorkingDirectory=$env:WD;"
        "$s.Description='Toolbox';$s.Save()"
    )
    env = dict(os.environ, LNK=str(link_path), TGT=target, ARGS=args, WD=str(workdir))
    subprocess.check_call(["powershell", "-NoProfile", "-Command", ps], env=env)
    print(f"Shortcut: {link_path}")


def main():
    if sys.platform != "win32":
        print("Shortcuts are only created on Windows. Start the app with:  python toolbox.pyw")
        return
    ensure_packages()
    target = pythonw_path()
    args = f'"{MAIN}"'
    desktop = Path(os.path.expandvars(r"%USERPROFILE%\Desktop"))
    start_menu = Path(os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"))
    for folder in (desktop, start_menu):
        if folder.exists():
            make_shortcut(folder / "Toolbox.lnk", target, args, APP_DIR)
    print("\nInstalled. Open 'Toolbox' from your Desktop or Start Menu.")


if __name__ == "__main__":
    main()
