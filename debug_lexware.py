import os
from dotenv import load_dotenv
from app.lexware_client import LexwareClient

# Load env vars
from pathlib import Path
env_path = Path('.') / '.env'
print(f"Loading .env from: {env_path.absolute()}")
print(f"File exists: {env_path.exists()}")
if env_path.exists():
    print(f"File content:\n{env_path.read_text()}")

success = load_dotenv(dotenv_path=env_path, override=True, verbose=True)
print(f"load_dotenv success: {success}")

print(f"MOCK_LEXWARE: {os.getenv('MOCK_LEXWARE')}")
print(f"LEXWARE_API_BASE_URL: {os.getenv('LEXWARE_API_BASE_URL')}")
# Mask key for security in logs
key = os.getenv('LEXWARE_API_KEY')
print(f"LEXWARE_API_KEY: {key[:5]}...{key[-5:] if key else 'None'}")

# Force mock off for testing
os.environ["MOCK_LEXWARE"] = "false"

client = LexwareClient()
print("\nAttempting to fetch customers...")
customers = client.get_customers()
print(f"\nResult: {len(customers)} customers found.")
print(customers)
