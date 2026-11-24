"""Draws the Toolbox icon (assets/toolbox.ico + toolbox.png). Run once: python assets/make_icon.py"""

from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
S = 1024  # draw big, then scale down for crisp small sizes


def draw():
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # rounded blue tile
    d.rounded_rectangle((40, 40, S - 40, S - 40), radius=210, fill=(47, 128, 237, 255))
    # photo frame
    d.rounded_rectangle((210, 270, S - 210, S - 270), radius=60, fill=(255, 255, 255, 255))
    # mountains and sun inside the frame
    d.polygon([(260, 700), (450, 470), (600, 640), (680, 560), (S - 260, 700)], fill=(31, 41, 51, 255))
    d.ellipse((610, 340, 720, 450), fill=(255, 196, 0, 255))
    # small "resize" corner arrow
    d.polygon([(S - 330, S - 160), (S - 160, S - 160), (S - 160, S - 330)], fill=(255, 255, 255, 255))
    return im


if __name__ == "__main__":
    big = draw()
    big.resize((256, 256), Image.Resampling.LANCZOS).save(HERE / "toolbox.png")
    big.save(HERE / "toolbox.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("Saved", HERE / "toolbox.ico")
