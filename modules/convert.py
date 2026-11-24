"""Toolbox module: convert images to another format (same size)."""

import tkinter as tk
from tkinter import colorchooser, ttk

from _common import HINT, JobPanel, SkipFile, has_alpha, open_image, quality_slider, radio_row, save_image
from _i18n import tr

NAME = "Convert Format"
DESCRIPTION = "Change images to JPEG, PNG, WebP or AVIF, keeping their size. The originals are left untouched."
ORDER = 2


class ConvertPanel(JobPanel):
    NAME = NAME
    OUT_NAME = "converted"
    RUN_LABEL = "Convert images"

    def build_settings(self, st):
        pad = self.PAD
        self.var_format = tk.StringVar(value="webp")
        self.var_quality = tk.IntVar(value=85)
        self.var_skip_same = tk.BooleanVar(value=True)
        self.bg = "#ffffff"

        radio_row(st, self.var_format, [("WebP (best for websites)", "webp"), ("JPEG", "jpeg"),
                                        ("PNG (lossless)", "png"), ("AVIF (smallest, newer)", "avif")],
                  0, "Convert to")
        quality_slider(st, self.var_quality, 1, hint="(not used for PNG)")

        ttk.Label(st, text=tr("Transparent areas")).grid(row=2, column=0, sticky="w", **pad)
        f = ttk.Frame(st)
        f.grid(row=2, column=1, columnspan=5, sticky="w", **pad)
        self.swatch = tk.Label(f, width=3, bg=self.bg, relief="solid", bd=1)
        self.swatch.pack(side="left")
        ttk.Button(f, text=tr("Pick colour…"), command=self._pick_bg).pack(side="left", padx=8)
        ttk.Label(f, text=tr("JPEG can't be transparent, so see-through areas get this colour"),
                  foreground=HINT).pack(side="left")

        ttk.Checkbutton(st, text=tr("Skip images that are already in the chosen format"),
                        variable=self.var_skip_same).grid(row=3, column=0, columnspan=6, sticky="w", **pad)

    def _pick_bg(self):
        c = colorchooser.askcolor(color=self.bg, title=tr("Background colour for transparent areas"))
        if c and c[1]:
            self.bg = c[1]
            self.swatch.configure(bg=self.bg)

    def get_opts(self):
        h = self.bg.lstrip("#")
        return {"format": self.var_format.get(), "quality": int(self.var_quality.get()),
                "bg": tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)), "skip_same": self.var_skip_same.get()}

    def process(self, src, dest_dir, o, index):
        fmt = o["format"]
        same = {"jpeg": (".jpg", ".jpeg"), "png": (".png",), "webp": (".webp",), "avif": (".avif",)}[fmt]
        if o["skip_same"] and src.suffix.lower() in same:
            raise SkipFile(tr("already {format}", format=fmt.upper()))
        im, icc = open_image(src)
        note = tr(" (transparency filled)") if fmt == "jpeg" and has_alpha(im) else ""
        dest = save_image(im, dest_dir / src.stem, fmt, o["quality"], icc=icc, bg=o["bg"])
        return dest, f"{src.suffix[1:].upper()} → {fmt.upper()}{note}"


def build(parent):
    return ConvertPanel(parent)
