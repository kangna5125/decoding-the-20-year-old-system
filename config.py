"""Global configuration and settings for Decoding the 20 Year Old System."""
import os


def load_env(env_path: str = ".env"):
    """Safely load environment variables from .env file without external dependencies."""
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass


# Load .env immediately
load_env()

# Project Info
PROJECT_NAME = "Decoding the 20 Year Old System"
PROJECT_TAGLINE = "Decode. Understand. Modernize. Preserve."
CHATBOT_NAME = "Legacy Assistant"

# Supported Languages
SUPPORTED_LANGUAGES = ["Python", "Java", "JavaScript", "C++"]

LANGUAGE_EXTENSIONS = {
    "Python": [".py"],
    "Java": [".java"],
    "JavaScript": [".js", ".jsx", ".mjs"],
    "C++": [".cpp", ".cc", ".cxx", ".hpp", ".h"]
}

# Model Settings
CODET5_MODEL_DIR = os.environ.get("MODEL_DIR", "models/codet5-small-csn")

# Dynamic Gemini Model Setting (updated via automatic selection when API key is present)
SELECTED_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "")

# Database
DB_PATH = os.environ.get("DB_PATH", "corrections.db")

# Privacy Notice
PRIVACY_NOTE = (
    "Privacy Notice: Source code analyzed using LLM features is sent to the Gemini API. "
    "Use demo or open-source code only; avoid uploading confidential or proprietary source code."
)
