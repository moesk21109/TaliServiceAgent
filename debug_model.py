from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field

try:
    class Customer(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        name: str

    print("Customer model created successfully")
except Exception as e:
    print(f"Error creating model: {e}")
    import traceback
    traceback.print_exc()
