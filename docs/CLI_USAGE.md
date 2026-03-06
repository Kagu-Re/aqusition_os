# CLI Usage Guide

This guide explains how to run CLI commands for the Acquisition Engine.

## Problem

The `ae` module is located in the `src/` directory, so Python needs to know where to find it.

## Solutions

### Option 1: Set PYTHONPATH (Quick)

**Windows (PowerShell):**
```powershell
$env:PYTHONPATH="src"
python -m ae.cli --help
```

**Windows (CMD):**
```cmd
set PYTHONPATH=src
python -m ae.cli --help
```

**Linux/macOS:**
```bash
export PYTHONPATH=src
python -m ae.cli --help
```

### Option 2: Use Wrapper Scripts (Recommended)

**Windows:**
```cmd
ops\scripts\ae_cli.bat auth-set-password --username admin
```

**Linux/macOS:**
```bash
bash ops/scripts/ae_cli.sh auth-set-password --username admin
```

### Option 3: Install Package (Permanent)

Install the package in editable mode so it's always available:

```bash
pip install -e .
```

After installation, you can run commands directly:
```bash
python -m ae.cli --help
```

## Common Commands

### Set Admin Password

**Windows:**
```cmd
set PYTHONPATH=src
set AE_DB_PATH=acq.db
python -m ae.cli auth-set-password --username admin
```

**Or using wrapper:**
```cmd
set AE_DB_PATH=acq.db
ops\scripts\ae_cli.bat auth-set-password --username admin
```

**Linux/macOS:**
```bash
export PYTHONPATH=src
export AE_DB_PATH=$(pwd)/acq.db
python -m ae.cli auth-set-password --username admin
```

### Start Console

**Windows:**
```cmd
set PYTHONPATH=src
set AE_DB_PATH=acq.db
python -m ae.cli serve-console
```

**Linux/macOS:**
```bash
export PYTHONPATH=src
export AE_DB_PATH=$(pwd)/acq.db
python -m ae.cli serve-console
```

### Initialize Database

**Windows:**
```cmd
set PYTHONPATH=src
python -m ae.cli init-db --db acq.db
```

**Linux/macOS:**
```bash
export PYTHONPATH=src
python -m ae.cli init-db --db acq.db
```

## Making PYTHONPATH Permanent

### Windows PowerShell

Add to your PowerShell profile:
```powershell
$env:PYTHONPATH="D:\aqusition_os\src"
```

Or create a `.env` file in the project root (if using a tool that reads it).

### Linux/macOS

Add to your `~/.bashrc` or `~/.zshrc`:
```bash
export PYTHONPATH="$HOME/path/to/aqusition_os/src:$PYTHONPATH"
```

## Troubleshooting

### "No module named 'ae'"

**Solution:** Set `PYTHONPATH=src` before running commands, or use the wrapper scripts.

### "ModuleNotFoundError: No module named 'ae'"

**Solution:** Make sure you're in the project root directory and `src/ae` exists.

### Commands work in scripts but not directly

**Solution:** The initialization script sets PYTHONPATH automatically. For direct CLI usage, use one of the solutions above.

## Best Practice

For development, we recommend:
1. **Install in editable mode**: `pip install -e .` (one-time setup)
2. **Use wrapper scripts**: `ops/scripts/ae_cli.bat` or `ops/scripts/ae_cli.sh` (cross-platform)

For production deployments, the package should be properly installed via `pip install .` or Docker.
