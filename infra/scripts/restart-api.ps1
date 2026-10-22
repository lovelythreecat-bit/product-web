# Complete local backend startup. -WhatIf previews without starting any service.
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateRange(1, 65535)] [int]$Port = 18000,
    [string]$Stream,
    [string]$Group = 'local-generation-workers',
    [ValidateRange(1, 32)] [int]$Concurrency = 4,
    [switch]$RestartApi,
    [switch]$Check
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$pythonPath = Join-Path $projectRoot 'backend/.venv/Scripts/python.exe'
$launcherPath = Join-Path $PSScriptRoot 'start_local.py'
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw 'Backend Python is missing. Install dependencies with: uv sync --frozen --project backend'
}
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'backend/.env') -PathType Leaf)) {
    throw 'backend/.env is missing. Prepare the local configuration before starting.'
}

$launcherArguments = @('-X', 'utf8', $launcherPath, '--root', $projectRoot,
    '--port', "$Port", '--group', $Group, '--concurrency', "$Concurrency")
if ($Stream) { $launcherArguments += @('--stream', $Stream) }
if ($RestartApi) { $launcherArguments += '--restart-api' }
if ($Check) { $launcherArguments += '--check' }
if ($WhatIfPreference) {
    $launcherArguments += '--dry-run'
} elseif (-not $PSCmdlet.ShouldProcess('Local backend stack', 'Check dependencies and start missing services and Workers')) {
    return
}

& $pythonPath @launcherArguments
if ($LASTEXITCODE -ne 0) {
    throw 'Backend startup or health monitoring failed. Check [FAILED] above and .local-data/runtime/launcher.log.'
}
