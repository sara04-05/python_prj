from uuid import uuid4
from dotenv import load_dotenv, set_key
import os


def generate_and_save_api_key():
    # Load environment variables
    load_dotenv()

    # Generate a new API key
    api_key = str(uuid4())
    print(f"Generated API Key: {api_key}")

    # Define the path for the .env file in the root directory
    root_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    env_file = os.path.join(root_directory, ".env")

    # Ensure the .env file exists
    if not os.path.isfile(env_file):
        open(env_file, 'w').close()

    # Get existing API keys
    existing_keys = os.getenv("API_KEYS", "")

    # Handle existing keys
    if existing_keys:
        # Ensure no extra commas are present
        existing_keys = existing_keys.strip(', ')
        # Append new API key with a comma separator if necessary
        new_keys = f"{existing_keys},{api_key}" if existing_keys else api_key
    else:
        new_keys = api_key

    # Update the .env file with the new list of API keys
    set_key(env_file, "API_KEYS", new_keys)
    print(f"API Keys updated: {new_keys}")


if __name__ == "__main__":
    generate_and_save_api_key()
