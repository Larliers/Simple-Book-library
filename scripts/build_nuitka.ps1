param(
    [switch]$Onefile
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Entry = Join-Path $ProjectRoot "src\main.py"
$Icon = Join-Path $ProjectRoot "src\assets\app_icon_bookcase.ico"
$OutputDir = Join-Path $ProjectRoot "build\nuitka"
$CacheDir = Join-Path $ProjectRoot "build\nuitka-cache"
$SitePackages = Join-Path $ProjectRoot ".venv\Lib\site-packages"
$FitzPackage = Join-Path $SitePackages "fitz"
$PyMuPDFPackage = Join-Path $SitePackages "pymupdf"

if (-not (Test-Path $Python)) {
    throw "Missing virtualenv Python: $Python"
}
if (-not (Test-Path $Icon)) {
    throw "Missing exe icon: $Icon"
}
if (-not (Test-Path $FitzPackage)) {
    throw "Missing PyMuPDF compatibility package: $FitzPackage"
}
if (-not (Test-Path $PyMuPDFPackage)) {
    throw "Missing PyMuPDF package: $PyMuPDFPackage"
}

$ModeArgs = @("--standalone")
if ($Onefile) {
    $ModeArgs = @("--onefile")
}

$ArgsList = @(
    "-m", "nuitka",
    $ModeArgs,
    "--enable-plugin=pyside6",
    "--assume-yes-for-downloads",
    "--no-deployment-flag=excluded-module-usage",
    "--low-memory",
    "--jobs=1",
    "--lto=no",
    "--windows-console-mode=disable",
    "--windows-icon-from-ico=$Icon",
    "--output-dir=$OutputDir",
    "--include-data-dir=src\assets=assets",
    "--include-data-dir=src\bookhub\i18n\locales=bookhub\i18n\locales",
    "--include-data-dir=src\bookhub\ui\web=bookhub\ui\web",
    "--include-qt-plugins=all",
    "--include-raw-dir=$FitzPackage=fitz",
    "--include-raw-dir=$PyMuPDFPackage=pymupdf",
    "--nofollow-import-to=fitz",
    "--nofollow-import-to=pymupdf",
    "--nofollow-import-to=pymupdf.*",
    "--nofollow-import-to=tests",
    "--nofollow-import-to=scripts",
    $Entry
)

Push-Location $ProjectRoot
try {
    New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null
    $env:NUITKA_CACHE_DIR = $CacheDir
    & $Python @ArgsList
    if ($LASTEXITCODE -ne 0) {
        throw "Nuitka build failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
