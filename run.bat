@echo off

REM 🔄 Step 0: Try deactivating any active conda environment
echo Deactivating any active conda environment...
call conda deactivate >nul 2>&1
call conda deactivate >nul 2>&1
call conda deactivate >nul 2>&1

REM 🔧 Set environment variables for Flask
echo Setting Flask environment variables...
set FLASK_RUN_EXCLUDE_PATTERNS=uploads/*
set FLASK_RUN_PORT=8090

echo Running Flask Interface
call venv\Scripts\activate
flask run
pause
