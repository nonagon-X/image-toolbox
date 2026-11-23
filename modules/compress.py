"""Toolbox module: make image files smaller without changing size or format."""

import shutil
import tkinter as tk
from tkinter import ttk

from _common import HINT, JobPanel, SkipFile, open_image, quality_slider, save_image

NAME = "Compress Only"
DESCRIPTION = "Shrink file sizes while keeping the same dimensions and format. The originals are left untouched."
ORDER = 3

FORMATS = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".webp": "webp", ".avif": "avif"}


class CompressPanel(JobPanel):
    NAME = NAME
    OUT_NAME = "compressed"
    RUN_LABEL = "Compress images"
    EXTS = set(FORMATS)

    def build_settings(self, st):
        pad = self.PAD
        self.var_quality = tk.IntVar(value=78)
        self.var_png = tk.BooleanVar(value=False)
        self.var_keep_smaller = tk.BooleanVar(value=True)
        self.var_exif = tk.BooleanVar(value=False)

        quality_slider(st, self.var_quality, 0, hint="(JPEG / WebP / AVIF — 70–80 is usually invisible)")
        ttk.Checkbutton(st, text="PNG: reduce to 256 colours (much smaller; fine for logos and graphics, "
                                 "can band on photos)", variable=self.var_png).grid(
            row=1, column=0, columnspan=6, sticky="w", **pad)
        ttk.Checkbutton(st, text="If compressing makes a file bigger, keep the original file instead",
                        variable=self.var_keep_smaller).grid(row=2, column=0, columnspan=6, sticky="w", **pad)
        ttk.Checkbutton(st, text="Keep photo info (camera, date, GPS location)",
                        variable=self.var_exif).grid(row=3, column=0, columnspan=6, sticky="w", **pad)
        ttk.Label(st, text="Supports JPEG, PNG, WebP and AVIF. Use Convert Format for other types.",
                  foreground=HINT).grid(row=4, column=0, columnspan=6, sticky="w", padx=10)

    def get_opts(self):
        return {"quality": int(self.var_quality.get()), "png_colors": 256 if self.var_png.get() else None,
                "keep_smaller": self.var_keep_smaller.get(), "exif": self.var_exif.get()}

    def process(self, src, dest_dir, o, index):
        fmt = FORMATS.get(src.suffix.lower())
        if not fmt:
            raise SkipFile("format not supported here")
        im, icc = open_image(src)
        exif = im.info.get("exif") if o["exif"] else None
        dest = save_image(im, dest_dir / src.stem, fmt, o["quality"], icc=icc, exif=exif,
                          png_colors=o["png_colors"], ext=src.suffix)
        if o["keep_smaller"] and dest.stat().st_size >= src.stat().st_size:
            shutil.copy2(src, dest)
            return dest, "already well compressed — original kept"
        saved = 100 - dest.stat().st_size * 100 // max(src.stat().st_size, 1)
        return dest, f"-{saved}%"


def build(parent):
    return CompressPanel(parent)
