$pythonExe = Join-Path $PSScriptRoot ".venv311\Scripts\python.exe"
$ultralyticsDir = Join-Path $PSScriptRoot ".cache\ultralytics"
$hfHome = Join-Path $PSScriptRoot ".cache\huggingface"

if (-not (Test-Path $pythonExe)) {
    Write-Error "Project Python runtime not found at $pythonExe"
    exit 1
}

New-Item -ItemType Directory -Force -Path $ultralyticsDir | Out-Null
New-Item -ItemType Directory -Force -Path $hfHome | Out-Null

$env:YOLO_CONFIG_DIR = $ultralyticsDir
$env:ULTRALYTICS_CONFIG_DIR = $ultralyticsDir
$env:HF_HOME = $hfHome
$env:TRANSFORMERS_CACHE = (Join-Path $hfHome "transformers")

& $pythonExe "$PSScriptRoot\main.py"
exit $LASTEXITCODE
