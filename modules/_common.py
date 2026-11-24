"""
Shared building blocks for Toolbox image modules (files starting with "_" are not
shown in the sidebar).

A module subclasses JobPanel and fills in:
    attributes: OUT_NAME, RUN_LABEL, EXTS, SHOW_SIZES, SOURCE_TITLE, FILE_LABEL,
                FOUND_TEXT, PROGRESS_TEXT   (texts in English; they are translated with tr())
    build_settings(frame)          - add the module's own options to the "2. Settings" box
    get_opts()                     - read the options (main thread); raise ValueError("msg") if invalid
    prepare(files, opts, base)     - optional: sort/plan before the run (worker thread); return files
    process(src, dest_dir, opts, i)- do one file (worker thread); return (dest_path, short_message)
                                     or raise SkipFile("reason")
    on_sources_changed()           - optional: called when the user picks new files
    count_units(src, opts)         - optional: progress steps per file (e.g. PDF pages)

All visible text goes through tr() from _i18n so it can be translated (see _lang_pl.py).
"""

import os
import queue
import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from _i18n import dec, num, tr

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif", ".avif"}
FORMAT_EXT = {"jpeg": ".jpg", "png": ".png", "webp": ".webp", "avif": ".avif"}
HINT = "#7b8794"

# iPhone photos (.heic) work too when the optional pillow-heif package is installed
try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
    SUPPORTED |= {".heic", ".heif"}
except ImportError:
    pass


class SkipFile(Exception):
    """Raise from process() to skip a file without counting it as a failure."""


# ---------------------------------------------------------------- image helpers

MARKER = ".toolbox-output"  # hidden file placed in every output folder


def mark_output_folder(folder):
    """Tag a folder as Toolbox output so later runs never treat its copies as source images."""
    m = Path(folder) / MARKER
    if not m.exists():
        m.write_text("Created by Toolbox. Folders with this file are skipped as image sources.\n")
        if os.name == "nt":
            try:
                import ctypes
                ctypes.windll.kernel32.SetFileAttributesW(str(m), 0x02)  # hidden
            except Exception:
                pass


def collect_images(sources, recursive, out_dir, exts=SUPPORTED):
    files = []
    out_res = out_dir.resolve()

    def skip_dir(d):
        return d.resolve() == out_res or (d / MARKER).exists()

    for item in sources:
        p = Path(item)
        if p.is_file() and p.suffix.lower() in exts:
            files.append(p)
        elif p.is_dir():
            for root, dirs, names in os.walk(p):
                root = Path(root)
                if root != p and skip_dir(root):
                    dirs[:] = []
                    continue
                dirs[:] = [x for x in dirs if not skip_dir(root / x)] if recursive else []
                files += [root / n for n in names if Path(n).suffix.lower() in exts]
    return sorted(set(files), key=lambda f: str(f).lower())


def base_of(sources):
    first = Path(sources[0])
    return first if first.is_dir() else first.parent


def rel_dir(base, src):
    """Sub-folder of src relative to base (keeps folder structure when including sub-folders)."""
    try:
        return src.resolve().parent.relative_to(base.resolve())
    except ValueError:
        return Path()


def target_format(src_suffix, wanted="keep"):
    if wanted != "keep":
        return wanted
    return {".jpg": "jpeg", ".jpeg": "jpeg", ".webp": "webp", ".png": "png",
            ".avif": "avif"}.get(src_suffix.lower(), "jpeg")


def open_image(src):
    """Open an image upright (applies camera rotation). Returns (image, icc_profile)."""
    from PIL import Image, ImageOps

    with Image.open(src) as im:
        icc = im.info.get("icc_profile")
        im = ImageOps.exif_transpose(im)  # returns a loaded copy
    return im, icc


def has_alpha(im):
    return im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info)


def flatten(im, bg=(255, 255, 255)):
    """Remove transparency by placing the image on a solid background colour."""
    from PIL import Image

    if has_alpha(im):
        im = im.convert("RGBA")
        out = Image.new("RGB", im.size, bg)
        out.paste(im, mask=im.getchannel("A"))
        return out
    return im if im.mode in ("RGB", "L") else im.convert("RGB")


def save_image(im, dest_stem, fmt, quality=82, icc=None, exif=None, bg=(255, 255, 255),
               png_colors=None, ext=None):
    """Save im as fmt. dest_stem is folder/name without extension. Returns the saved path."""
    from PIL import Image

    dest_stem = Path(dest_stem)
    dest = dest_stem.with_name(dest_stem.name + (ext or FORMAT_EXT[fmt]))
    extra = {}
    if icc:
        extra["icc_profile"] = icc
    if exif:
        extra["exif"] = exif

    if fmt == "jpeg":
        flatten(im, bg).save(dest, "JPEG", quality=quality, optimize=True, progressive=True, **extra)
    elif fmt in ("webp", "avif"):
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA" if has_alpha(im) else "RGB")
        if fmt == "webp":
            im.save(dest, "WEBP", quality=quality, method=6, **extra)
        else:
            im.save(dest, "AVIF", quality=quality, **extra)
    elif fmt == "png":
        if png_colors:
            im = im.convert("RGBA").quantize(colors=png_colors, method=Image.Quantize.FASTOCTREE)
        im.save(dest, "PNG", optimize=True, **{k: v for k, v in extra.items() if k == "icc_profile"})
    else:
        raise ValueError(f"Unknown format {fmt}")
    return dest


def kb(n):
    return f"{num(round(n / 1024))} KB"


# ---------------------------------------------------------------- small UI helpers
# Labels passed to these helpers are English; the helpers translate them.

def quality_slider(parent, var, row, label="Quality", hint="(80–85 is a good balance)", pad=None):
    pad = pad or {"padx": 10, "pady": 5}
    ttk.Label(parent, text=tr(label)).grid(row=row, column=0, sticky="w", **pad)
    f = ttk.Frame(parent)
    f.grid(row=row, column=1, columnspan=5, sticky="w", **pad)
    ttk.Scale(f, from_=30, to=100, variable=var, length=220,
              command=lambda v: var.set(round(float(v)))).pack(side="left")
    ttk.Label(f, textvariable=var, width=4).pack(side="left", padx=8)
    if hint:
        ttk.Label(f, text=tr(hint), foreground=HINT).pack(side="left")
    return f


def radio_row(parent, var, choices, row, label, pad=None):
    pad = pad or {"padx": 10, "pady": 5}
    ttk.Label(parent, text=tr(label)).grid(row=row, column=0, sticky="w", **pad)
    f = ttk.Frame(parent)
    f.grid(row=row, column=1, columnspan=5, sticky="w", **pad)
    for text, val in choices:
        ttk.Radiobutton(f, text=tr(text), value=val, variable=var).pack(side="left", padx=(0, 14))
    return f


class Choice:
    """A read-only drop-down that shows translated labels but returns the English key."""

    def __init__(self, parent, keys, default, width=20, on_change=None):
        self.keys = list(keys)
        self.var = tk.StringVar(value=tr(default))
        self.widget = ttk.Combobox(parent, textvariable=self.var, values=[tr(k) for k in self.keys],
                                   state="readonly", width=width)
        if on_change:
            self.widget.bind("<<ComboboxSelected>>", lambda e: on_change())

    def get(self):
        labels = [tr(k) for k in self.keys]
        value = self.var.get()
        return self.keys[labels.index(value)] if value in labels else self.keys[0]

    def set(self, key):
        self.var.set(tr(key))


# ---------------------------------------------------------------- base panel

class JobPanel(ttk.Frame):
    NAME = "Tool"
    OUT_NAME = "output"          # default output sub-folder name
    RUN_LABEL = "Run"
    EXTS = SUPPORTED             # which files are picked up
    SHOW_SIZES = True            # log size before → after
    SOURCE_TITLE = "1. Choose images"
    FILE_LABEL = "Images"        # label in the "Choose files" dialog
    FOUND_TEXT = "Found {files} file(s)."
    PROGRESS_TEXT = "{done} of {total}"

    PAD = {"padx": 10, "pady": 5}

    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill="both", expand=True)
        self.sources = []
        self.q = queue.Queue()
        self.running = False
        self.cancel = threading.Event()

        self.var_source = tk.StringVar(value=tr("No folder or files chosen"))
        self.var_recursive = tk.BooleanVar(value=False)
        self.var_out = tk.StringVar()
        self.var_open = tk.BooleanVar(value=True)
        self.var_status = tk.StringVar(value=tr("Ready"))
        self._build()

    # ---- hooks for modules
    def build_settings(self, frame):
        pass

    def get_opts(self):
        return {}

    def prepare(self, files, opts, base):
        return files

    def process(self, src, dest_dir, opts, index):
        raise NotImplementedError

    def on_sources_changed(self):
        pass

    def count_units(self, src, opts):
        """How many progress steps src takes (e.g. pages in a PDF). In process(), call
        opts["_tick"]() after each step and check opts["_cancelled"]() in long loops."""
        return 1

    # ---- layout
    def _build(self):
        pad = self.PAD
        src = ttk.LabelFrame(self, text=tr(self.SOURCE_TITLE), style="Section.TLabelframe", padding=8)
        src.pack(fill="x", pady=(0, 8))
        ttk.Button(src, text=tr("Choose folder…"), command=self.pick_folder).grid(row=0, column=0, **pad)
        ttk.Button(src, text=tr("Choose files…"), command=self.pick_files).grid(row=0, column=1, **pad)
        ttk.Checkbutton(src, text=tr("Include sub-folders"), variable=self.var_recursive,
                        command=self.on_sources_changed).grid(row=0, column=2, **pad)
        ttk.Label(src, textvariable=self.var_source, foreground="#52606d").grid(
            row=1, column=0, columnspan=4, sticky="w", padx=10)

        st = ttk.LabelFrame(self, text=tr("2. Settings"), style="Section.TLabelframe", padding=8)
        st.pack(fill="x", pady=(0, 8))
        self.build_settings(st)

        out = ttk.LabelFrame(self, text=tr("3. Save copies to"), style="Section.TLabelframe", padding=8)
        out.pack(fill="x", pady=(0, 8))
        out.columnconfigure(0, weight=1)
        ttk.Entry(out, textvariable=self.var_out).grid(row=0, column=0, sticky="ew", **pad)
        ttk.Button(out, text=tr("Browse…"), command=self.pick_out).grid(row=0, column=1, **pad)
        ttk.Checkbutton(out, text=tr("Open the folder when finished"), variable=self.var_open).grid(
            row=1, column=0, sticky="w", padx=10)

        run = ttk.Frame(self)
        run.pack(fill="x", pady=(2, 6))
        self.btn_run = ttk.Button(run, text=tr(self.RUN_LABEL), style="Accent.TButton", command=self.start)
        self.btn_run.pack(side="left")
        self.btn_stop = ttk.Button(run, text=tr("Stop"), command=self.stop, state="disabled")
        self.btn_stop.pack(side="left", padx=(8, 0))
        self.progress = ttk.Progressbar(run, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=14)
        ttk.Label(run, textvariable=self.var_status, width=30).pack(side="left")

        logf = ttk.Frame(self)
        logf.pack(fill="both", expand=True)
        self.log = tk.Text(logf, height=6, font=("Consolas", 9), relief="flat", bg="#f5f7fa",
                           state="disabled", wrap="none")
        sb = ttk.Scrollbar(logf, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        self.log.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    # ---- pickers
    def pick_folder(self):
        d = filedialog.askdirectory(title=tr("Choose a folder"))
        if d:
            self.sources = [d]
            self.var_source.set(tr("Folder: {path}", path=d))
            self.var_out.set(str(Path(d) / self.OUT_NAME))
            self.on_sources_changed()

    def pick_files(self):
        pattern = " ".join(f"*{e}" for e in sorted(self.EXTS))
        label = tr(self.FILE_LABEL)
        files = filedialog.askopenfilenames(title=tr("Choose files"),
                                            filetypes=[(label, pattern), (tr("All files"), "*.*")])
        if files:
            self.sources = list(files)
            self.var_source.set(tr("{n} file(s) selected in {path}", n=num(len(files)), path=Path(files[0]).parent))
            self.var_out.set(str(Path(files[0]).parent / self.OUT_NAME))
            self.on_sources_changed()

    def pick_out(self):
        d = filedialog.askdirectory(title=tr("Where should the copies go?"))
        if d:
            self.var_out.set(d)

    def current_files(self):
        """Files that a run would process right now (main thread, for previews)."""
        if not self.sources:
            return [], None
        base = base_of(self.sources)
        out_dir = Path(self.var_out.get().strip() or base / self.OUT_NAME)
        return collect_images(self.sources, self.var_recursive.get(), out_dir, self.EXTS), base

    # ---- run
    def _write(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def start(self):
        title = tr(self.NAME)
        if self.running:
            return
        if not self.sources:
            messagebox.showinfo(title, tr("Choose a folder or some files first."))
            return
        try:
            import PIL  # noqa: F401
        except ImportError:
            messagebox.showerror(title, tr("The Pillow library is missing.\nRun install.bat or:  pip install pillow"))
            return
        try:
            opts = self.get_opts()
        except ValueError as e:
            messagebox.showerror(title, str(e))
            return

        base = base_of(self.sources)
        out_dir = Path(self.var_out.get().strip() or base / self.OUT_NAME)
        if out_dir.resolve() == base.resolve():
            messagebox.showerror(title, tr("Please choose a different output folder than the one with your "
                                           "files, so the originals are never overwritten."))
            return

        opts.update(sources=list(self.sources), recursive=self.var_recursive.get())
        self.running = True
        self.cancel.clear()
        self.btn_run.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.progress.configure(value=0)
        self.var_status.set(tr("Working…"))
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

        def worker():
            try:
                self._run(opts, base, out_dir)
            except Exception as e:
                self.q.put(("error", str(e)))

        threading.Thread(target=worker, daemon=True).start()
        self.after(50, self._poll)

    def _run(self, opts, base, out_dir):
        emit = lambda k, p: self.q.put((k, p))  # noqa: E731
        out_dir.mkdir(parents=True, exist_ok=True)
        mark_output_folder(out_dir)
        files = collect_images(opts["sources"], opts["recursive"], out_dir, self.EXTS)
        files = self.prepare(files, opts, base)

        units = []
        for f in files:
            try:
                units.append(max(1, int(self.count_units(f, opts))))
            except Exception:
                units.append(1)
        emit("total", (len(files), sum(units)))

        done = 0

        def tick(n=1):
            nonlocal done
            done += n
            emit("progress", done)

        opts["_tick"] = tick
        opts["_cancelled"] = self.cancel.is_set

        ok = failed = skipped = saved = 0
        finished_units = 0
        for i, src in enumerate(files, 1):
            if self.cancel.is_set():
                break
            try:
                dest_dir = out_dir / rel_dir(base, src)
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest, msg = self.process(src, dest_dir, opts, i)
                line = f"✓ {src.name}"
                if dest.name != src.name:
                    line += f" → {dest.name}"
                if msg:
                    line += f"   {msg}"
                if self.SHOW_SIZES:
                    before, after = src.stat().st_size, dest.stat().st_size
                    saved += before - after
                    line += f"   {kb(before)} → {kb(after)}"
                emit("log", line)
                ok += 1
            except SkipFile as e:
                emit("log", f"– {src.name}: " + tr("skipped ({reason})", reason=e))
                skipped += 1
            except Exception as e:
                emit("log", f"✗ {src.name}: {e}")
                failed += 1
            finished_units += units[i - 1]
            if not self.cancel.is_set() and done != finished_units:
                done = finished_units  # modules that don't tick still move the bar
                emit("progress", done)
        emit("done", (ok, failed, skipped, saved, out_dir, self.cancel.is_set()))

    def _poll(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "total":
                    nfiles, nunits = payload
                    self.progress.configure(maximum=max(nunits, 1))
                    self._write(tr(self.FOUND_TEXT, files=num(nfiles), units=num(nunits)))
                elif kind == "progress":
                    self.progress.configure(value=payload)
                    self.var_status.set(tr(self.PROGRESS_TEXT, done=num(payload),
                                           total=num(int(self.progress["maximum"]))))
                elif kind == "log":
                    self._write(payload)
                elif kind == "error":
                    self._finish()
                    self.var_status.set(tr("Stopped with an error"))
                    self._write(tr("Error: {message}", message=payload))
                    messagebox.showerror(tr(self.NAME), payload)
                    return
                elif kind == "done":
                    ok, failed, skipped, saved, out_dir, stopped = payload
                    self._finish()
                    if stopped:
                        self.var_status.set(tr("Stopped"))
                        summary = tr("Stopped by you. Done: {ok}, failed: {failed}", ok=num(ok), failed=num(failed))
                    else:
                        self.var_status.set(tr("Finished: {ok} done, {failed} failed", ok=num(ok), failed=num(failed)))
                        summary = tr("Finished. Done: {ok}, failed: {failed}", ok=num(ok), failed=num(failed))
                    if skipped:
                        summary += tr(", skipped: {n}", n=num(skipped))
                    if self.SHOW_SIZES and ok:
                        summary += tr(". Saved {mb} MB", mb=dec(saved / 1048576))
                    self._write("\n" + summary + ".")
                    self._write(tr("Copies are in: {path}", path=out_dir.resolve()))
                    if ok and self.var_open.get() and hasattr(os, "startfile"):
                        os.startfile(out_dir)
                    return
        except queue.Empty:
            pass
        self.after(50, self._poll)

    def stop(self):
        if self.running:
            self.cancel.set()
            self.var_status.set(tr("Stopping…"))
            self.btn_stop.configure(state="disabled")

    def _finish(self):
        self.running = False
        self.btn_run.configure(state="normal")
        self.btn_stop.configure(state="disabled")


def copy_file(src, dest):
    shutil.copy2(src, dest)
    return dest
