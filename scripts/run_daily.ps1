param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [int]$DocumentLimit = 20,
    [int]$MetricLimit = 100,
    [int]$AiLimit = 10,
    [switch]$ForceAi
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$dataDir = Join-Path $ProjectRoot "data"
$logDir = Join-Path $ProjectRoot "logs"
$lockPath = Join-Path $dataDir "run_daily.lock"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logPath = Join-Path $logDir "run_daily-$timestamp.log"

New-Item -ItemType Directory -Force -Path $dataDir, $logDir | Out-Null

if (Test-Path $lockPath) {
    $lockAge = (Get-Date) - (Get-Item $lockPath).LastWriteTime
    if ($lockAge.TotalHours -lt 6) {
        "Another run_daily job appears to be running. Lock: $lockPath" | Tee-Object -FilePath $logPath -Append
        exit 2
    }
    Remove-Item -LiteralPath $lockPath -Force
}

try {
    "pid=$PID started_at=$(Get-Date -Format o)" | Set-Content -Path $lockPath -Encoding utf8
    Set-Location $ProjectRoot

    $argsList = @(
        "run",
        "disclosure-investing",
        "run-daily",
        "--document-limit",
        $DocumentLimit,
        "--metric-limit",
        $MetricLimit,
        "--ai-limit",
        $AiLimit
    )
    if ($ForceAi) {
        $argsList += "--force-ai"
    }

    "[$(Get-Date -Format o)] Starting run_daily" | Tee-Object -FilePath $logPath -Append
    & uv @argsList *>&1 | Tee-Object -FilePath $logPath -Append
    $exitCode = $LASTEXITCODE
    "[$(Get-Date -Format o)] Finished run_daily with exit code $exitCode" | Tee-Object -FilePath $logPath -Append

    if ($exitCode -ne 0) {
        exit $exitCode
    }
}
finally {
    if (Test-Path $lockPath) {
        Remove-Item -LiteralPath $lockPath -Force
    }
}
