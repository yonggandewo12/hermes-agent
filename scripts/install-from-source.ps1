param(
    [string]$SourceDir = (Get-Location).Path,
    [switch]$SkipSetup,
    [switch]$NoVenv,
    [string]$HermesHome = "$env:LOCALAPPDATA\hermes"
)

$ErrorActionPreference = 'Stop'
$PythonVersion = '3.11'

function Write-Info { param([string]$Message) Write-Host "→ $Message" -ForegroundColor Cyan }
function Write-Success { param([string]$Message) Write-Host "✓ $Message" -ForegroundColor Green }
function Write-Warn { param([string]$Message) Write-Host "⚠ $Message" -ForegroundColor Yellow }
function Write-Err { param([string]$Message) Write-Host "✗ $Message" -ForegroundColor Red }

function Test-SourceDir {
    if (-not (Test-Path $SourceDir)) { throw "Source directory does not exist: $SourceDir" }
    $required = @('pyproject.toml', 'package.json', 'hermes_cli')
    foreach ($item in $required) {
        if (-not (Test-Path (Join-Path $SourceDir $item))) {
            throw "Not a Hermes source root: missing $item in $SourceDir"
        }
    }
    $script:InstallDir = (Resolve-Path $SourceDir).Path
    Write-Success "Using local source tree: $script:InstallDir"
}

function Install-UvIfNeeded {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        $script:UvCmd = 'uv'
        Write-Success "uv found ($(uv --version))"
        return
    }
    Write-Info 'Installing uv...'
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex" | Out-Null
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        $script:UvCmd = 'uv'
        Write-Success "uv installed ($(uv --version))"
        return
    }
    $uvCandidates = @(
        "$env:USERPROFILE\.local\bin\uv.exe",
        "$env:USERPROFILE\.cargo\bin\uv.exe"
    )
    foreach ($candidate in $uvCandidates) {
        if (Test-Path $candidate) {
            $script:UvCmd = $candidate
            Write-Success "uv installed ($(& $candidate --version))"
            return
        }
    }
    throw 'uv installation failed'
}

function Ensure-Python {
    try {
        $pythonPath = & $UvCmd python find $PythonVersion 2>$null
        if ($pythonPath) {
            Write-Success "Python found: $(& $pythonPath --version)"
            return
        }
    } catch { }
    Write-Info "Installing Python $PythonVersion via uv..."
    & $UvCmd python install $PythonVersion | Out-Null
    $pythonPath = & $UvCmd python find $PythonVersion
    Write-Success "Python ready: $(& $pythonPath --version)"
}

function Ensure-Git {
    if (Get-Command git -ErrorAction SilentlyContinue) {
        Write-Success "Git found ($(git --version))"
        return
    }
    throw 'Git is required. Please install it manually and rerun.'
}

function Ensure-Pip {
    if (Get-Command pip -ErrorAction SilentlyContinue) {
        Write-Success 'pip found'
        return
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        try {
            python -m pip --version | Out-Null
            Write-Success 'pip found via python -m pip'
            return
        } catch { }
    }
    throw 'pip is required for internal source installation. Please install it manually and rerun.'
}

function Ensure-Node {
    if (Get-Command node -ErrorAction SilentlyContinue) {
        $script:HasNode = $true
        Write-Success "Node.js found ($(node --version))"
        return
    }
    $script:HasNode = $false
    Write-Info 'Node.js not found — attempting install...'
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        try {
            winget install OpenJS.NodeJS.LTS --silent --accept-package-agreements --accept-source-agreements | Out-Null
            $env:Path = [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine')
            if (Get-Command node -ErrorAction SilentlyContinue) {
                $script:HasNode = $true
                Write-Success "Node.js installed ($(node --version))"
                return
            }
        } catch { }
    }
    Write-Warn 'Node.js unavailable; browser-related tooling will be skipped'
}

function Ensure-Npm {
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Write-Success "npm found ($(npm --version))"
        return
    }
    throw 'npm is required for internal source installation. Please install it manually and rerun.'
}

function Install-OptionalSystemPackages {
    if (-not (Get-Command rg -ErrorAction SilentlyContinue)) {
        Write-Warn 'ripgrep not found; attempting install'
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            try { winget install BurntSushi.ripgrep.MSVC --silent --accept-package-agreements --accept-source-agreements | Out-Null } catch { }
        }
    }
    if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
        Write-Warn 'ffmpeg not found; attempting install'
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            try { winget install Gyan.FFmpeg --silent --accept-package-agreements --accept-source-agreements | Out-Null } catch { }
        }
    }
}

function New-Venv {
    if ($NoVenv) {
        Write-Warn 'Skipping venv creation (-NoVenv)'
        return
    }
    Push-Location $InstallDir
    if (Test-Path 'venv') { Remove-Item -Recurse -Force 'venv' }
    & $UvCmd venv venv --python $PythonVersion | Out-Null
    $env:VIRTUAL_ENV = Join-Path $InstallDir 'venv'
    Pop-Location
    Write-Success 'Virtual environment ready'
}

function Install-PythonDeps {
    Push-Location $InstallDir
    if (-not $NoVenv) { $env:VIRTUAL_ENV = Join-Path $InstallDir 'venv' }
    try {
        # --no-compile: skip .pyc generation (faster install, compiled on first import)
        & $UvCmd pip install --no-compile '.[all]'
    } catch {
        Write-Warn 'Full extras install failed, falling back to base install'
        & $UvCmd pip install --no-compile '.'
    }
    try { & $UvCmd pip install playwright | Out-Null } catch { Write-Warn 'Python Playwright package install failed' }
    Pop-Location
    Write-Success 'Python package installation complete'
}

function Install-NodeDeps {
    if (-not $HasNode) {
        Write-Info 'Skipping Node.js dependencies because Node.js is unavailable'
        return
    }

    # Faster npm flags: skip audit/fund checks, prefer cached packages
    $npmFlags = '--silent --no-audit --no-fund --prefer-offline'

    Push-Location $InstallDir
    $bridgeDir = Join-Path $InstallDir 'scripts\whatsapp-bridge'
    $hasBridge = Test-Path (Join-Path $bridgeDir 'package.json')

    if ($hasBridge) {
        # Run repo npm and whatsapp-bridge npm in parallel
        $repoJob = Start-Job -ScriptBlock {
            param($dir, $flags)
            Set-Location $dir
            try { npm install $flags } catch { Write-Warn 'npm install failed in repo root' }
        } -ArgumentList $InstallDir, $npmFlags

        $bridgeJob = Start-Job -ScriptBlock {
            param($dir, $flags)
            Set-Location $dir
            try { npm install $flags } catch { Write-Warn 'npm install failed in whatsapp bridge' }
        } -ArgumentList $bridgeDir, $npmFlags

        Wait-Job $repoJob | Out-Null
        Receive-Job $repoJob -Wait | Out-Null
        Remove-Job $repoJob -Force

        Wait-Job $bridgeJob | Out-Null
        Receive-Job $bridgeJob -Wait | Out-Null
        Remove-Job $bridgeJob -Force
    } else {
        if (Test-Path 'package.json') {
            try { npm install $npmFlags } catch { Write-Warn 'npm install failed in repo root' }
        }
    }

    if (Test-Path 'package.json') {
        Write-Info 'Installing Playwright Chromium browser...'
        try {
            npx playwright install chromium | Out-Null
            Write-Success 'Playwright Chromium installed'
        } catch {
            Write-Warn 'Playwright Chromium install failed'
        }
    }
    Pop-Location
}

function Set-HermesPath {
    if ($NoVenv) { return }
    $hermesBin = Join-Path $InstallDir 'venv\Scripts'
    $currentPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    if ($currentPath -notlike "*$hermesBin*") {
        [Environment]::SetEnvironmentVariable('Path', "$hermesBin;$currentPath", 'User')
    }
    [Environment]::SetEnvironmentVariable('HERMES_HOME', $HermesHome, 'User')
    $env:HERMES_HOME = $HermesHome
    $env:Path = "$hermesBin;$env:Path"
    Write-Success 'hermes command path configured'
}

function Initialize-Config {
    $dirs = @('cron','sessions','logs','pairing','hooks','image_cache','audio_cache','memories','skills','whatsapp\session')
    foreach ($dir in $dirs) {
        New-Item -ItemType Directory -Force -Path (Join-Path $HermesHome $dir) | Out-Null
    }
    $envFile = Join-Path $HermesHome '.env'
    if (-not (Test-Path $envFile)) {
        $example = Join-Path $InstallDir '.env.example'
        if (Test-Path $example) { Copy-Item $example $envFile } else { New-Item -ItemType File -Path $envFile | Out-Null }
    }
    $configFile = Join-Path $HermesHome 'config.yaml'
    if (-not (Test-Path $configFile)) {
        $example = Join-Path $InstallDir 'cli-config.yaml.example'
        if (Test-Path $example) { Copy-Item $example $configFile }
    }
    $soul = Join-Path $HermesHome 'SOUL.md'
    if (-not (Test-Path $soul)) { '# Hermes Agent Persona' | Set-Content -Path $soul -Encoding UTF8 }
    $pythonExe = Join-Path $InstallDir 'venv\Scripts\python.exe'
    if (Test-Path $pythonExe) {
        try { & $pythonExe (Join-Path $InstallDir 'tools\skills_sync.py') | Out-Null } catch { }
    }
    Write-Success 'Configuration initialized'
}

function Run-SetupWizard {
    if ($SkipSetup) {
        Write-Info 'Skipping setup wizard (-SkipSetup)'
        return
    }
    Push-Location $InstallDir
    if (-not $NoVenv) {
        & '.\venv\Scripts\python.exe' -m hermes_cli.main setup
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        python -m hermes_cli.main setup
    } else {
        Write-Warn 'Skipping setup wizard because no Python executable is available on PATH'
    }
    Pop-Location
}

function Verify-Install {
    if (-not $NoVenv) {
        $hermesExe = Join-Path $InstallDir 'venv\Scripts\hermes.exe'
    } else {
        $hermesExe = Get-Command hermes -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue
    }
    if (-not $hermesExe -or -not (Test-Path $hermesExe)) {
        throw 'hermes executable not found for verification'
    }
    & $hermesExe --version
    & $hermesExe doctor
    Write-Success 'End-to-end source installation verification passed'
}

try {
    Test-SourceDir
    Install-UvIfNeeded
    Ensure-Python
    Ensure-Git
    Ensure-Pip
    Ensure-Node
    Ensure-Npm
    Install-OptionalSystemPackages
    New-Venv
    Install-PythonDeps
    Install-NodeDeps
    Set-HermesPath
    Initialize-Config
    Run-SetupWizard
    Verify-Install
} catch {
    Write-Err "$($_.Exception.Message)"
    exit 1
}
