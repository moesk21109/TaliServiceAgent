from sqlmodel import SQLModel, create_engine, Session
import os

# Database URL from env or default to SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)


def init_db():
    """Initialize database tables."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency injection for FastAPI."""
    with Session(engine) as session:
        yield session
