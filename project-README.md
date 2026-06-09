# Insurance Claims App

This is a full-stack Next.js and Python FastAPI application designed for deterministic health insurance claims adjudication.

## Quick Start Commands

There are two helper scripts in this root directory to instantly run the application servers (make sure to run them from the root):

1. **Start the Backend**: Double-click `run_backend.bat` or run it from the terminal:
   .\run_backend.bat
2. **Start the Frontend**: Double-click `run_frontend.bat` or run it from the terminal:
   .\run_frontend.bat

## IDE Configuration

A `.vscode/settings.json` file has been created to resolve "Cannot find module" errors in editor (but python interpreter may need to be set up manually). 

It configures VS Code to:
- Automatically point the Python interpreter to `backend/venv/Scripts/python.exe`.
- Add `backend` to the Python analysis path so imports like `from ingestion.policy_parser` resolve correctly without red error lines.

**Note**: You may need to reload your VS Code window (press `Ctrl+Shift+P`, type `Reload Window`, and press Enter) for the new settings to take effect.
