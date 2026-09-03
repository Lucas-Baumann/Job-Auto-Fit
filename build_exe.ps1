# Build JobAutoFit.exe — requer: pip install pyinstaller
# Uso: powershell -ExecutionPolicy Bypass -File build_exe.ps1
param([switch]$OneFile = $true)

Write-Host "[Build] Instalando PyInstaller..." -ForegroundColor Cyan
pip install --upgrade pyinstaller

$args = @(
    "gui.py",
    "--name", "JobAutoFit_v2",
    "--windowed",
    "--icon", "NONE",
    # curriculum_base.json NUNCA entra aqui: ficaria com dados pessoais reais gravados
    # dentro do binario para sempre. O app já lida bem com a ausência do arquivo (fica em branco).
    "--add-data", ".env.example;.",
    "--add-data", "logo.ico;.",
    "--icon", "logo.ico",
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

Write-Host "[Build] Concluído. Saída em dist/JobAutoFit_v2.exe" -ForegroundColor Green
Write-Host "Dica: antivírus pode acusar falso positivo em --onefile. Use --onedir se ocorrer."
