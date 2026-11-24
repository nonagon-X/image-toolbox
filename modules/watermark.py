"""Toolbox module: add a text or logo watermark to images."""

import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk

from _common import (HINT, Choice, JobPanel, has_alpha, open_image, quality_slider, radio_row, save_image,
                     target_format)
from _i18n import tr

NAME = "Add Watermark"
DESCRIPTION = "Stamp a text or logo watermark on your images. Watermarked copies are made; originals stay as they are."
ORDER = 5

TILED = "Tiled (repeat across image)"
POSITIONS = ["Bottom right", "Bottom left", "Bottom centre", "Top right", "Top left", "Top centre",
             "Centre", TILED]
FONTS = ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"]


def load_font(size):
    from PIL import ImageFont

    for name in FONTS:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def make_mark(img_w, o):
    """Build the watermark as an RGBA image sized for an image img_w pixels wide."""
    from PIL import Image, ImageDraw

    target_w = max(8, int(img_w * o["size"] / 100))
    if o["kind"] == "text":
        probe = load_font(100)
        d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        w100 = max(1, d.textbbox((0, 0), o["text"], font=probe)[2])
        fs = max(8, int(100 * target_w / w100))
        font = load_font(fs)
        stroke = max(1, fs // 22) if o["outline"] else 0
        box = d.textbbox((0, 0), o["text"], font=font, stroke_width=stroke)
        mark = Image.new("RGBA", (box[2] - box[0], box[3] - box[1]), (0, 0, 0, 0))
        ImageDraw.Draw(mark).text((-box[0], -box[1]), o["text"], font=font, fill=o["color"] + (255,),
                                  stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
    else:
        logo = o["logo_img"]
        h = max(1, round(logo.height * target_w / logo.width))
        mark = logo.resize((target_w, h), Image.Resampling.LANCZOS)

    alpha = mark.getchannel("A").point(lambda a: a * o["opacity"] // 100)
    mark.putalpha(alpha)
    return mark


def apply_watermark(im, o):
    from PIL import Image

    base = im.convert("RGBA")
    W, H = base.size
    mark = make_mark(W, o)
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    m = int(min(W, H) * o["margin"] / 100)
    w, h = mark.size
    pos = o["position"]

    if pos == TILED:
        if o["kind"] == "text":
            mark = mark.rotate(30, expand=True, resample=Image.Resampling.BICUBIC)
            w, h = mark.size
        step_x, step_y = int(w * 1.5) + 1, int(h * 2.2) + 1
        for row, y in enumerate(range(-h // 2, H, step_y)):
            offset = (step_x // 2) if row % 2 else 0
            for x in range(-w // 2 - offset, W, step_x):
                layer.paste(mark, (x, y))  # tiles never overlap, so a plain paste keeps alpha exact
    else:
        if "left" in pos:
            x = m
        elif "right" in pos:
            x = W - w - m
        else:
            x = (W - w) // 2
        y = m if pos.startswith("Top") else (H - h - m if pos.startswith("Bottom") else (H - h) // 2)
        layer.paste(mark, (x, y))

    out = Image.alpha_composite(base, layer)
    return out if has_alpha(im) else out.convert("RGB")


class WatermarkPanel(JobPanel):
    NAME = NAME
    OUT_NAME = "watermarked"
    RUN_LABEL = "Add watermark"

    def build_settings(self, st):
        pad = {"padx": 10, "pady": 4}
        self.var_kind = tk.StringVar(value="text")
        self.var_text = tk.StringVar(value=tr("© Your Company"))
        self.var_logo = tk.StringVar()
        self.var_outline = tk.BooleanVar(value=True)
        self.var_size = tk.IntVar(value=25)
        self.var_opacity = tk.IntVar(value=60)
        self.var_margin = tk.IntVar(value=3)
        self.var_format = tk.StringVar(value="keep")
        self.var_quality = tk.IntVar(value=88)
        self.color = "#ffffff"

        radio_row(st, self.var_kind, [("Text", "text"), ("Logo image (PNG with transparency works best)", "logo")],
                  0, "Watermark", pad)

        ttk.Label(st, text=tr("Text")).grid(row=1, column=0, sticky="w", **pad)
        tf = ttk.Frame(st)
        tf.grid(row=1, column=1, columnspan=5, sticky="w", **pad)
        ttk.Entry(tf, textvariable=self.var_text, width=30).pack(side="left")
        self.swatch = tk.Label(tf, width=3, bg=self.color, relief="solid", bd=1)
        self.swatch.pack(side="left", padx=(10, 4))
        ttk.Button(tf, text=tr("Colour…"), command=self._pick_color).pack(side="left")
        ttk.Checkbutton(tf, text=tr("dark outline (readable on any photo)"),
                        variable=self.var_outline).pack(side="left", padx=10)

        ttk.Label(st, text=tr("Logo")).grid(row=2, column=0, sticky="w", **pad)
        lf = ttk.Frame(st)
        lf.grid(row=2, column=1, columnspan=5, sticky="w", **pad)
        ttk.Entry(lf, textvariable=self.var_logo, width=50).pack(side="left")
        ttk.Button(lf, text=tr("Choose logo…"), command=self._pick_logo).pack(side="left", padx=8)

        ttk.Label(st, text=tr("Size / opacity")).grid(row=3, column=0, sticky="w", **pad)
        sf = ttk.Frame(st)
        sf.grid(row=3, column=1, columnspan=5, sticky="w", **pad)
        for var, lo, hi, unit in [(self.var_size, 5, 90, "% of width"), (self.var_opacity, 10, 100, "% opacity")]:
            ttk.Scale(sf, from_=lo, to=hi, variable=var, length=140,
                      command=lambda v, var=var: var.set(round(float(v)))).pack(side="left")
            ttk.Label(sf, textvariable=var, width=3).pack(side="left", padx=(6, 0))
            ttk.Label(sf, text=tr(unit), foreground=HINT).pack(side="left", padx=(0, 18))

        ttk.Label(st, text=tr("Position")).grid(row=4, column=0, sticky="w", **pad)
        pf = ttk.Frame(st)
        pf.grid(row=4, column=1, columnspan=5, sticky="w", **pad)
        self.position = Choice(pf, POSITIONS, POSITIONS[0], width=28)
        self.position.widget.pack(side="left")
        ttk.Label(pf, text=tr("margin")).pack(side="left", padx=(14, 4))
        ttk.Spinbox(pf, from_=0, to=20, textvariable=self.var_margin, width=4).pack(side="left")
        ttk.Label(pf, text="%", foreground=HINT).pack(side="left", padx=(2, 18))
        ttk.Button(pf, text=tr("Preview on first image…"), command=self.preview).pack(side="left")

        radio_row(st, self.var_format, [("Keep original", "keep"), ("JPEG", "jpeg"), ("WebP", "webp"),
                                        ("PNG", "png")], 5, "Format", pad)
        quality_slider(st, self.var_quality, 6, hint="", pad=pad)

    def _pick_color(self):
        c = colorchooser.askcolor(color=self.color, title=tr("Watermark text colour"))
        if c and c[1]:
            self.color = c[1]
            self.swatch.configure(bg=self.color)

    def _pick_logo(self):
        f = filedialog.askopenfilename(title=tr("Choose your logo"),
                                       filetypes=[(tr("Images"), "*.png *.webp *.jpg *.jpeg *.gif"),
                                                  (tr("All files"), "*.*")])
        if f:
            self.var_logo.set(f)
            self.var_kind.set("logo")

    def get_opts(self):
        from PIL import Image

        h = self.color.lstrip("#")
        try:
            margin = int(self.var_margin.get())
        except (tk.TclError, ValueError):
            raise ValueError(tr("Margin must be a whole number."))
        o = {"kind": self.var_kind.get(), "text": self.var_text.get(), "outline": self.var_outline.get(),
             "color": tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)), "size": int(self.var_size.get()),
             "opacity": int(self.var_opacity.get()), "position": self.position.get(),
             "margin": max(0, margin), "format": self.var_format.get(), "quality": int(self.var_quality.get())}
        if o["kind"] == "text" and not o["text"].strip():
            raise ValueError(tr("Type the watermark text."))
        if o["kind"] == "logo":
            path = self.var_logo.get().strip()
            if not path or not Path(path).is_file():
                raise ValueError(tr("Choose a logo image file."))
            try:
                with Image.open(path) as logo:
                    o["logo_img"] = logo.convert("RGBA")
            except Exception as e:
                raise ValueError(tr("Could not open the logo: {error}", error=e))
        return o

    def preview(self):
        from PIL import ImageTk

        files, _base = self.current_files()
        if not files:
            messagebox.showinfo(tr(NAME), tr("Choose a folder or some files first."))
            return
        try:
            o = self.get_opts()
            im, _icc = open_image(files[0])
            im = apply_watermark(im, o)
        except ValueError as e:
            messagebox.showerror(tr(NAME), str(e))
            return
        except Exception as e:
            messagebox.showerror(tr(NAME), tr("Preview failed: {error}", error=e))
            return
        im.thumbnail((900, 650))
        win = tk.Toplevel(self)
        win.title(tr("Preview – {name}", name=files[0].name))
        photo = ImageTk.PhotoImage(im)
        lbl = tk.Label(win, image=photo)
        lbl.image = photo
        lbl.pack(padx=10, pady=10)
        ttk.Button(win, text=tr("Close"), command=win.destroy).pack(pady=(0, 10))

    def process(self, src, dest_dir, o, index):
        im, icc = open_image(src)
        out = apply_watermark(im, o)
        fmt = target_format(src.suffix, o["format"])
        dest = save_image(out, dest_dir / src.stem, fmt, o["quality"], icc=icc)
        kind = tr("text watermark") if o["kind"] == "text" else tr("logo watermark")
        return dest, f"{kind}, {tr(o['position']).split(' (')[0].lower()}"


def build(parent):
    return WatermarkPanel(parent)
