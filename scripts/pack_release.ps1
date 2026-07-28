param(
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"

if (-not $ProjectRoot) {
    $ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
}

$AppVersion = (Select-String -Path (Join-Path $ProjectRoot "src\bookhub\version.py") -Pattern 'APP_VERSION = "(.+)"').Matches[0].Groups[1].Value
$DistDir = Join-Path $ProjectRoot "build\nuitka\main.dist"
$ReleaseRoot = Join-Path $ProjectRoot "build\release"
$FinalName = "Simple-Book-library-v$AppVersion"
$StageDir = Join-Path $ReleaseRoot $FinalName
$ZipPath = Join-Path $ReleaseRoot "$FinalName-win64.zip"

if (-not (Test-Path $DistDir)) {
    throw "Missing Nuitka output: $DistDir (run scripts\build_nuitka.ps1 first)"
}

Remove-Item $StageDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $ReleaseRoot | Out-Null
Copy-Item $DistDir $StageDir -Recurse

foreach ($dir in @("img_preview", "sql", "Scan_error_logs")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $StageDir $dir) | Out-Null
}

$readme = @"
Simple Book Library — user data folders
简易图书馆 — 用户数据目录

img_preview/       Cover thumbnail cache / 封面缩略图缓存
sql/               Library database (library.db) and scan report / 书库数据库与扫描报告
Scan_error_logs/   Scan conflict and cleanup logs / 扫描冲突与清理日志

First run will write into these folders automatically.
首次运行会自动写入上述目录。

When upgrading: keep these three folders; replace main.exe and other program files only.
升级时请保留这三个文件夹，仅替换 main.exe 及同目录依赖文件。
"@
Set-Content -Path (Join-Path $StageDir "DATA_README.txt") -Value $readme -Encoding UTF8

Get-ChildItem $StageDir -Recurse -File -Include *.db, scan_report.json, *.webp -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue

Remove-Item $ZipPath -Force -ErrorAction SilentlyContinue
Compress-Archive -Path $StageDir -DestinationPath $ZipPath -Force

Write-Host "Staged: $StageDir"
Write-Host "Zip:    $ZipPath"
