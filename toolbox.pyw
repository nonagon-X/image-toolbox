"""
Toolbox - a small desktop app that hosts tool modules.

Every .py file in the "modules" folder that defines NAME, DESCRIPTION and
build(parent) is shown in the sidebar automatically. Order with ORDER (lower first).
When packaged as Toolbox.exe, a "modules" folder next to the exe is loaded too,
so extra modules can be added without rebuilding.
"""

import importlib.util
import sys
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import messagebox, ttk

APP_NAME = "Toolbox"
VERSION = "1.1.0"

if getattr(sys, "frozen", False):  # running as Toolbox.exe (PyInstaller)
    BUNDLE_DIR = Path(sys._MEIPASS)
    USER_DIR = Path(sys.executable).resolve().parent
else:
    BUNDLE_DIR = USER_DIR = Path(__file__).resolve().parent

MODULE_DIRS = [BUNDLE_DIR / "modules"]
if USER_DIR != BUNDLE_DIR:
    MODULE_DIRS.append(USER_DIR / "modules")
ICON = BUNDLE_DIR / "assets" / "toolbox.ico"

for d in reversed(MODULE_DIRS):
    sys.path.insert(0, str(d))  # lets modules share code from modules/_common.py

import _i18n  # noqa: E402
from _i18n import LANGS, tr  # noqa: E402

SIDEBAR_BG = "#1f2933"
SIDEBAR_FG = "#cbd2d9"
SIDEBAR_ACTIVE = "#3e4c59"


def load_modules():
    mods, seen = [], set()
    for folder in MODULE_DIRS:
        for path in sorted(folder.glob("*.py")):
            if path.name.startswith("_") or path.name in seen:
                continue
            seen.add(path.name)
            try:
                spec = importlib.util.spec_from_file_location(f"toolbox_mod_{path.stem}", path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "NAME") and hasattr(mod, "build"):
                    mods.append(mod)
            except Exception:
                traceback.print_exc()
    mods.sort(key=lambda m: (getattr(m, "ORDER", 100), m.NAME))
    return mods


class ToolboxApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1060x820")
        self.minsize(920, 720)
        if ICON.exists():
            try:
                self.iconbitmap(default=str(ICON))
            except tk.TclError:
                pass
        self._style()
        self.modules = load_modules()
        self.current = None
        self.build_ui()

    def _style(self):
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 18))
        style.configure("Sub.TLabel", font=("Segoe UI", 10), foreground="#52606d")
        style.configure("Section.TLabelframe.Label", font=("Segoe UI Semibold", 10))
        style.configure("Accent.TButton", font=("Segoe UI Semibold", 11), padding=(18, 8))

    # ---- whole window (rebuilt when the language changes)
    def build_ui(self):
        for w in self.winfo_children():
            if not isinstance(w, tk.Toplevel):
                w.destroy()
        self.buttons, self.pages = {}, {}

        self.sidebar = tk.Frame(self, bg=SIDEBAR_BG, width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        tk.Label(self.sidebar, text=APP_NAME, bg=SIDEBAR_BG, fg="white",
                 font=("Segoe UI Semibold", 16), anchor="w", padx=18, pady=18).pack(fill="x")
        tk.Label(self.sidebar, text=tr("MODULES"), bg=SIDEBAR_BG, fg="#7b8794",
                 font=("Segoe UI", 8, "bold"), anchor="w", padx=18).pack(fill="x", pady=(4, 6))

        for mod in self.modules:
            btn = tk.Label(self.sidebar, text=tr(mod.NAME), bg=SIDEBAR_BG, fg=SIDEBAR_FG,
                           font=("Segoe UI", 11), anchor="w", padx=18, pady=9, cursor="hand2")
            btn.pack(fill="x")
            btn.bind("<Button-1>", lambda e, m=mod: self.show(m))
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=SIDEBAR_ACTIVE))
            btn.bind("<Leave>", lambda e, b=btn, m=mod: self._unhover(b, m))
            self.buttons[mod.NAME] = btn

        # language switch at the bottom of the sidebar
        bottom = tk.Frame(self.sidebar, bg=SIDEBAR_BG)
        bottom.pack(side="bottom", fill="x", padx=18, pady=16)
        tk.Label(bottom, text=f"v{VERSION}", bg=SIDEBAR_BG, fg="#616e7c",
                 font=("Segoe UI", 8)).pack(side="right")
        for code, label in LANGS.items():
            active = code == _i18n.language()
            lbl = tk.Label(bottom, text=label, bg=SIDEBAR_BG, cursor="hand2",
                           fg="white" if active else "#7b8794",
                           font=("Segoe UI", 9, "bold" if active else "normal"))
            lbl.pack(side="left", padx=(0, 10))
            lbl.bind("<Button-1>", lambda e, c=code: self.change_language(c))

        self.content = ttk.Frame(self, padding=24)
        self.content.pack(side="left", fill="both", expand=True)

        if not self.modules:
            ttk.Label(self.content, text=tr("No modules found in {path}", path=MODULE_DIRS[0])).pack()
        else:
            self.show(self.current if self.current in self.modules else self.modules[0])

    def change_language(self, code):
        if code == _i18n.language():
            return
        if any(getattr(p, "running", False) for p in self._panels()):
            messagebox.showinfo(APP_NAME, tr("Please wait until the current job finishes, then change the language."))
            return
        _i18n.set_language(code)
        self.build_ui()

    def _panels(self):
        for page in self.pages.values():
            for w in page.winfo_children()[2].winfo_children():
                yield w

    def _unhover(self, btn, mod):
        btn.config(bg=SIDEBAR_ACTIVE if self.current is mod else SIDEBAR_BG)

    def show(self, mod):
        self.current = mod
        for name, btn in self.buttons.items():
            active = name == mod.NAME
            btn.config(bg=SIDEBAR_ACTIVE if active else SIDEBAR_BG, fg="white" if active else SIDEBAR_FG)
        for page in self.pages.values():
            page.pack_forget()
        if mod.NAME not in self.pages:
            page = ttk.Frame(self.content)
            ttk.Label(page, text=tr(mod.NAME), style="Title.TLabel").pack(anchor="w")
            ttk.Label(page, text=tr(getattr(mod, "DESCRIPTION", "")), style="Sub.TLabel").pack(anchor="w", pady=(2, 14))
            body = ttk.Frame(page)
            body.pack(fill="both", expand=True)
            try:
                mod.build(body)
            except Exception:
                ttk.Label(body, text=tr("This module failed to load:") + "\n\n" + traceback.format_exc(),
                          foreground="#c0392b").pack(anchor="w")
            self.pages[mod.NAME] = page
        self.pages[mod.NAME].pack(fill="both", expand=True)


def selftest(report_path):
    """Toolbox.exe --selftest report.txt : checks a build works end to end, without showing a window."""
    import tempfile
    lines, ok = [], True

    def check(name, fn):
        nonlocal ok
        try:
            lines.append(f"OK    {name}: {fn() or ''}")
        except Exception as e:
            ok = False
            lines.append(f"FAIL  {name}: {e!r}")

    tmp = Path(tempfile.mkdtemp(prefix="toolbox-selftest-"))
    src = tmp / "src"
    src.mkdir()

    def make_inputs():
        from PIL import Image
        Image.new("RGB", (3000, 2000), (40, 90, 200)).save(src / "photo.jpg")
        Image.new("RGB", (1240, 1754), "white").save(src / "doc.pdf", save_all=True,
                                                       append_images=[Image.new("RGB", (1240, 1754), "grey")])
        return "photo.jpg + 2-page doc.pdf"

    check("create test files", make_inputs)
    app = None

    def build_pages():
        nonlocal app
        app = ToolboxApp()
        app.withdraw()
        for m in app.modules:
            app.show(m)
        return ", ".join(m.NAME for m in app.modules)

    def run_job(name, out, setup=None):
        def go():
            page = app.pages[name].winfo_children()[2].winfo_children()[0]
            page.sources = [str(src)]
            page.var_out.set(str(tmp / out))
            page.var_open.set(False)
            if setup:
                setup(page)
            page.start()
            while page.running:
                app.update()
            files = sorted(p.relative_to(tmp / out).as_posix() for p in (tmp / out).rglob("*.*")
                           if p.name != ".toolbox-output")
            if not files:
                raise RuntimeError(page.log.get("1.0", "end").strip())
            return ", ".join(files)
        return go

    for lang in ("en", "pl"):
        _i18n.set_language(lang, remember=False)
        check(f"[{lang}] open all module pages", build_pages)
        check(f"[{lang}] Resize", run_job("Resize Images", f"{lang}_resize"))
        check(f"[{lang}] Convert to AVIF", run_job("Convert Format", f"{lang}_convert",
                                                    lambda p: p.var_format.set("avif")))
        check(f"[{lang}] PDF to Images", run_job("PDF to Images", f"{lang}_pdf"))
        check(f"[{lang}] sidebar text", lambda: ", ".join(b.cget("text") for b in app.buttons.values()))
        app.destroy()

    lines.insert(0, f"Toolbox {VERSION} self-test: {'PASSED' if ok else 'FAILED'}  (frozen={getattr(sys, 'frozen', False)})")
    Path(report_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv:
        i = sys.argv.index("--selftest")
        report = sys.argv[i + 1] if len(sys.argv) > i + 1 else "toolbox-selftest.txt"
        _i18n.set_language("en", remember=False)
        sys.exit(selftest(report))
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # crisp text on high-DPI screens
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("nonagonx.toolbox")  # own taskbar icon
        except Exception:
            pass
    _i18n.init()
    ToolboxApp().mainloop()


if __name__ == "__main__":
    main()
