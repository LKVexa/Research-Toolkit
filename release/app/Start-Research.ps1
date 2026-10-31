param([Parameter(ValueFromRemainingArguments=$true)][string[]]$ResearchArguments)
$ErrorActionPreference = 'Stop'
$candidates = @()
if ($env:RESEARCH_PYTHON) { $candidates += $env:RESEARCH_PYTHON }
$profileFolder = [Environment]::GetFolderPath([Environment+SpecialFolder]::UserProfile)
$candidates += Join-Path $profileFolder '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$foundPython = Get-Command python.exe -ErrorAction SilentlyContinue
if ($foundPython) { $candidates += $foundPython.Source }
$selectedPython = $null
foreach ($candidate in $candidates) {
    if ((Test-Path -LiteralPath $candidate -PathType Leaf) -and ($candidate -notlike '*WindowsApps*')) {
        $selectedPython = $candidate
        break
    }
}
if (-not $selectedPython) {
    Write-Error 'Set RESEARCH_PYTHON to Python 3.12.14 with NumPy 2.3.5; see INSTALL.md.'
    exit 2
}
if (-not $ResearchArguments) { $ResearchArguments = @('doctor') }
& $selectedPython -I -B (Join-Path $PSScriptRoot 'research.py') @ResearchArguments
exit $LASTEXITCODE
