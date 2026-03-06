@echo off
REM Wrapper script to run ae.cli commands with proper PYTHONPATH
REM Usage: ops\scripts\ae_cli.bat <command> [args...]

setlocal
set "ROOT=%~dp0..\.."
set "PYTHONPATH=%ROOT%\src"
set "AE_DB_PATH=%AE_DB_PATH%"

python -m ae.cli %*
