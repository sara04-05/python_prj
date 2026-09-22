"""
Generate a secure API key for the astronomy APOD application.
Run this once and save the key to your .env file as API_KEY
"""
import secrets


def generate_api_key(length: int = 32) -> str:
    """Generate a cryptographically secure API key."""
    return secrets.token_urlsafe(length)


if __name__ == "__main__":
    key = generate_api_key()
    print(f"Generated API Key: {key}")
    print(f"\nAdd this to your .env file:")
    print(f"API_KEY={key}")
