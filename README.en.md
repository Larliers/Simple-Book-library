# Simple Book Library

**v2.1.0** · [English](README.en.md) | [中文](README.md) · [GitHub Releases](https://github.com/Larliers/Simple-Book-library/releases)

A local Windows desktop library for your personal collection. Scan PDF / EPUB / HTML / Markdown / FB2 / DOCX books, comic image folders and CBZ archives, and TXT novels into one library, browse cover grids, and open items with your system default apps. The UI is a **Qt WebEngine** glassmorphism SPA with switchable **Glass** and **Vaporwave** skins.

## What's new in v2.1.0

- **Settings → General → About**: shows the current version and checks GitHub for the latest release; prompts you to open the download page when an update is available
- **Dual UI skins**: switch between Glass and Vaporwave under Settings → Appearance (restart required); Vaporwave includes day/night variants and bundled local woff2 fonts
- **Improved CBZ open**: extracts all image pages to a read cache, then opens the first page in your default image viewer
- **Vaporwave layout fix**: production DOM aligned with the Glass skin layout; Settings, modals, toasts, and Text Rules render correctly

## Who is this for?

- One place for local PDFs, EPUBs, HTML, Markdown, FB2, DOCX, comic folders/CBZ, and TXT novels
- Folder-based scanning instead of adding files one by one
- Tags, collections, favorites, and TXT import rules
- Large libraries with incremental scans, configurable fingerprint strategies, and viewport virtualization

## Features

| Section | Formats | What you can do |
|---------|---------|-----------------|
| **Library** | PDF, EPUB, HTML/HTM, Markdown, FB2/FB2.ZIP, DOCX | Grid / list view, detail pane, tags, search |
| **Comic** | **Leaf image folders** and **CBZ** | One folder or CBZ = one volume; waterfall or paginated layout |
| **Text Novel** | TXT (auto-detects encoding) | List view, text preview, custom import rule chains |
| **Collections** | — | Custom reading lists |
| **Favorites** | Books + comics | Unified favorites |
| **Settings** | — | Paths & Scan, appearance, thumbnail cache, error logs, update check |

### Import & scan

1. Set Library / Comic / Text roots under **Settings → Paths & Scan**.
2. Run a scan to recurse into those roots (**folder-level import only**).
3. Metadata extraction and cover thumbnails are generated automatically.

Notes:

- **Fingerprint strategy** (Settings → General): new installs default to **Quick** (first 4MB); Fast (size+mtime only, may miss content-only changes) or Strict (full SHA256) are optional. Unchanged Library/Text files are skipped on rescan.
- **Per-directory scan strategy** (optional): assign a strategy per root when enabled; global strategy applies when disabled; saved overrides are kept.
- **Comic scan**: directory snapshot (fast) or full rescan each time (strict); same-title conflicts: skip incoming / keep both / prefer newer.
- **TXT encoding preference**: Simplified first / Traditional first / Auto; text rules extract metadata from filename or body.
- **Thumbnail cache**: default `img_preview/`; relocate under Settings (migrate / rewire index / switch only).
- Missing sources are logged and removed; same name+extension under different paths is skipped and logged.

### Browse & open

- **Single click**: select and show details.
- **Double click**: open with the system default app.
- Search: Library supports `title:` / `author:` / `tag:` prefixes.
- Large lists use viewport virtualization; grid columns and buffer screens are configurable.

### Text rules (TXT)

Open **Rules** next to a text root under Settings → Paths & Scan to edit rule chains with live preview, templates, and common regex helpers.

### Appearance

- **Glass**: default glassmorphism skin.
- **Vaporwave**: neon vaporwave skin (restart required after switching).
- **Day/night theme**: auto by local time or manual.

### Where data lives

| Path | Purpose |
|------|---------|
| `src/sql/library.db` | SQLite library database |
| `img_preview/` (default) | Cover thumbnail cache |
| `src/Scan_error_logs/` | Scan conflicts, missing-file removals, etc. |
| `src/fonts/` | Optional custom fonts |

## Requirements

- **OS**: Windows 10 / 11
- **Python**: **3.10.6** recommended (3.10+; matches locked deps)
- **UI language**: Simplified Chinese by default (some Settings strings fall back to English)

## Getting started

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\.venv\Scripts\pythonw.exe src\main.py
```

## Build an exe

```powershell
.\scripts\build_nuitka.ps1          # standalone folder (recommended)
.\scripts\build_nuitka.ps1 -Onefile # single-file exe
```

Output goes to `build/nuitka/`. The first Nuitka build downloads MinGW automatically and can take a while.

## Developer checks

```powershell
pip install -r requirements-dev.txt
$env:PYTHONPATH="src"
.\.venv\Scripts\python.exe -m pytest src/tests -q
.\.venv\Scripts\python.exe src\main.py --check-pymupdf
```

## Limitations

- Import is **scan-from-configured-roots only**; single-file drag-and-drop is not supported.
- Comics support **image folders** and **CBZ**; CBR and other archives are not supported.
- Opening files depends on OS file associations.
- Scan and thumbnail jobs are mutually exclusive; first-time scans of large libraries can take a while.
- Without PyMuPDF, PDFs can still be indexed but metadata and covers may be incomplete.

## Further reading

- Source layout: [`src_construction.md`](src_construction.md)
- UI design references: `Simple-Book-library-Dev_Document/UI/`

## License

See notices in the repository. Third-party packages follow their own licenses.
