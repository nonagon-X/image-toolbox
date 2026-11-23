"""Toolbox module: resize images for websites. Originals are never modified."""

import tkinter as tk
from tkinter import ttk

from _common import HINT, JobPanel, open_image, quality_slider, radio_row, save_image, target_format

NAME = "Resize Images"
DESCRIPTION = "Make web-ready copies of your images at a smaller size. The originals are left untouched."
ORDER = 1

PRESETS = {
    "Full HD (1920 px)": 1920,
    "Large (1600 px)": 1600,
    "Medium (1200 px)": 1200,
    "Small (800 px)": 800,
    "Thumbnail (400 px)": 400,
    "Custom": None,
}


class ResizePanel(JobPanel):
    NAME = NAME
    OUT_NAME = "web_resized"
    RUN_LABEL = "Resize images"

    def build_settings(self, st):
        pad = self.PAD
        self.var_preset = tk.StringVar(value="Full HD (1920 px)")
        self.var_w = tk.IntVar(value=1920)
        self.var_h = tk.IntVar(value=1920)
        self.var_format = tk.StringVar(value="keep")
        self.var_quality = tk.IntVar(value=82)
        self.var_suffix = tk.StringVar()

        ttk.Label(st, text="Size").grid(row=0, column=0, sticky="w", **pad)
        cb = ttk.Combobox(st, textvariable=self.var_preset, values=list(PRESETS), state="readonly", width=20)
        cb.grid(row=0, column=1, sticky="w", **pad)
        cb.bind("<<ComboboxSelected>>", self._on_preset)
        ttk.Label(st, text="Max width").grid(row=0, column=2, sticky="e", **pad)
        self.sp_w = ttk.Spinbox(st, from_=50, to=10000, increment=50, textvariable=self.var_w, width=7,
                                state="disabled")
        self.sp_w.grid(row=0, column=3, sticky="w")
        ttk.Label(st, text="Max height").grid(row=0, column=4, sticky="e", **pad)
        self.sp_h = ttk.Spinbox(st, from_=50, to=10000, increment=50, textvariable=self.var_h, width=7,
                                state="disabled")
        self.sp_h.grid(row=0, column=5, sticky="w")

        radio_row(st, self.var_format, [("Keep original", "keep"), ("JPEG", "jpeg"),
                                        ("WebP (smallest)", "webp"), ("PNG", "png")], 1, "Format")
        quality_slider(st, self.var_quality, 2)

        ttk.Label(st, text="Name suffix").grid(row=3, column=0, sticky="w", **pad)
        ttk.Entry(st, textvariable=self.var_suffix, width=12).grid(row=3, column=1, sticky="w", **pad)
        ttk.Label(st, text='optional, e.g. "_web" → photo_web.jpg', foreground=HINT).grid(
            row=3, column=2, columnspan=4, sticky="w")

    def _on_preset(self, _=None):
        size = PRESETS[self.var_preset.get()]
        state = "normal" if size is None else "disabled"
        self.sp_w.configure(state=state)
        self.sp_h.configure(state=state)
        if size:
            self.var_w.set(size)
            self.var_h.set(size)

    def get_opts(self):
        try:
            w, h = int(self.var_w.get()), int(self.var_h.get())
        except (tk.TclError, ValueError):
            w = h = 0
        if w <= 0 or h <= 0:
            raise ValueError("Width and height must be whole numbers above 0.")
        return {"width": w, "height": h, "quality": int(self.var_quality.get()),
                "format": self.var_format.get(), "suffix": self.var_suffix.get().strip()}

    def process(self, src, dest_dir, o, index):
        from PIL import Image

        im, icc = open_image(src)
        old = im.size
        if im.width > o["width"] or im.height > o["height"]:
            im.thumbnail((o["width"], o["height"]), Image.Resampling.LANCZOS)
        fmt = target_format(src.suffix, o["format"])
        dest = save_image(im, dest_dir / (src.stem + o["suffix"]), fmt, o["quality"], icc=icc)
        return dest, f"{old[0]}×{old[1]} → {im.width}×{im.height}"


def build(parent):
    return ResizePanel(parent)
