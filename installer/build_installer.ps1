param(
    [string]$PythonExe = "python",
    [switch]$SkipInno
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$buildVenv = Join-Path $repoRoot ".venv-build"
$venvPython = Join-Path $buildVenv "Scripts\python.exe"
$venvPip = Join-Path $buildVenv "Scripts\pip.exe"

Write-Host "[1/6] Preparing clean build environment..." -ForegroundColor Cyan
if (!(Test-Path $buildVenv)) {
    & $PythonExe -m venv $buildVenv
}

Write-Host "[2/6] Installing build dependencies..." -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip
& $venvPip install -r requirements.txt
& $venvPip install pyinstaller

Write-Host "[3/6] Cleaning previous build outputs..." -ForegroundColor Cyan
Remove-Item -Recurse -Force "build" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "dist" -ErrorAction SilentlyContinue

Write-Host "[4/6] Building app binaries with PyInstaller..." -ForegroundColor Cyan
& $venvPython -m PyInstaller "installer\GestureVLC.spec" --noconfirm --clean

if (!(Test-Path "dist\GestureVLC\GestureVLC.exe")) {
    throw "PyInstaller output not found: dist\\GestureVLC\\GestureVLC.exe"
}

Write-Host "[5/6] Verifying runtime model assets..." -ForegroundColor Cyan
$bundleRoot = "dist\GestureVLC"
if (Test-Path "dist\GestureVLC\_internal") {
    $bundleRoot = "dist\GestureVLC\_internal"
}

$required = @(
    (Join-Path $bundleRoot "app\models\air_writing_cnn.onnx"),
    (Join-Path $bundleRoot "gesture\gesture_model.pkl"),
    (Join-Path $bundleRoot "gesture\gesture_scaler.pkl"),
    (Join-Path $bundleRoot "gesture\class_map.json")
)

$missing = @()
foreach ($path in $required) {
    if (!(Test-Path $path)) {
        $missing += $path
    }
}

if ($missing.Count -gt 0) {
    $msg = "Missing required packaged assets:`n - " + ($missing -join "`n - ")
    throw $msg
}

if ($SkipInno) {
    Write-Host "[6/6] SkipInno enabled. App build completed at dist\\GestureVLC" -ForegroundColor Yellow
    exit 0
}

Write-Host "[6/6] Building setup executable with Inno Setup..." -ForegroundColor Cyan
$iscc = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
if (!$iscc) {
    $candidates = @(
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    )

    $isccPath = $null
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            $isccPath = $candidate
            break
        }
    }

    if (!$isccPath) {
        throw "Inno Setup compiler (ISCC.exe) not found. Install Inno Setup 6 or run with -SkipInno."
    }
}
else {
    $isccPath = $iscc.Source
}

& $isccPath "installer\GestureVLC.iss"

if (!(Test-Path "dist-installer\GestureVLC-Setup.exe")) {
    throw "Installer build failed. Expected dist-installer\\GestureVLC-Setup.exe"
}

Write-Host "Build complete: dist-installer\\GestureVLC-Setup.exe" -ForegroundColor Green
