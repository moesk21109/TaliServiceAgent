"""Start server with custom configuration for large file uploads."""

import uvicorn
from uvicorn.config import LOGGING_CONFIG

if __name__ == "__main__":
    # Configure logging
    log_config = LOGGING_CONFIG.copy()
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # Für alle Geräte im Netzwerk erreichbar
        port=8000,
        reload=True,
        # Increase limits for large PDF uploads (100 MB)
        limit_concurrency=1000,
        limit_max_requests=10000,
        timeout_keep_alive=300,  # 5 minutes
        log_config=log_config,
        # Access log for debugging
        access_log=True,
    )
