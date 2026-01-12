"""Entry point - Run FastAPI server."""

import uvicorn
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables before importing the app
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

from app.main import app

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8000, reload=False)
