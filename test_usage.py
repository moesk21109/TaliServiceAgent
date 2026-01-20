"""Test API usage tracking."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import init_db, engine
from app.models import APIUsage, APIUsageStats
from sqlmodel import Session, select
from datetime import datetime

def test_usage_tracking():
    """Test that usage tracking works."""
    
    # Initialize database
    print("Initializing database...")
    init_db()
    
    # Create a session
    with Session(engine) as session:
        # Clean up any existing test data
        existing = session.exec(select(APIUsage)).all()
        for record in existing:
            session.delete(record)
        session.commit()
        
        # Create test usage record
        print("Creating test usage record...")
        usage = APIUsage(
            provider="openai",
            model="gpt-4o-mini",
            endpoint="test_endpoint",
            tokens_used=150,
            request_successful=True
        )
        session.add(usage)
        session.commit()
        
        # Verify record was created
        print("Verifying record...")
        all_records = session.exec(select(APIUsage)).all()
        assert len(all_records) == 1, f"Expected 1 record, got {len(all_records)}"
        
        record = all_records[0]
        assert record.provider == "openai"
        assert record.model == "gpt-4o-mini"
        assert record.endpoint == "test_endpoint"
        assert record.tokens_used == 150
        assert record.request_successful == True
        
        print("✅ Usage tracking test passed!")
        
        # Create another failed request
        print("Creating failed request record...")
        failed_usage = APIUsage(
            provider="openai",
            model="gpt-4o-mini",
            endpoint="test_endpoint",
            tokens_used=0,
            request_successful=False,
            error_message="Test error"
        )
        session.add(failed_usage)
        session.commit()
        
        # Verify we now have 2 records
        all_records = session.exec(select(APIUsage)).all()
        assert len(all_records) == 2, f"Expected 2 records, got {len(all_records)}"
        
        print("✅ Failed request tracking test passed!")
        
        # Clean up
        print("Cleaning up test data...")
        for record in all_records:
            session.delete(record)
        session.commit()
        
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_usage_tracking()
