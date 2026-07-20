@echo off
REM Generate PNG images from all PlantUML diagrams
REM Requires: PlantUML (Java) - choco install plantuml OR download from plantuml.com
REM Output: PNG files in docs/diagrams/output/

set OUTPUT=output
if not exist %OUTPUT% mkdir %OUTPUT%

echo Generating EcoSweep diagram images...
echo.

where plantuml >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo PlantUML not found in PATH.
    echo Install: choco install plantuml
    echo Or use: https://www.plantuml.com/plantuml/uml/ (paste each .puml file)
    echo.
    echo Files to convert:
    dir /b *.puml
    exit /b 1
)

for %%f in (*.puml) do (
    echo [%%f] -> %OUTPUT%\%%~nf.png
    plantuml -tpng -o %OUTPUT% "%%f"
)

echo.
echo Done. Images in %OUTPUT%\
dir %OUTPUT%\*.png
pause
