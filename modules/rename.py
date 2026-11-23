"""Toolbox module: rename many images at once (as copies)."""

import re
import shutil
import tkinter as tk
import unicodedata
from datetime import datetime
from tkinter import ttk

from _common import HINT, SUPPORTED, JobPanel, rel_dir

NAME = "Rename in Bulk"
DESCRIPTION = "Give many images clean, web-friendly names in one go. Renamed copies are made; originals stay as they are."
ORDER = 4

SORTS = ["File name", "Date taken (camera)", "Date modified"]


def date_taken(path):
    try:
        from PIL import Image

        with Image.open(path) as im:
            exif = im.getexif()
            value = exif.get_ifd(0x8769).get(36867) or exif.get(306)
            if value:
                return datetime.strptime(str(value).strip()[:19], "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    return datetime.fromtimestamp(path.stat().st_mtime)


def clean(name, o):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name)  # never allowed on Windows
    if o["hyphens"]:
        name = re.sub(r"[\s_]+", "-", name)
    if o["web_safe"]:
        name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
        name = re.sub(r"[^A-Za-z0-9\-_.]", "", name)
        name = re.sub(r"-{2,}", "-", name)
    if o["lower"]:
        name = name.lower()
    return name.strip(" .-_") or "image"


def plan_names(files, o, base):
    """Return the files in order and a {file: new name} plan, with clashes numbered -2, -3…"""
    dates = {}
    if "{date}" in o["pattern"] or o["sort"] == SORTS[1]:
        dates = {f: date_taken(f) for f in files}
    if o["sort"] == SORTS[1]:
        files = sorted(files, key=lambda f: (dates[f], str(f).lower()))
    elif o["sort"] == SORTS[2]:
        files = sorted(files, key=lambda f: (f.stat().st_mtime, str(f).lower()))

    plan, used = {}, set()
    for i, f in enumerate(files):
        n = str(o["start"] + i).zfill(o["digits"])
        stem = (o["pattern"]
                .replace("{name}", f.stem)
                .replace("{n}", n)
                .replace("{date}", dates[f].strftime("%Y-%m-%d") if f in dates else "")
                .replace("{folder}", f.parent.name))
        stem = clean(stem, o)
        ext = f.suffix.lower() if o["lower"] else f.suffix
        new, k = stem + ext, 2
        folder = str(rel_dir(base, f)).lower()
        while (folder, new.lower()) in used:
            new, k = f"{stem}-{k}{ext}", k + 1
        used.add((folder, new.lower()))
        plan[f] = new
    return files, plan


class RenamePanel(JobPanel):
    NAME = NAME
    OUT_NAME = "renamed"
    RUN_LABEL = "Rename copies"
    EXTS = SUPPORTED | {".svg", ".heic", ".heif", ".jfif"}
    SHOW_SIZES = False

    def build_settings(self, st):
        pad = self.PAD
        self.var_pattern = tk.StringVar(value="{name}")
        self.var_start = tk.IntVar(value=1)
        self.var_digits = tk.IntVar(value=2)
        self.var_lower = tk.BooleanVar(value=True)
        self.var_hyphens = tk.BooleanVar(value=True)
        self.var_web = tk.BooleanVar(value=True)
        self.var_sort = tk.StringVar(value=SORTS[0])
        self._after = None

        ttk.Label(st, text="New name").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(st, textvariable=self.var_pattern, width=34).grid(row=0, column=1, columnspan=3, sticky="w", **pad)
        quick = ttk.Frame(st)
        quick.grid(row=0, column=4, columnspan=2, sticky="w")
        for label, tpl in [("Name", "{name}"), ("Text + number", "my-photo-{n}"), ("Date + number", "{date}-{n}")]:
            ttk.Button(quick, text=label, command=lambda t=tpl: self.var_pattern.set(t)).pack(side="left", padx=2)

        ttk.Label(st, text="{name} original name   {n} number   {date} date taken   {folder} folder name",
                  foreground=HINT).grid(row=1, column=1, columnspan=5, sticky="w", padx=10)

        ttk.Label(st, text="Numbers").grid(row=2, column=0, sticky="w", **pad)
        nf = ttk.Frame(st)
        nf.grid(row=2, column=1, columnspan=5, sticky="w", **pad)
        ttk.Label(nf, text="start at").pack(side="left")
        ttk.Spinbox(nf, from_=0, to=99999, textvariable=self.var_start, width=6).pack(side="left", padx=(4, 14))
        ttk.Label(nf, text="digits").pack(side="left")
        ttk.Spinbox(nf, from_=1, to=6, textvariable=self.var_digits, width=3).pack(side="left", padx=(4, 14))
        ttk.Label(nf, text="order by").pack(side="left")
        ttk.Combobox(nf, textvariable=self.var_sort, values=SORTS, state="readonly", width=20).pack(side="left", padx=4)

        of = ttk.Frame(st)
        of.grid(row=3, column=0, columnspan=6, sticky="w", **pad)
        ttk.Checkbutton(of, text="lowercase", variable=self.var_lower).pack(side="left", padx=(0, 14))
        ttk.Checkbutton(of, text="spaces → hyphens", variable=self.var_hyphens).pack(side="left", padx=(0, 14))
        ttk.Checkbutton(of, text="web-safe characters only (best for SEO and URLs)",
                        variable=self.var_web).pack(side="left")

        ttk.Label(st, text="Preview").grid(row=4, column=0, sticky="nw", **pad)
        self.preview = tk.Listbox(st, height=5, font=("Consolas", 9), relief="flat", bg="#f5f7fa",
                                  activestyle="none", width=90)
        self.preview.grid(row=4, column=1, columnspan=5, sticky="we", **pad)
        self.preview.insert("end", "Choose a folder or files to see the new names here.")

        for v in (self.var_pattern, self.var_start, self.var_digits, self.var_lower,
                  self.var_hyphens, self.var_web, self.var_sort):
            v.trace_add("write", lambda *a: self._schedule_preview())

    def get_opts(self):
        try:
            start, digits = int(self.var_start.get()), int(self.var_digits.get())
        except (tk.TclError, ValueError):
            raise ValueError("Start number and digits must be whole numbers.")
        pattern = self.var_pattern.get().strip()
        if not pattern:
            raise ValueError("Type a new name pattern, e.g. {name} or my-photo-{n}.")
        return {"pattern": pattern, "start": start, "digits": max(1, digits), "lower": self.var_lower.get(),
                "hyphens": self.var_hyphens.get(), "web_safe": self.var_web.get(), "sort": self.var_sort.get()}

    def on_sources_changed(self):
        self._schedule_preview()

    def _schedule_preview(self):
        if self._after:
            self.after_cancel(self._after)
        self._after = self.after(250, self._update_preview)

    def _update_preview(self):
        self._after = None
        self.preview.delete(0, "end")
        files, base = self.current_files()
        if not files:
            self.preview.insert("end", "No images found yet." if self.sources else
                                "Choose a folder or files to see the new names here.")
            return
        try:
            o = self.get_opts()
        except ValueError as e:
            self.preview.insert("end", str(e))
            return
        ordered, plan = plan_names(files, o, base)
        for f in ordered[:30]:
            self.preview.insert("end", f"{f.name}  →  {plan[f]}")
        if len(ordered) > 30:
            self.preview.insert("end", f"… and {len(ordered) - 30} more")

    def prepare(self, files, o, base):
        ordered, o["plan"] = plan_names(files, o, base)
        return ordered

    def process(self, src, dest_dir, o, index):
        dest = dest_dir / o["plan"][src]
        shutil.copy2(src, dest)
        return dest, ""


def build(parent):
    return RenamePanel(parent)
