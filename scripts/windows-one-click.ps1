<#
Automated setup for Windows using winget + pip.
Requirements: Windows 10/11 with winget and Python 3.10+ available on PATH.
#>

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "[1/4] Installing Transmission (winget)..."
winget install -e --id Transmission.Transmission --accept-source-agreements --accept-package-agreements

Write-Host "[2/4] Ensuring Python dependencies are installed..."
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Write-Host "[3/4] Building environment file (.env.local)..."
if (-not $Env:TRANSMISSION_USERNAME) { $Env:TRANSMISSION_USERNAME = "admin" }
if (-not $Env:TRANSMISSION_PASSWORD) { $Env:TRANSMISSION_PASSWORD = "changeme" }
if (-not $Env:TRANSMISSION_HOST) { $Env:TRANSMISSION_HOST = "127.0.0.1" }
if (-not $Env:TRANSMISSION_PORT) { $Env:TRANSMISSION_PORT = "9091" }
if (-not $Env:TRANSMISSION_DOWNLOAD_DIR) { $Env:TRANSMISSION_DOWNLOAD_DIR = "$Env:USERPROFILE\Downloads" }

if (-not $Env:APP_SECRET_KEY) {
    $Env:APP_SECRET_KEY = [System.Convert]::ToHexString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).ToLower()
}

@"
TRANSMISSION_HOST=$($Env:TRANSMISSION_HOST)
TRANSMISSION_PORT=$($Env:TRANSMISSION_PORT)
TRANSMISSION_USERNAME=$($Env:TRANSMISSION_USERNAME)
TRANSMISSION_PASSWORD=$($Env:TRANSMISSION_PASSWORD)
TRANSMISSION_DOWNLOAD_DIR=$($Env:TRANSMISSION_DOWNLOAD_DIR)
APP_SECRET_KEY=$($Env:APP_SECRET_KEY)
"@ | Set-Content -Path .env.local -Encoding UTF8

Write-Host "[4/4] Launching the Flask app..."
Get-Content .env.local | ForEach-Object {
    if ([string]::IsNullOrWhiteSpace($_)) { return }
    $pair = $_.Split("=",2)
    if ($pair.Length -eq 2) { Set-Item -Path Env:$($pair[0]) -Value $pair[1] }
}
python app.py
