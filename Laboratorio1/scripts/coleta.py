import os

from dotenv import load_dotenv

load_dotenv()


def get_github_token() -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN não está definida. Configure um .env a partir de .env.example."
        )
    return token
