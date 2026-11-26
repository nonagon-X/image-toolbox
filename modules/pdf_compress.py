"""Toolbox module: make scanned PDFs smaller by re-saving every page as a lighter image."""

import shutil
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from _common import (HINT, JobPanel, SkipFile, dest_path, quality_slider, radio_row, replace_file,
                     temp_path)
from _i18n import num, tr

NAME = "Compress PDF"
DESCRIPTION = ("Make scanned PDFs much smaller by lowering the resolution and image quality of each page. "
               "Choose whether to save copies or replace the originals.")
ORDER = 7

DPIS = ["72", "100", "120", "150", "200", "300"]
MAX_SIDE = 20000  # safety limit per page, in pixels


def pdfium():
    try:
        import pypdfium2
        return pypdfium2
    except ImportError:
        raise ValueError(tr("The PDF library is missing.\nRun install.bat again, or:  pip install pypdfium2"))


def has_text(pdf, max_pages=5):
    """True when one of the first pages has selectable text (a digital PDF or an OCR'd scan)."""
    for i in range(min(len(pdf), max_pages)):
        page = pdf[i]
        try:
            tp = page.get_textpage()
            try:
                if tp.count_chars() > 0:
                    return True
            finally:
                tp.close()
        finally:
            page.close()
    return False


class PdfCompressPanel(JobPanel):
    NAME = NAME
    OUT_NAME = "smaller_pdfs"
    RUN_LABEL = "Compress PDF"
    EXTS = {".pdf"}
    SOURCE_TITLE = "1. Choose PDF files"
    FILE_LABEL = "PDF files"
    FOUND_TEXT = "Found {files} PDF file(s), {units} page(s) to process."
    PROGRESS_TEXT = "page {done} of {total}"
    OUTPUT_CHOICE = True
    DEFAULT_SUFFIX = "_small"

    def build_settings(self, st):
        pad = self.PAD
        self.var_dpi = tk.StringVar(value="150")
        self.var_colour = tk.StringVar(value="colour")
        self.var_quality = tk.IntVar(value=70)
        self.var_keep_smaller = tk.BooleanVar(value=True)
        self.var_skip_text = tk.BooleanVar(value=True)

        ttk.Label(st, text=tr("Resolution")).grid(row=0, column=0, sticky="w", **pad)
        rf = ttk.Frame(st)
        rf.grid(row=0, column=1, columnspan=5, sticky="w", **pad)
        ttk.Combobox(rf, textvariable=self.var_dpi, values=DPIS, width=5).pack(side="left")
        ttk.Label(rf, text=tr("DPI   (150 = easy to read and print, 100 = smallest; scanners often use 300–600)"),
                  foreground=HINT).pack(side="left", padx=8)

        radio_row(st, self.var_colour, [("Colour", "colour"),
                                        ("Greyscale (much smaller for text documents)", "grey")], 1, "Colours")
        quality_slider(st, self.var_quality, 2, hint="(60–75 is usually fine for scans)")
        ttk.Checkbutton(st, text=tr("If the result isn't smaller, keep the original file"),
                        variable=self.var_keep_smaller).grid(row=3, column=0, columnspan=6, sticky="w", **pad)
        ttk.Checkbutton(st, text=tr("Skip PDFs with selectable text (they are not plain scans; "
                                    "compressing would turn their text into pictures)"),
                        variable=self.var_skip_text).grid(row=4, column=0, columnspan=6, sticky="w", **pad)

    def get_opts(self):
        pdfium()  # fail early with a clear message if the library is missing
        try:
            dpi = int(float(self.var_dpi.get()))
        except ValueError:
            raise ValueError(tr("DPI must be a number."))
        if not 50 <= dpi <= 600:
            raise ValueError(tr("DPI must be between 50 and 600."))
        return {"dpi": dpi, "gray": self.var_colour.get() == "grey", "quality": int(self.var_quality.get()),
                "keep_smaller": self.var_keep_smaller.get(), "skip_text": self.var_skip_text.get()}

    def count_units(self, src, o):
        pdf = pdfium().PdfDocument(str(src))
        try:
            return len(pdf)
        finally:
            pdf.close()

    # ---- work
    def process(self, src, dest_dir, o, index):
        lib = pdfium()
        dest = dest_path(src, dest_dir, o)
        tmp = temp_path(dest)
        work = Path(tempfile.mkdtemp(prefix="toolbox-pdf-"))
        try:
            try:
                pdf = lib.PdfDocument(str(src))
            except Exception:
                raise SkipFile(tr("can't open it: password-protected or damaged"))
            try:
                if o["skip_text"] and has_text(pdf):
                    raise SkipFile(tr("it has selectable text, so it is not a plain scan"))
                self._rebuild(lib, pdf, work, tmp, o)
            finally:
                pdf.close()  # must be closed before the original can be replaced
            if o["_cancelled"]():
                raise SkipFile(tr("stopped"))

            if o["keep_smaller"] and tmp.stat().st_size >= src.stat().st_size:
                tmp.unlink()
                if o["out_mode"] == "overwrite":
                    return src, tr("already small — original kept")
                shutil.copy2(src, dest)
                return dest, tr("already small — original copied")
            return replace_file(tmp, dest), ""
        finally:
            if tmp.exists():
                tmp.unlink()
            shutil.rmtree(work, ignore_errors=True)

    def _rebuild(self, lib, pdf, work, out_path, o):
        """Render each page to a JPEG and put the JPEGs into a new PDF of the same page size."""
        out = lib.PdfDocument.new()
        try:
            for i in range(len(pdf)):
                if o["_cancelled"]():
                    return
                page = pdf[i]
                try:
                    w, h = page.get_size()  # in points, already turned for rotated pages
                    scale = o["dpi"] / 72
                    biggest = max(w, h) * scale
                    if biggest > MAX_SIDE:
                        scale *= MAX_SIDE / biggest
                    im = page.render(scale=scale, grayscale=o["gray"]).to_pil()
                finally:
                    page.close()
                im = im.convert("L" if o["gray"] else "RGB")
                jpg = work / f"p{i:05d}.jpg"
                im.save(jpg, "JPEG", quality=o["quality"], optimize=True, dpi=(o["dpi"], o["dpi"]))
                del im

                new_page = out.new_page(w, h)
                img = lib.PdfImage.new(out)
                img.load_jpeg(str(jpg), inline=False, autoclose=True)
                img.set_matrix(lib.PdfMatrix().scale(w, h))
                new_page.insert_obj(img)
                new_page.gen_content()
                new_page.close()
                o["_tick"]()
            out.save(str(out_path))
        finally:
            out.close()


def build(parent):
    return PdfCompressPanel(parent)
