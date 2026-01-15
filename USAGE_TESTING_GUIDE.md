"""
Manual Test Guide for API Usage Tracking
=========================================

This guide shows how to test the API usage tracking endpoints manually.

## Prerequisites

1. Start the server:
   ```bash
   cd /home/runner/work/TaliServiceAgent/TaliServiceAgent
   python start_server.py
   ```

2. Or use uvicorn directly:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

## Test Endpoints

### 1. Get Usage Statistics

Get overall API usage statistics:

```bash
curl http://localhost:8000/usage/stats
```

Example response:
```json
{
  "total_requests": 150,
  "total_tokens": 45000,
  "requests_today": 25,
  "tokens_today": 7500,
  "requests_this_month": 150,
  "tokens_this_month": 45000,
  "failed_requests": 3,
  "last_request_at": "2024-01-15T13:20:00"
}
```

### 2. Get Recent Requests

View the last 50 API requests:

```bash
curl http://localhost:8000/usage/requests
```

With custom limit:

```bash
curl http://localhost:8000/usage/requests?limit=100
```

Example response:
```json
[
  {
    "id": 150,
    "provider": "openai",
    "model": "gpt-4o-mini",
    "endpoint": "chat_with_messages",
    "tokens_used": 320,
    "request_successful": true,
    "error_message": null,
    "created_at": "2024-01-15T13:20:00"
  },
  ...
]
```

### 3. Clear Old Records

Delete API usage records older than 30 days:

```bash
curl -X DELETE "http://localhost:8000/usage/clear?keep_days=30"
```

Delete all records:

```bash
curl -X DELETE "http://localhost:8000/usage/clear?keep_days=0"
```

## Using from Python

```python
import requests

# Get stats
response = requests.get("http://localhost:8000/usage/stats")
stats = response.json()

print(f"Total requests: {stats['total_requests']}")
print(f"Total tokens: {stats['total_tokens']}")
print(f"Requests today: {stats['requests_today']}")
print(f"Failed requests: {stats['failed_requests']}")

# Get recent requests
response = requests.get("http://localhost:8000/usage/requests?limit=10")
recent = response.json()

for req in recent:
    print(f"{req['created_at']}: {req['model']} - {req['tokens_used']} tokens")
```

## Using from Frontend (JavaScript)

```javascript
// Get usage stats
fetch('/usage/stats')
  .then(response => response.json())
  .then(data => {
    console.log(`Total requests: ${data.total_requests}`);
    console.log(`Total tokens: ${data.total_tokens}`);
    console.log(`Requests today: ${data.requests_today}`);
    console.log(`Failed requests: ${data.failed_requests}`);
  });

// Get recent requests
fetch('/usage/requests?limit=20')
  .then(response => response.json())
  .then(requests => {
    requests.forEach(req => {
      console.log(`${req.created_at}: ${req.endpoint} - ${req.tokens_used} tokens`);
    });
  });
```

## API Documentation

Once the server is running, you can also view the interactive API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Look for the "usage" tag to find all usage-related endpoints.
"""

if __name__ == "__main__":
    print(__doc__)
