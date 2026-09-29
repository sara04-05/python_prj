import os
import uuid

from dotenv import load_dotenv, set_key


def generate_key():
    """Generate and save one API key in the local .env file."""
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    load_dotenv(env_file)

    new_key = str(uuid.uuid4())
    set_key(env_file, "API_KEYS", new_key)

    print(new_key)
    return new_key


if __name__ == "__main__":
    generate_key()
