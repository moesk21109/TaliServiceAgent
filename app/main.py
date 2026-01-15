"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to sys.path to allow running this file directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load env vars with explicit path
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)
print(f"[STARTUP] Loaded .env from: {env_path}")
print(f"[STARTUP] MOCK_LEXWARE={os.getenv('MOCK_LEXWARE')}")
print(f"[STARTUP] LEXWARE_API_KEY={'***' + os.getenv('LEXWARE_API_KEY', '')[-5:] if os.getenv('LEXWARE_API_KEY') else 'NOT SET'}")

from app.db import init_db
from app.routers import customers, documents, chat, general_chat, usage

# Initialize database
init_db()

# Migrate database schema (add new columns if needed)
# Note: On fresh PostgreSQL deployments, tables are created fresh by init_db()
# These migrations are only needed for existing SQLite databases
try:
    from sqlmodel import Session, text
    from app.db import engine, DATABASE_URL
    
    # Skip migrations for fresh PostgreSQL (tables created by init_db)
    if "postgresql" in DATABASE_URL or "postgres" in DATABASE_URL:
        print("[MIGRATION] PostgreSQL detected - using fresh schema from init_db()")
    else:
        with Session(engine) as session:
            # Customer columns (SQLite only)
            try:
                session.exec(text("SELECT customer_type FROM customer LIMIT 1"))
            except:
                print("[MIGRATION] Adding customer_type, vat_id, tax_number columns...")
                session.exec(text("ALTER TABLE customer ADD COLUMN customer_type VARCHAR DEFAULT 'privat'"))
                session.exec(text("ALTER TABLE customer ADD COLUMN vat_id VARCHAR"))
                session.exec(text("ALTER TABLE customer ADD COLUMN tax_number VARCHAR"))
                session.commit()
                print("[MIGRATION] ✅ Customer columns added!")
            
            # ChatMessage is_file_upload column (SQLite only)
            try:
                session.exec(text("SELECT is_file_upload FROM chatmessage LIMIT 1"))
            except:
                print("[MIGRATION] Adding is_file_upload column to chatmessage...")
                session.exec(text("ALTER TABLE chatmessage ADD COLUMN is_file_upload BOOLEAN DEFAULT 0"))
                session.commit()
                print("[MIGRATION] ✅ is_file_upload column added!")
except Exception as e:
    print(f"[MIGRATION] Note: {e}")

# Create app
app = FastAPI(title="TaliServiceAgent", description="AI-assisted document generation with Lexware")


# Add request logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    print(f"[REQUEST] {request.method} {request.url}")
    try:
        response = await call_next(request)
        print(f"[RESPONSE] {response.status_code}")
        return response
    except Exception as e:
        print(f"[ERROR] {e}")
        raise


# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(customers.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(general_chat.router)
app.include_router(usage.router)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root():
    """Serve main HTML page (live.html) with no-cache headers."""
    return FileResponse(
        "static/live.html", 
        media_type="text/html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@app.get("/live.html")
def live_html():
    """Serve customer chat interface with no-cache headers."""
    return FileResponse(
        "static/live.html", 
        media_type="text/html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@app.get("/general-chat.html")
def general_chat_html():
    """Serve general chat interface."""
    return FileResponse("static/general-chat.html", media_type="text/html")


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/products")
def get_products():
    """Get products from Lexware."""
    from app.lexware_client import lexware_client
    return lexware_client.get_products()


@app.get("/api/services")
def get_services():
    """Get services from Lexware."""
    from app.lexware_client import lexware_client
    return lexware_client.get_services()
