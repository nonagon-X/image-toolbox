# Toolbox

A simple Windows desktop app for preparing images for websites and shrinking scanned PDFs. Pick a module from the sidebar, click your options and run. **Your original files are never changed** unless you ask for it: the image modules save copies to a separate folder, and Compress PDF saves copies unless you choose to overwrite.

Available in **English** and **Polish** (Polski). Switch at the bottom of the sidebar. On a Polish Windows, it starts in Polish automatically.

## Modules

| Module | What it does |
|---|---|
| **Resize Images** | Shrinks images to a web size (Full HD, Large, Medium, Small, Thumbnail or custom) while keeping the shape. Small images are never enlarged. |
| **Convert Format** | Converts to WebP, JPEG, PNG or AVIF at the same size. Lets you choose the background colour for transparent areas when saving as JPEG. |
| **Compress Only** | Makes files smaller while keeping the same size and format. Optionally reduces PNGs to 256 colours. Keeps the original if compressing doesn't make it smaller. |
| **Rename in Bulk** | Gives files clean, SEO-friendly names using a pattern like `{name}`, `my-photo-{n}` or `{date}-{n}`, with a live preview. Polish letters become plain ones (`Łódź` → `lodz`). |
| **Add Watermark** | Adds a text or logo watermark. You can set the position (corners, centre or tiled), size, opacity and colour, and preview it on the first image. |
| **PDF to Images** | Saves PDF pages as JPEG, PNG or WebP. Set the size by width in pixels or by DPI, pick pages (`all`, `1-5, 8, 10-`), and optionally use greyscale. Works through big PDFs one page at a time, with page-by-page progress and a Stop button. |
| **Compress PDF** | Makes scanned PDFs much smaller by re-saving each page at a lower resolution (DPI) and JPEG quality, in colour or greyscale, with the same page size. Saves copies next to the originals or in a folder, with a prefix and/or suffix you type (default `_small`, e.g. `scan_small.pdf`), or overwrites the originals after asking. By default it skips PDFs with selectable text, which aren't plain scans, and keeps the original if the result isn't smaller. |

Every module also:
- works on a whole folder or on files you pick, with an option to include sub-folders (the folder layout is kept in the output)
- turns phone photos the right way up and keeps their colour profiles
- removes hidden photo data (camera details and GPS location) by default, which is good for privacy
- shows progress and the size of each file before and after, with a Stop button
- never re-processes its own output folders

## Install: the easy way

1. Download **`ToolboxSetup.exe`** from the [Releases](../../releases) page.
2. Run it. It installs Toolbox for your Windows user (no administrator rights needed) and adds it to the Start Menu, and to the Desktop if you tick that box. Python and all the libraries are inside.

Toolbox then appears in **Settings → Apps → Installed apps**, where you can uninstall it like any other program.

**Updating:** click **Check for updates** at the bottom of the sidebar. If there is a newer version, Toolbox downloads the new installer, closes itself and installs the update over the old version. You can also download and run the newer `ToolboxSetup.exe` yourself.

**Portable version:** if you'd rather not install anything, download **`Toolbox.exe`** instead and keep it anywhere, for example on a USB stick. It works the same, but it doesn't appear in Installed apps and updates itself only by opening the download page.

Because the files aren't code-signed, Windows may show *"Windows protected your PC"* the first time. Click **More info → Run anyway**.

## Install: from source (for developers)

Needs [Python 3.10+](https://www.python.org/downloads/) on Windows 10 or 11.

1. Clone this repository.
2. Double-click **`install.bat`**. It installs [Pillow](https://pypi.org/project/pillow/) and [pypdfium2](https://pypi.org/project/pypdfium2/) (the PDF engine used in Chrome) and adds a **Toolbox** shortcut to your Desktop and Start Menu.

Optional: `pip install pillow-heif` to open iPhone `.heic` photos (source version only).

### Building Toolbox.exe yourself

```
pip install pyinstaller
python build.py              (or double-click build.bat)
```

The exe appears in `dist/`. To check that a build works, without opening any windows:

```
dist\Toolbox.exe --selftest report.txt
```

## Adding a module

Drop a new `.py` file into `modules/`. It appears in the sidebar automatically if it defines:

```python
NAME = "My Tool"
DESCRIPTION = "One line shown under the title."
ORDER = 10            # position in the sidebar (lower comes first)

def build(parent):    # create the module's interface inside parent (a ttk.Frame)
    ...
```

`Toolbox.exe` also loads extra modules from a `modules` folder placed next to the exe.

For image tasks, subclass `JobPanel` from `modules/_common.py`. It already provides the file picker, output folder, Run and Stop buttons, progress bar, log and background thread, so you only write `build_settings()`, `get_opts()` and `process()`. For long jobs, add `count_units()` and call `opts["_tick"]()` after each step, as `pdf_to_images.py` does, so you get detailed progress and the Stop button works partway through a file. See `modules/compress.py` for a short example. To let people overwrite their originals or save copies next to them with a prefix or suffix, set `OUTPUT_CHOICE = True` and write through `dest_path()`, `temp_path()` and `replace_file()`, as `pdf_compress.py` does.

## Translations

Write all visible text in English inside `tr()`, for example `tr("Choose folder…")` or `tr("Found {files} file(s).", files=n)`. Polish texts live in `modules/_lang_pl.py`, which maps each English text to its Polish version; any text missing there shows in English. To add another language, create `modules/_lang_xx.py` with a `TEXTS` dictionary and add it to `LANGS` in `modules/_i18n.py`.

## Project layout

```
toolbox.pyw          main window, finds and loads modules, --selftest
install.py / .bat    installs the libraries, creates shortcuts (source version)
build.py / .bat      builds dist/Toolbox.exe, and dist/ToolboxSetup.exe when Inno Setup is installed
installer/Toolbox.iss  Inno Setup script for the installer (keep its AppId unchanged)
Start Toolbox.bat    starts the source version without a console window
assets/              app icon (make_icon.py draws it)
modules/
  _common.py         shared image helpers and the JobPanel base class
  _i18n.py           translation helpers (tr, number formats, language setting)
  _lang_pl.py        Polish texts
  resize.py          Resize Images
  convert.py         Convert Format
  compress.py        Compress Only
  rename.py          Rename in Bulk
  watermark.py       Add Watermark
  pdf_to_images.py   PDF to Images
  pdf_compress.py    Compress PDF
```

Settings (currently just the language) are saved in `%APPDATA%\Toolbox\settings.json`.

## License

[MIT](LICENSE)
