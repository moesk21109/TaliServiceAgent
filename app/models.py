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


# ==========================================
# ELEKTRO-PLANER MODELS
# ==========================================

class FloorProject(SQLModel, table=True):
    """Elektro-Planer Projekt."""
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: Optional[int] = Field(default=None, foreign_key="customer.id")
    name: str  # "Kindergarten Wandsbek"
    address: Optional[str] = None
    notes: Optional[str] = None
    share_token: Optional[str] = Field(default=None, unique=True, index=True)  # For sharing
    share_enabled: bool = Field(default=False)
    share_can_add: bool = Field(default=True)
    share_can_move: bool = Field(default=True)
    share_can_delete: bool = Field(default=False)
    share_can_comment: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectFloor(SQLModel, table=True):
    """Stockwerk im Projekt."""
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="floorproject.id")
    name: str  # "EG", "OG", "UG", "DG"
    floor_plan_data: Optional[str] = None  # Base64 encoded image
    floor_plan_type: Optional[str] = None  # "image/png", "image/jpeg"
    scale_pixels_per_meter: Optional[float] = Field(default=50.0)
    order_index: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectRoom(SQLModel, table=True):
    """Raum auf einem Stockwerk."""
    id: Optional[int] = Field(default=None, primary_key=True)
    floor_id: int = Field(foreign_key="projectfloor.id")
    name: str  # "Küche"
    color: str = Field(default="#3498db")  # Hex color
    category: str = Field(default="bestand")  # "bestand", "neubau", "abbruch"
    x: float
    y: float
    width: float
    height: float
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectElement(SQLModel, table=True):
    """Elektro-Element im Projekt."""
    id: Optional[int] = Field(default=None, primary_key=True)
    floor_id: int = Field(foreign_key="projectfloor.id")
    room_id: Optional[int] = Field(default=None, foreign_key="projectroom.id")
    element_type: str  # "steckdose_schuko", "wechselschalter", etc.
    code: str  # "SD01", "WS02", etc.
    x: float
    y: float
    rotation: float = Field(default=0)  # 0, 90, 180, 270
    height: Optional[float] = None  # Mounting height in cm
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Pydantic schemas for Elektro-Planer API

class FloorProjectCreate(SQLModel):
    """Create new project."""
    name: str
    customer_id: Optional[int] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class FloorProjectResponse(SQLModel):
    """Project response."""
    id: int
    customer_id: Optional[int]
    name: str
    address: Optional[str]
    notes: Optional[str]
    share_token: Optional[str]
    share_enabled: bool
    created_at: datetime
    updated_at: datetime


class ProjectFloorCreate(SQLModel):
    """Create new floor."""
    project_id: int
    name: str
    floor_plan_data: Optional[str] = None
    floor_plan_type: Optional[str] = None
    scale_pixels_per_meter: Optional[float] = 50.0


class ProjectFloorResponse(SQLModel):
    """Floor response."""
    id: int
    project_id: int
    name: str
    floor_plan_data: Optional[str]
    floor_plan_type: Optional[str]
    scale_pixels_per_meter: Optional[float]
    order_index: int


class ProjectRoomCreate(SQLModel):
    """Create new room."""
    floor_id: int
    name: str
    color: str = "#3498db"
    category: str = "bestand"
    x: float
    y: float
    width: float
    height: float


class ProjectRoomResponse(SQLModel):
    """Room response."""
    id: int
    floor_id: int
    name: str
    color: str
    category: str
    x: float
    y: float
    width: float
    height: float


class ProjectElementCreate(SQLModel):
    """Create new element."""
    floor_id: int
    room_id: Optional[int] = None
    element_type: str
    code: str
    x: float
    y: float
    rotation: float = 0
    height: Optional[float] = None
    notes: Optional[str] = None


class ProjectElementResponse(SQLModel):
    """Element response."""
    id: int
    floor_id: int
    room_id: Optional[int]
    element_type: str
    code: str
    x: float
    y: float
    rotation: float
    height: Optional[float]
    notes: Optional[str]


class ProjectFullSave(SQLModel):
    """Full project save (all data at once)."""
    project: FloorProjectCreate
    floor: ProjectFloorCreate
    rooms: List[ProjectRoomCreate] = []
    elements: List[ProjectElementCreate] = []


class ProjectFullResponse(SQLModel):
    """Full project response with all data."""
    project: FloorProjectResponse
    floor: ProjectFloorResponse
    rooms: List[ProjectRoomResponse] = []
    elements: List[ProjectElementResponse] = []
