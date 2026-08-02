[CmdletBinding()]
param(
    [string]$RepoPath = "D:\OpenCode\calendar-event-planner-v2",
    [Parameter(Mandatory = $true)]
    [string]$PersonQuery,
    [int]$DaysBack = 7,
    [int]$DaysAhead = 30
)

$ErrorActionPreference = "Stop"

$PythonScript = Join-Path $PSScriptRoot "Test-Stage1-Connections.py"

if (-not (Test-Path $PythonScript)) {
    throw "Python diagnostics file not found: $PythonScript"
}

$RepoPath = [System.IO.Path]::GetFullPath($RepoPath)

$VenvPython = Join-Path $RepoPath ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    $PythonCommand = $VenvPython
    $PythonArgs = @()
}
elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCommand = "py"
    $PythonArgs = @("-3")
}
elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCommand = "python"
    $PythonArgs = @()
}
else {
    throw "Python 3 was not found."
}

$Arguments = @(
    $PythonScript,
    "--repo-path", $RepoPath,
    "--person-query", $PersonQuery,
    "--days-back", [string]$DaysBack,
    "--days-ahead", [string]$DaysAhead
)

& $PythonCommand @PythonArgs @Arguments
exit $LASTEXITCODE
