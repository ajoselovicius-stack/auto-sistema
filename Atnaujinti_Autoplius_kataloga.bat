@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ==========================================
echo AutoSistema - Autoplius katalogo sinchronizavimas
echo ==========================================
echo.
echo Bus atsisiustos Autoplius markes ir visu modeliu ID.
echo Tada katalogo kopija bus ikelta i GitHub, kad veiktu ir internetineje programoje.
echo.
pause

py -3 scripts\update_autoplius_catalog.py
if errorlevel 1 (
  echo.
  echo KLAIDA: nepavyko atsisiusti katalogo. Nieko neikeliu i GitHub.
  pause
  exit /b 1
)

git add autoplius_catalog.json
git diff --cached --quiet
if not errorlevel 1 (
  echo.
  echo Katalogas nepasikeite. Nera ka kelti.
  pause
  exit /b 0
)

git commit -m "Refresh Autoplius make and model catalog"
if errorlevel 1 (
  echo.
  echo KLAIDA kuriant Git commit.
  pause
  exit /b 1
)

git push
if errorlevel 1 (
  echo.
  echo KLAIDA keliant i GitHub. Patikrink interneto rysi ir GitHub prisijungima.
  pause
  exit /b 1
)

echo.
echo PAVYKO! Autoplius katalogas ikeltas i GitHub.
echo Internetine programa atsinaujins automatiskai po keliu minuciu.
pause
