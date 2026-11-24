"""Toolbox module: turn PDF pages into images. Handles big PDFs page by page."""

import re
import tkinter as tk
from tkinter import ttk

from _common import HINT, JobPanel, SkipFile, quality_slider, radio_row, save_image

NAME = "PDF to Images"
DESCRIPTION = "Save PDF pages as JPEG, PNG or WebP images at the size you choose. The PDF is left untouched."
ORDER = 6

WIDTHS = ["800", "1200", "1600", "1920", "2480", "3508"]
DPIS = ["72", "96", "150", "200", "300", "600"]
MAX_SIDE = 20000  # safety limit per page, in pixels


def pdfium():
    try:
        import pypdfium2
        return pypdfium2
    except ImportError:
        raise ValueError("The PDF library is missing.\nRun install.bat again, or:  pip install pypdfium2")


def parse_pages(text):
    """'all' / '' / '1-5, 8, 10-' → list of (start, end) ranges (1-based, end None = last page)."""
    text = text.strip().lower()
    if text in ("", "all"):
        return [(1, None)]
    ranges = []
    for part in re.split(r"[,;\s]+", text):
        if not part:
            continue
        m = re.fullmatch(r"(\d+)?-(\d+)?|(\d+)", part)
        if not m or part == "-":
            raise ValueError(f'"{part}" is not a valid page or range. Use e.g. 1-5, 8, 10-')
        if m.group(3):
            ranges.append((int(m.group(3)), int(m.group(3))))
        else:
            start, end = int(m.group(1) or 1), int(m.group(2)) if m.group(2) else None
            if end is not None and end < start:
                raise ValueError(f'"{part}": the first page must not be after the last.')
            ranges.append((start, end))
    return ranges


def select_pages(ranges, count):
    pages = []
    for start, end in ranges:
        for n in range(max(1, start), min(count, end or count) + 1):
            if n not in pages:
                pages.append(n)
    return pages


def page_scale(width_pt, height_pt, o):
    scale = (o["width"] / width_pt) if o["mode"] == "width" else (o["dpi"] / 72)
    biggest = max(width_pt, height_pt) * scale
    if biggest > MAX_SIDE:
        scale *= MAX_SIDE / biggest
    return scale


class PdfPanel(JobPanel):
    NAME = NAME
    OUT_NAME = "pdf_images"
    RUN_LABEL = "Convert PDF"
    EXTS = {".pdf"}
    SHOW_SIZES = False
    UNIT = "page"
    SOURCE_TITLE = "1. Choose PDF files"
    FILE_LABEL = "PDF files"

    def build_settings(self, st):
        pad = self.PAD
        self.var_mode = tk.StringVar(value="width")
        self.var_width = tk.StringVar(value="1600")
        self.var_dpi = tk.StringVar(value="150")
        self.var_pages = tk.StringVar(value="all")
        self.var_format = tk.StringVar(value="jpeg")
        self.var_quality = tk.IntVar(value=90)
        self.var_gray = tk.BooleanVar(value=False)
        self.var_folder = tk.BooleanVar(value=True)
        self.var_estimate = tk.StringVar(value="")
        self._after = None

        ttk.Label(st, text="Image size").grid(row=0, column=0, sticky="w", **pad)
        sf = ttk.Frame(st)
        sf.grid(row=0, column=1, columnspan=5, sticky="w", **pad)
        ttk.Radiobutton(sf, text="Width", value="width", variable=self.var_mode).pack(side="left")
        ttk.Combobox(sf, textvariable=self.var_width, values=WIDTHS, width=7).pack(side="left", padx=4)
        ttk.Label(sf, text="px", foreground=HINT).pack(side="left", padx=(0, 22))
        ttk.Radiobutton(sf, text="Resolution", value="dpi", variable=self.var_mode).pack(side="left")
        ttk.Combobox(sf, textvariable=self.var_dpi, values=DPIS, width=5).pack(side="left", padx=4)
        ttk.Label(sf, text="DPI   (150 = screen, 300 = print)", foreground=HINT).pack(side="left")

        ttk.Label(st, textvariable=self.var_estimate, foreground="#2f80ed").grid(
            row=1, column=1, columnspan=5, sticky="w", padx=10)

        ttk.Label(st, text="Pages").grid(row=2, column=0, sticky="w", **pad)
        pf = ttk.Frame(st)
        pf.grid(row=2, column=1, columnspan=5, sticky="w", **pad)
        ttk.Entry(pf, textvariable=self.var_pages, width=22).pack(side="left")
        ttk.Label(pf, text='"all", or e.g.  1-5, 8, 10-   (10- means page 10 to the end)',
                  foreground=HINT).pack(side="left", padx=10)

        radio_row(st, self.var_format, [("JPEG (smallest for photos/scans)", "jpeg"),
                                        ("PNG (sharpest text)", "png"), ("WebP", "webp")], 3, "Format")
        quality_slider(st, self.var_quality, 4, hint="(not used for PNG; 85–92 keeps text crisp)")

        of = ttk.Frame(st)
        of.grid(row=5, column=0, columnspan=6, sticky="w", **pad)
        ttk.Checkbutton(of, text="Greyscale (smaller files for text documents)",
                        variable=self.var_gray).pack(side="left", padx=(0, 18))
        ttk.Checkbutton(of, text="Put each PDF's pages in its own folder",
                        variable=self.var_folder).pack(side="left")

        for v in (self.var_mode, self.var_width, self.var_dpi):
            v.trace_add("write", lambda *a: self._schedule_estimate())

    # ---- size estimate shown under the size options
    def on_sources_changed(self):
        self._schedule_estimate()

    def _schedule_estimate(self):
        if self._after:
            self.after_cancel(self._after)
        self._after = self.after(300, self._update_estimate)

    def _update_estimate(self):
        self._after = None
        if self.running:
            return
        files, _ = self.current_files()
        if not files:
            self.var_estimate.set("")
            return
        try:
            o = self._size_opts()
            pdf = pdfium().PdfDocument(str(files[0]))
            try:
                w, h = pdf[0].get_size()
                count = len(pdf)
            finally:
                pdf.close()
            s = page_scale(w, h, o)
            total = sum(self._page_count(f) for f in files) if len(files) <= 50 else None
            msg = f"Page 1 of {files[0].name} → ≈ {round(w * s):,} × {round(h * s):,} px   ({count:,} pages"
            if len(files) > 1 and total is not None:
                msg += f"; {total:,} pages in {len(files)} PDFs"
            self.var_estimate.set(msg + ")")
        except Exception as e:
            self.var_estimate.set(f"Can't read {files[0].name}: {e}" if "PDF" not in str(e) else str(e))

    def _page_count(self, path):
        pdf = pdfium().PdfDocument(str(path))
        try:
            return len(pdf)
        finally:
            pdf.close()

    # ---- options
    def _size_opts(self):
        try:
            width, dpi = int(float(self.var_width.get())), int(float(self.var_dpi.get()))
        except ValueError:
            raise ValueError("Width and DPI must be numbers.")
        if self.var_mode.get() == "width" and not 50 <= width <= MAX_SIDE:
            raise ValueError(f"Width must be between 50 and {MAX_SIDE:,} px.")
        if self.var_mode.get() == "dpi" and not 20 <= dpi <= 1200:
            raise ValueError("DPI must be between 20 and 1200.")
        return {"mode": self.var_mode.get(), "width": width, "dpi": dpi}

    def get_opts(self):
        pdfium()  # fail early with a clear message if the library is missing
        o = self._size_opts()
        o.update(ranges=parse_pages(self.var_pages.get()), format=self.var_format.get(),
                 quality=int(self.var_quality.get()), gray=self.var_gray.get(),
                 own_folder=self.var_folder.get())
        return o

    def count_units(self, src, o):
        return len(select_pages(o["ranges"], self._page_count(src))) or 1

    # ---- work
    def process(self, src, dest_dir, o, index):
        lib = pdfium()
        try:
            pdf = lib.PdfDocument(str(src))
        except Exception:
            raise SkipFile("can't open it: password-protected or damaged")
        try:
            pages = select_pages(o["ranges"], len(pdf))
            if not pages:
                raise SkipFile(f"it has only {len(pdf)} page(s), none in the chosen range")
            folder = dest_dir / src.stem if o["own_folder"] else dest_dir
            folder.mkdir(parents=True, exist_ok=True)
            digits = max(3, len(str(len(pdf))))
            first = None
            done = 0
            for n in pages:
                if o["_cancelled"]():
                    break
                page = pdf[n - 1]
                try:
                    w, h = page.get_size()
                    bitmap = page.render(scale=page_scale(w, h, o), grayscale=o["gray"])
                    im = bitmap.to_pil()
                finally:
                    page.close()
                if o["gray"] and im.mode != "L":
                    im = im.convert("L")
                dest = save_image(im, folder / f"{src.stem}-p{n:0{digits}d}", o["format"], o["quality"])
                first = first or im.size
                done += 1
                o["_tick"]()
        finally:
            pdf.close()
        stopped = " (stopped)" if done < len(pages) else ""
        return folder, f"{done:,} page(s) → {first[0]}×{first[1]} px{stopped}" if first else "no pages saved"


def build(parent):
    return PdfPanel(parent)
