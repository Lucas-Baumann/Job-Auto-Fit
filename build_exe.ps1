# Build JobAutoFit.exe — requer: pip install pyinstaller
# Uso: powershell -ExecutionPolicy Bypass -File build_exe.ps1
param([switch]$OneFile = $true)

Write-Host "[Build] Instalando PyInstaller..." -ForegroundColor Cyan
pip install --upgrade pyinstaller

$args = @(
    "gui.py",
    "--name", "JobAutoFit",
    "--windowed",
    "--icon", "NONE",
    "--add-data", "curriculum_base.json;.",
    "--add-data", ".env.example;.",
    "--hidden-import", "google.generativeai",
    "--hidden-import", "plyer",
    "--hidden-import", "pypdf",
    "--hidden-import", "docx",
    "--collect-all", "ttkbootstrap",
    "--collect-all", "reportlab"
)
if ($OneFile) { $args += "--onefile" } else { $args += "--onedir" }

Write-Host "[Build] Executando: pyinstaller $($args -join ' ')" -ForegroundColor Yellow
pyinstaller @args

Write-Host "[Build] Concluído. Saída em dist/JobAutoFit.exe" -ForegroundColor Green
Write-Host "Dica: antivírus pode acusar falso positivo em --onefile. Use --onedir se ocorrer."
