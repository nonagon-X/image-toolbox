"""
Toolbox - a small desktop app that hosts tool modules.

Every .py file in the "modules" folder that defines NAME, DESCRIPTION and
build(parent) is shown in the sidebar automatically. Order with ORDER (lower first).
"""

import importlib.util
import sys
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import ttk

APP_NAME = "Toolbox"
APP_DIR = Path(__file__).resolve().parent
MODULES_DIR = APP_DIR / "modules"

SIDEBAR_BG = "#1f2933"
SIDEBAR_FG = "#cbd2d9"
SIDEBAR_ACTIVE = "#3e4c59"
ACCENT = "#2f80ed"


sys.path.insert(0, str(MODULES_DIR))  # lets modules share code from modules/_common.py


def load_modules():
    mods = []
    for path in sorted(MODULES_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue
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
        self.geometry("1040x800")
        self.minsize(900, 700)
        self._style()

        self.sidebar = tk.Frame(self, bg=SIDEBAR_BG, width=210)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text=APP_NAME, bg=SIDEBAR_BG, fg="white",
                 font=("Segoe UI Semibold", 16), anchor="w", padx=18, pady=18).pack(fill="x")
        tk.Label(self.sidebar, text="MODULES", bg=SIDEBAR_BG, fg="#7b8794",
                 font=("Segoe UI", 8, "bold"), anchor="w", padx=18).pack(fill="x", pady=(4, 6))

        self.content = ttk.Frame(self, padding=24)
        self.content.pack(side="left", fill="both", expand=True)

        self.buttons = {}
        self.pages = {}
        self.modules = load_modules()

        for mod in self.modules:
            btn = tk.Label(self.sidebar, text=mod.NAME, bg=SIDEBAR_BG, fg=SIDEBAR_FG,
                           font=("Segoe UI", 11), anchor="w", padx=18, pady=9, cursor="hand2")
            btn.pack(fill="x")
            btn.bind("<Button-1>", lambda e, m=mod: self.show(m))
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=SIDEBAR_ACTIVE))
            btn.bind("<Leave>", lambda e, b=btn, m=mod: self._unhover(b, m))
            self.buttons[mod.NAME] = btn

        if not self.modules:
            ttk.Label(self.content, text=f"No modules found in {MODULES_DIR}").pack()
        else:
            self.current = None
            self.show(self.modules[0])

    def _style(self):
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 18))
        style.configure("Sub.TLabel", font=("Segoe UI", 10), foreground="#52606d")
        style.configure("Section.TLabelframe.Label", font=("Segoe UI Semibold", 10))
        style.configure("Accent.TButton", font=("Segoe UI Semibold", 11), padding=(18, 8))

    def _unhover(self, btn, mod):
        btn.config(bg=SIDEBAR_ACTIVE if self.current is mod else SIDEBAR_BG)

    def show(self, mod):
        self.current = mod
        for name, btn in self.buttons.items():
            active = name == mod.NAME
            btn.config(bg=SIDEBAR_ACTIVE if active else SIDEBAR_BG,
                       fg="white" if active else SIDEBAR_FG)
        for page in self.pages.values():
            page.pack_forget()
        if mod.NAME not in self.pages:
            page = ttk.Frame(self.content)
            ttk.Label(page, text=mod.NAME, style="Title.TLabel").pack(anchor="w")
            ttk.Label(page, text=getattr(mod, "DESCRIPTION", ""), style="Sub.TLabel").pack(anchor="w", pady=(2, 14))
            body = ttk.Frame(page)
            body.pack(fill="both", expand=True)
            try:
                mod.build(body)
            except Exception:
                ttk.Label(body, text="This module failed to load:\n\n" + traceback.format_exc(),
                          foreground="#c0392b").pack(anchor="w")
            self.pages[mod.NAME] = page
        self.pages[mod.NAME].pack(fill="both", expand=True)


if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # crisp text on high-DPI screens
        except Exception:
            pass
    ToolboxApp().mainloop()
