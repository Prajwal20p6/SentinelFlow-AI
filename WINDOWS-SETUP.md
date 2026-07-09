# Windows Development Setup Details

This guide provides step-by-step instructions for configuring and debugging SentinelFlow AI on native Windows environments without needing Docker or WSL.

## Manual Step-by-Step Installation

If you prefer to configure the system manually rather than using `setup.ps1`, follow these steps:

### 1. Set Up Python Virtual Environment
Navigate to the `/backend` folder, initialize a local `venv` directory, and install requirements:
```cmd
cd backend
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\pip install -r requirements-dev.txt
```

### 2. Configure Local Database
Run the database creation and seed operations:
```cmd
cd backend
venv\Scripts\python -c "from app.core.database import get_db; from app.models.models import Base; from app.core.database import engine; Base.metadata.create_all(bind=engine)"
```

### 3. Set Up Next.js Frontend Node Packages
Navigate to `/frontend` and install Node dependencies:
```cmd
cd ../frontend
npm install
```

### 4. Running Backend and Frontend Separately
If you want to run backend and frontend processes in separate consoles for debugging:
- **FastAPI Backend (Port 8000)**:
  ```cmd
  cd backend
  venv\Scripts\python run.py
  ```
- **Next.js Dev Frontend (Port 3000)**:
  ```cmd
  cd frontend
  npm run dev
  ```

## Common Windows Issues & Solutions

### 1. Execution Policy Restricted Error
When executing `setup.ps1`, if PowerShell raises a security exception regarding executing scripts:
- **Solution**: Execute the script bypassing the policy locally:
  ```powershell
  PowerShell.exe -ExecutionPolicy Bypass -File .\setup.ps1
  ```

### 2. Node/NPM command not recognized
If running `npm install` fails with `command not found`:
- **Solution**: Ensure Node.js binary folder is added to user environment variables and restart your terminal.

### 3. File locks on SQLite database
SQLite throws `sqlite3.OperationalError: database is locked` on Windows when multiple tasks attempt simultaneous writes.
- **Solution**: SentinelFlow AI automatically configures write-ahead-logging (WAL) journal mode on startup hooks.
