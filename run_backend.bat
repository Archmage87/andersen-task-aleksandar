@echo off
echo Starting FastAPI Backend...
cd backend
call venv\Scripts\activate
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
