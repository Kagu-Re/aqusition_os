@echo off
REM End-to-end initialization and testing script for Windows
REM Usage: ops\scripts\e2e_init_and_test.bat [--db-path <path>] [--skip-tests] [--skip-console] [--skip-smoke]

python ops\scripts\e2e_init_and_test.py %*
