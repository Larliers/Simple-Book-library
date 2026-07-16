# Simple Book Library

[English](README.en.md) | [中文](README.md)

A local Windows desktop library app for your personal collection. Scan PDF / EPUB books, comic image folders, and TXT novels into one library, browse cover grids, and open items with your system default apps.

## Who is this for?

- You want one place for local PDFs, EPUBs, comic folders, and TXT novels
- You prefer folder-based scanning over adding files one by one
- You need tags, collections, favorites, and import rules for TXT metadata

## Features

| Section | Formats | What you can do |
|---------|---------|-----------------|
| **Library** | PDF, EPUB | Grid / list view, detail pane, tags, search |
| **Comic** | **Leaf image folders** (jpg / jpeg / png / webp) | One folder = one volume; title = folder name; waterfall or paginated layout |
| **Text Novel** | TXT (auto-detects UTF-8 / GBK, etc.) | List view, text preview, custom import rule chains |
| **Collections** | — | Custom reading lists |
| **Favorites** | Books + comics | Unified favorites entry |
| **Settings** | — | Paths, scan options, fonts, thumbnails, error logs |

### Import

1. Set separate root folders for Library / Comic / Text in Settings.
2. Run a scan to recurse into those roots (**folder-level import only** — single-file drag-and-drop is not supported).
3. The app extracts available title / author metadata and builds cover thumbnails.

Notes:

- Library scan depth is configurable (about 1–3 levels).
- Comics (**by design**): aimed at readers who store pages as images, one folder per volume. A leaf folder of jpg/jpeg/png/webp becomes one comic; the title is the folder name. A fast placeholder cover appears first, then compressed thumbnails are generated in the background. **CBZ / CBR / ZIP comic archives are not supported.**
- TXT: encoding is auto-detected (UTF-8, GBK/GB18030, etc.); **text rules** extract title, author, series, and tags from the filename or body; novels land in Text Novel, not the main Library list.
- Missing source files are logged and removed from the library.
- Same name + extension under different paths: import is skipped and logged.

### Browse & open

- **Single click**: select and show details on the right.
- **Double click**: open with the system default app (a reader must be installed).
- Search: Library supports `title:` / `author:` / `tag:` prefixes; Text Novel has its own filter.
- Cover chrome (e.g. selection border) can be tuned in Settings.

### Text rules (TXT)

Open the Rules panel in Settings to:

- Edit the import rule chain with live preview
- Use built-in templates and common regex helpers
- Save rules so later Text scans pick up the new metadata

### Where data lives

Everything stays on your machine — nothing is uploaded:

| Path | Purpose |
|------|---------|
| `src/sql/library.db` | SQLite library database |
| `img_preview/` | Cover thumbnail cache |
| `src/Scan_error_logs/` | Scan conflicts, missing-file removals, etc. |
| `src/fonts/` | Optional custom fonts (reload from Settings) |

## Requirements

- **OS**: Windows 10 / 11 (primary supported platform)
- **Python**: **3.10.6** recommended (3.10+ required; matches locked deps)
- **UI language**: Simplified Chinese by default

## Getting started

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch (no console window)
.\.venv\Scripts\pythonw.exe src\main.py
```

Optional: create a shortcut named `启动 简易图书馆.lnk` in the repo root pointing at the same `pythonw.exe` and `src\main.py` (shortcuts are gitignored).

### Optional: build an exe

```powershell
.\scripts\build_nuitka.ps1          # standalone folder
.\scripts\build_nuitka.ps1 -Onefile # single-file exe
```

Output goes to `build/nuitka/`.

### Optional: developer checks

```powershell
pip install -r requirements-dev.txt
$env:PYTHONPATH="src"
.\.venv\Scripts\python.exe -m pytest src/tests -q

# Verify the PDF engine (exit code 0 = OK)
.\.venv\Scripts\python.exe src\main.py --check-pymupdf
```

## Limitations

- Import is **scan-from-configured-roots only**; you cannot drop a single file into the library.
- The Comic section manages **image folders only** — CBZ/CBR archives are not supported.
- Opening files depends on OS file associations (PDF reader, image viewer, etc.).
- Scan and thumbnail jobs are mutually exclusive; large first-time scans can take a while.
- If PyMuPDF is missing or unavailable, PDFs can still be indexed, but metadata and covers may be incomplete (with a warning).

## Further reading

- Source layout: [`src_construction.md`](src_construction.md)
- UI design references: `Simple-Book-library-Dev_Document/UI/新UI/`

## License

See notices in the repository. Third-party packages follow their own licenses.
