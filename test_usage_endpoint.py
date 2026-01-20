"""Test API usage endpoints."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db, engine
from app.models import APIUsage
from sqlmodel import Session, select
from datetime import datetime

# Initialize database
init_db()

client = TestClient(app)

def test_usage_stats_endpoint():
    """Test the /usage/stats endpoint."""
    
    # Clean up existing data
    with Session(engine) as session:
        existing = session.exec(select(APIUsage)).all()
        for record in existing:
            session.delete(record)
        session.commit()
        
        # Create test data
        print("Creating test usage data...")
        for i in range(5):
            usage = APIUsage(
                provider="openai",
                model="gpt-4o-mini",
                endpoint=f"test_endpoint_{i}",
                tokens_used=100 + i * 10,
                request_successful=True
            )
            session.add(usage)
        
        # Add one failed request
        failed = APIUsage(
            provider="openai",
            model="gpt-4o-mini",
            endpoint="failed_test",
            tokens_used=0,
            request_successful=False,
            error_message="Test error"
        )
        session.add(failed)
        session.commit()
    
    # Test the stats endpoint
    print("Testing /usage/stats endpoint...")
    response = client.get("/usage/stats")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.json()
    print(f"Response: {data}")
    
    assert "total_requests" in data
    assert "total_tokens" in data
    assert "requests_today" in data
    assert "failed_requests" in data
    
    assert data["total_requests"] == 6, f"Expected 6 requests, got {data['total_requests']}"
    assert data["failed_requests"] == 1, f"Expected 1 failed request, got {data['failed_requests']}"
    assert data["total_tokens"] == sum([100 + i * 10 for i in range(5)]), f"Token sum mismatch"
    
    print("✅ /usage/stats endpoint test passed!")
    
    # Test the recent requests endpoint
    print("Testing /usage/requests endpoint...")
    response = client.get("/usage/requests?limit=10")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.json()
    print(f"Found {len(data)} recent requests")
    
    assert len(data) == 6, f"Expected 6 requests, got {len(data)}"
    assert isinstance(data, list)
    
    # Verify the failed request is in the list
    failed_requests = [r for r in data if not r["request_successful"]]
    assert len(failed_requests) == 1
    assert failed_requests[0]["error_message"] == "Test error"
    
    print("✅ /usage/requests endpoint test passed!")
    
    # Clean up
    with Session(engine) as session:
        existing = session.exec(select(APIUsage)).all()
        for record in existing:
            session.delete(record)
        session.commit()
    
    print("\n✅ All endpoint tests passed!")


if __name__ == "__main__":
    test_usage_stats_endpoint()
