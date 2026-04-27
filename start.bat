@echo off
echo Starting Apex...

:: Backend (FastAPI)
start "Apex Backend" cmd /k "cd /d E:\Claude Projects\Apex\backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: Frontend (Next.js)
start "Apex Frontend" cmd /k "cd /d E:\Claude Projects\Apex\frontend && npm run dev"

echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Login: swapneet.lahoti@gmail.com / Apex2026!
pause
