from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.orm import relationship


class ChatMessage(SQLModel, table=True):
    """Individual chat messages with role (user/assistant)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="chatsession.id")
    role: str  # "user" or "assistant"
    content: str
    is_file_upload: bool = Field(default=False)  # True if message is a file upload
    created_at: datetime = Field(default_factory=datetime.utcnow)
    session: Optional["ChatSession"] = Relationship(
        back_populates="messages",
        sa_relationship=relationship("ChatSession", back_populates="messages")
    )


class Document(SQLModel, table=True):
    """AI-generated business document (Angebot/Rechnung) - ALWAYS DRAFT."""
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customer.id")
    chat_session_id: Optional[int] = Field(default=None, foreign_key="chatsession.id")
    doc_type: str  # "angebot" or "rechnung"
    title: str
    content: str  # AI-generated markdown/text
    is_draft: bool = Field(default=True)  # CRITICAL: Always True
    model_used: str  # "gpt-4o-mini"
    provider: str  # "openai"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    customer: "Customer" = Relationship(
        back_populates="documents",
        sa_relationship=relationship("Customer", back_populates="documents")
    )


class ChatSession(SQLModel, table=True):
    """Chat session per customer (like Claude threads)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customer.id")
    title: str  # e.g., "Angebot für Projekt X"
    topic: Optional[str] = None  # "angebot", "rechnung", "general"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    customer: "Customer" = Relationship(
        back_populates="chat_sessions",
        sa_relationship=relationship("Customer", back_populates="chat_sessions")
    )
    messages: List[ChatMessage] = Relationship(
        back_populates="session",
        sa_relationship=relationship("ChatMessage", back_populates="session")
    )


class Customer(SQLModel, table=True):
    """Customer from Lexware."""
    id: Optional[int] = Field(default=None, primary_key=True)
    lexware_id: str = Field(unique=True, index=True)  # Lexware customer ID
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    customer_type: Optional[str] = Field(default="privat")  # "privat" or "gewerbe"
    vat_id: Optional[str] = None  # Umsatzsteuer-ID (für § 13b UStG)
    tax_number: Optional[str] = None  # Steuernummer
    tax_id: Optional[str] = None  # Legacy field
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    documents: List[Document] = Relationship(
        back_populates="customer",
        sa_relationship=relationship("Document", back_populates="customer")
    )
    chat_sessions: List[ChatSession] = Relationship(
        back_populates="customer",
        sa_relationship=relationship("ChatSession", back_populates="customer")
    )


# Pydantic schemas for API requests/responses
class ChatSessionResponse(SQLModel):
    """Chat session response."""
    id: int
    customer_id: int
    title: str
    topic: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ChatMessageResponse(SQLModel):
    """Chat message response."""
    id: int
    session_id: int
    role: str
    content: str
    is_file_upload: bool = False
    created_at: datetime


class ChatSessionCreate(SQLModel):
    """Create new chat session."""
    customer_id: int
    title: str
    topic: Optional[str] = None


class ChatMessageCreate(SQLModel):
    """Send chat message."""
    session_id: int
    content: str


class CustomerResponse(SQLModel):
    """Customer API response."""
    id: int
    lexware_id: str
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    customer_type: Optional[str] = "privat"  # "privat" or "gewerbe"


class CustomerCreate(SQLModel):
    """Customer creation payload for Lexware."""
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    customer_type: Optional[str] = "privat"  # "privat" or "gewerbe"
    vat_id: Optional[str] = None  # Umsatzsteuer-ID (für § 13b UStG)
    tax_number: Optional[str] = None  # Steuernummer


class DocumentCreate(SQLModel):
    """Document creation payload."""
    customer_id: int
    doc_type: str  # "angebot" or "rechnung"
    prompt: str  # Custom user prompt for document
    provider: str = "openai"  # "openai"
    model: str = "gpt-4o-mini"


class DocumentResponse(SQLModel):
    """Document API response."""
    id: int
    customer_id: int
    doc_type: str
    title: str
    content: str
    is_draft: bool
    model_used: str
    provider: str
    created_at: datetime


class APIUsage(SQLModel, table=True):
    """Track API usage for monitoring and limits."""
    id: Optional[int] = Field(default=None, primary_key=True)
    provider: str  # "openai", "anthropic", etc.
    model: str  # "gpt-4o-mini", etc.
    endpoint: str  # "chat", "generate_document", etc.
    tokens_used: Optional[int] = None  # Total tokens used in request
    request_successful: bool = Field(default=True)  # Whether request succeeded
    error_message: Optional[str] = None  # Error details if failed
    created_at: datetime = Field(default_factory=datetime.utcnow)


class APIUsageStats(SQLModel):
    """API usage statistics response."""
    total_requests: int
    total_tokens: int
    requests_today: int
    tokens_today: int
    requests_this_month: int
    tokens_this_month: int
    failed_requests: int
    last_request_at: Optional[datetime] = None
