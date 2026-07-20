# Generate PNG images from all PlantUML diagrams
# Requires: PlantUML (Java) - choco install plantuml
# Output: docs/diagrams/output/

$OutputDir = Join-Path $PSScriptRoot "output"
if (-not (Test-Path $OutputDir)) { New-Item -ItemType Directory -Path $OutputDir | Out-Null }

Write-Host "EcoSweep Diagram Generator" -ForegroundColor Cyan
Write-Host ""

$plantuml = Get-Command plantuml -ErrorAction SilentlyContinue
if (-not $plantuml) {
    Write-Host "PlantUML not found. Options:" -ForegroundColor Yellow
    Write-Host "  1. Install: choco install plantuml"
    Write-Host "  2. Online: https://www.plantuml.com/plantuml/uml/"
    Write-Host ""
    Write-Host "Files to convert:" -ForegroundColor Gray
    Get-ChildItem -Filter "*.puml" | ForEach-Object { Write-Host "  - $($_.Name)" }
    exit 1
}

Get-ChildItem -Filter "*.puml" | ForEach-Object {
    Write-Host "[$($_.Name)] -> output/$($_.BaseName).png"
    plantuml -tpng -o $OutputDir $_.FullName
}

Write-Host ""
Write-Host "Done. Images in $OutputDir\" -ForegroundColor Green
Get-ChildItem $OutputDir -Filter "*.png" | ForEach-Object { Write-Host "  $($_.Name)" }
