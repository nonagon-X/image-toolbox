# Toolbox

A simple Windows desktop app for preparing images for websites. Pick a module from the sidebar, click your options and run. **Your original files are never changed**: every module saves copies to a separate folder.

## Modules

| Module | What it does |
|---|---|
| **Resize Images** | Shrinks images to a web size (Full HD, Large, Medium, Small, Thumbnail or custom) while keeping the shape. Small images are never enlarged. |
| **Convert Format** | Converts to WebP, JPEG, PNG or AVIF at the same size. Lets you choose the background colour for transparent areas when saving as JPEG. |
| **Compress Only** | Makes files smaller while keeping the same size and format. Optionally reduces PNGs to 256 colours. Keeps the original if compressing doesn't make it smaller. |
| **Rename in Bulk** | Gives files clean, SEO-friendly names using a pattern like `{name}`, `my-photo-{n}` or `{date}-{n}`, with a live preview. |
| **Add Watermark** | Adds a text or logo watermark. You can set the position (corners, centre or tiled), size, opacity and colour, and preview it on the first image. |

Every module also:
- works on a whole folder or on files you pick, with an option to include sub-folders (the folder layout is kept in the output)
- turns phone photos the right way up and keeps their colour profiles
- removes hidden photo data (camera details and GPS location) by default, which is good for privacy
- shows progress and the size of each file before and after
- never re-processes its own output folders

## Requirements

- Windows 10 or 11
- [Python 3.10+](https://www.python.org/downloads/) (with tkinter, which is included by default)
- [Pillow](https://pypi.org/project/pillow/), which the installer adds for you
- Optional: `pip install pillow-heif` to open iPhone `.heic` photos

## Install

1. Download or clone this repository.
2. Double-click **`install.bat`**.

This installs Pillow if it's missing and adds a **Toolbox** shortcut to your Desktop and Start Menu.

You can also start the app without installing: double-click `Start Toolbox.bat`, or run `pythonw toolbox.pyw`.

## Adding a module

Drop a new `.py` file into `modules/`. It appears in the sidebar automatically if it defines:

```python
NAME = "My Tool"
DESCRIPTION = "One line shown under the title."
ORDER = 10            # position in the sidebar (lower comes first)

def build(parent):    # create the module's interface inside parent (a ttk.Frame)
    ...
```

For image tasks, subclass `JobPanel` from `modules/_common.py`. It already provides the image picker, output folder, Run button, progress bar, log and background thread, so you only write `build_settings()`, `get_opts()` and `process()`. See `modules/compress.py` for a short example.

## Project layout

```
toolbox.pyw          main window, finds and loads modules
install.py / .bat    installs Pillow, creates shortcuts
Start Toolbox.bat    starts the app without a console window
modules/
  _common.py         shared image helpers and the JobPanel base class
  resize.py          Resize Images
  convert.py         Convert Format
  compress.py        Compress Only
  rename.py          Rename in Bulk
  watermark.py       Add Watermark
```

## License

[MIT](LICENSE)
