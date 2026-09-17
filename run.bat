@echo off
REM Single-command startup for the Support Ticket AI System (Windows CMD / PowerShell)
REM Starts FastAPI (port 8000) and Streamlit UI (port 8501) in separate windows.

echo 🚀 Starting Support Ticket AI System...

REM Use python -m to ensure correct environment
set PY=python

REM Start FastAPI in a new window titled "FastAPI"
start "FastAPI" cmd /k %PY% -m uvicorn app.main:app --host 0.0.0.0 --port 8000

REM Start Streamlit in a new window titled "Streamlit"
start "Streamlit" cmd /k %PY% -m streamlit run ui/streamlit_app.py --server.port 8501

echo.
echo ✅ Both services launched.
echo    FastAPI : http://localhost:8000
echo    Streamlit: http://localhost:8501
echo.
echo Press any key to close this launcher window (services keep running in their own windows).
pause >nul