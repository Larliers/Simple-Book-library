# Simple Book Library

[English](README.en.md) | [中文](README.md)

A local Windows desktop library app for your personal collection. Scan PDF / EPUB / HTML / Markdown / FB2 / DOCX books, comic image folders and CBZ archives, and TXT novels into one library, browse cover grids, and open items with your system default apps.

## Who is this for?

- You want one place for local PDFs, EPUBs, HTML, Markdown, FB2, DOCX, comic folders/CBZ, and TXT novels
- You prefer folder-based scanning over adding files one by one
- You need tags, collections, favorites, and import rules for TXT metadata

## Features

| Section | Formats | What you can do |
|---------|---------|-----------------|
| **Library** | PDF, EPUB, HTML/HTM, Markdown, FB2/FB2.ZIP, DOCX | Grid / list view, detail pane, tags, search; covers prefer embedded images, else a title placeholder card |
| **Comic** | **Leaf image folders** (jpg / jpeg / png / webp / gif / bmp / tiff) and **CBZ** | One folder or CBZ = one volume; title = folder/file name; GIF covers use the first frame; waterfall or paginated layout |
| **Text Novel** | TXT (auto-detects UTF-8 / GBK, etc.) | List view, text preview, custom import rule chains |
| **Collections** | — | Custom reading lists |
| **Favorites** | Books + comics | Unified favorites entry |
| **Settings** | — | Paths & Scan, fonts, thumbnails, error logs |

### Import

1. Set separate root folders for Library / Comic / Text in Settings.
2. Run a scan to recurse into those roots (**folder-level import only** — single-file drag-and-drop is not supported).
3. The app extracts available title / author metadata and builds cover thumbnails.

Notes:

- Library scan depth is configurable (about 1–3 levels).
- Library document formats: HTML/HTM, Markdown, FB2/FB2.ZIP, and DOCX share the Library scan and cover-cache pipeline with PDF/EPUB. HTML/Markdown use a local embedded image when available, otherwise a title placeholder card (no full-page browser render).
- Comics: a leaf folder of jpg/jpeg/png/webp/gif/bmp/tiff, or a **CBZ** archive, becomes one volume; the title is the folder name or CBZ stem. GIF covers use the **first frame**. A fast placeholder appears first, then compressed thumbnails generate in the background. **CBR and other archive types remain unsupported.**
- TXT: encoding is auto-detected (UTF-8, GBK/GB18030, Big5, etc.); Settings “Text encoding preference” (Simplified first / Traditional first / Auto; default Simplified) steers simplified/traditional ranking; **text rules** extract title, author, series, and tags from the filename or body; novels land in Text Novel, not the main Library list. On rescan, unchanged files are skipped using the same fingerprint strategy as Library (Settings “Fingerprint strategy”; **new installs default to Quick**/first 4MB; Fast only compares size+mtime and may miss content-only changes; Text has no thumbnail requirement).
- Settings “Paths & Scan” combines root folders with scan/thumbnail tasks (no separate Tasks nav item).
- **Per-directory scan strategy** (optional): enable “Assign scan strategy to different paths” on Paths & Scan to set a strategy per Library / Comic / Text root (unset = inherit global). When disabled, every root uses the global strategy (Library/Text: “Fingerprint strategy”; comics: “Comic scan strategy”); saved per-root overrides are kept but not applied. Library/Text overrides: Fast / Quick / Strict; comic overrides: directory snapshot (fast) / full rescan each time (strict)—full disables folder snapshot short-circuit and re-reads sidecar TXT notes.
- Comic same-title conflicts within one comic root: configurable in Settings (default skip incoming; or keep both / prefer newer).
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
| `img_preview/` (default) | Cover thumbnail cache; changeable under Settings → Paths & Scan (migrate / rewire index / switch only) |
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
- The Comic section supports **image folders** and **CBZ**; CBR and other archives remain unsupported.
- Opening files depends on OS file associations (PDF reader, image viewer, etc.).
- Scan and thumbnail jobs are mutually exclusive; large first-time scans can take a while.
- If PyMuPDF is missing or unavailable, PDFs can still be indexed, but metadata and covers may be incomplete (with a warning).

## Further reading

- Source layout: [`src_construction.md`](src_construction.md)
- UI design references: `Simple-Book-library-Dev_Document/UI/新UI/`

## License

See notices in the repository. Third-party packages follow their own licenses.
