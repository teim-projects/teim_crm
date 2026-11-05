
$ErrorActionPreference = "Stop"

# Project paths
$ProjectPath = "C:\teim_crm"
$PythonExe = Join-Path $ProjectPath ".venv\Scripts\python.exe"

# Verify project and virtual environment
if (!(Test-Path $PythonExe)) {
    Write-Host "ERROR: Virtual environment Python not found." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Set-Location $ProjectPath

# Check Memurai
$Memurai = Get-Service -Name "*Memurai*" -ErrorAction SilentlyContinue

if (!$Memurai -or $Memurai.Status -ne "Running") {
    Write-Host "ERROR: Memurai is not running. Start Memurai before continuing." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Securely request the live CRM reader password
$SecurePassword = Read-Host "Enter CRM recommendation reader password" -AsSecureString
$env:CRM_DB_PASSWORD = [System.Net.NetworkCredential]::new("", $SecurePassword).Password
$SecurePassword = $null

if ([string]::IsNullOrWhiteSpace($env:CRM_DB_PASSWORD)) {
    Write-Host "ERROR: Password was not provided." -ForegroundColor Red
    Remove-Item Env:CRM_DB_PASSWORD -ErrorAction SilentlyContinue
    Read-Host "Press Enter to exit"
    exit 1
}

# Start Django server
$DjangoCommand = "Set-Location '$ProjectPath'; Write-Host 'DJANGO DEVELOPMENT SERVER' -ForegroundColor Green; & '$PythonExe' manage.py runserver"
Start-Process powershell.exe -WorkingDirectory $ProjectPath -ArgumentList @("-NoExit", "-Command", $DjangoCommand)

Start-Sleep -Seconds 2

# Start Celery worker
$WorkerCommand = "Set-Location '$ProjectPath'; Write-Host 'CELERY WORKER' -ForegroundColor Green; & '$PythonExe' -m celery -A crm worker -l info --pool=solo"
Start-Process powershell.exe -WorkingDirectory $ProjectPath -ArgumentList @("-NoExit", "-Command", $WorkerCommand)

Start-Sleep -Seconds 2

# Start Celery Beat
$BeatCommand = "Set-Location '$ProjectPath'; Write-Host 'CELERY BEAT' -ForegroundColor Green; & '$PythonExe' -m celery -A crm beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler"
Start-Process powershell.exe -WorkingDirectory $ProjectPath -ArgumentList @("-NoExit", "-Command", $BeatCommand)

# Clear password from the launcher process environment
Remove-Item Env:CRM_DB_PASSWORD -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "CRM startup commands launched." -ForegroundColor Green
Write-Host "Django, Celery Worker and Celery Beat are opening in separate windows."
Write-Host "Keep all three windows running while using the CRM."
