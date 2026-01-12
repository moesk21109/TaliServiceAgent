"""
Database migration script to add customer_type, vat_id, and tax_number fields.
Run this once to update the database schema.
"""
from sqlmodel import Session, text
from app.db import engine

def migrate():
    print("[MIGRATION] Adding new customer fields...")
    
    with Session(engine) as session:
        try:
            # Check if columns exist
            session.exec(text("SELECT customer_type FROM customer LIMIT 1"))
            print("[MIGRATION] Columns already exist, skipping.")
        except:
            print("[MIGRATION] Adding customer_type, vat_id, tax_number columns...")
            
            # Add new columns with default values
            session.exec(text("ALTER TABLE customer ADD COLUMN customer_type VARCHAR DEFAULT 'privat'"))
            session.exec(text("ALTER TABLE customer ADD COLUMN vat_id VARCHAR"))
            session.exec(text("ALTER TABLE customer ADD COLUMN tax_number VARCHAR"))
            
            session.commit()
            print("[MIGRATION] ✅ Migration complete!")

if __name__ == "__main__":
    migrate()
