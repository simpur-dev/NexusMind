"""
Application configuration loaded from environment variables and the project .env file.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(dotenv_path=None, override=False):
        env_path = Path(dotenv_path or Path.cwd() / '.env')
        if not env_path.exists():
            return
        for raw_line in env_path.read_text(encoding='utf-8').splitlines():
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if override or key not in os.environ:
                os.environ[key] = value


APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
PROJECT_ENV = PROJECT_ROOT / '.env'

if PROJECT_ENV.exists():
    load_dotenv(PROJECT_ENV, override=True)
else:
    load_dotenv(override=True)


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    """Runtime configuration for the Flask application."""

    SECRET_KEY = os.environ.get('SECRET_KEY', 'nexusmind-secret-key')
    DEBUG = _bool_env('FLASK_DEBUG', True)
    JSON_AS_ASCII = False

    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')

    NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USERNAME = os.environ.get('NEO4J_USERNAME', 'neo4j')
    NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'neo4jneo4j')
    NEO4J_DATABASE = os.environ.get('NEO4J_DATABASE', 'neo4j')
    GRAPHITI_OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY') or os.environ.get('LLM_API_KEY')
    EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL', 'text-embedding-v3')

    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    UPLOAD_FOLDER = str(APP_DIR / '..' / 'uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}

    DEFAULT_CHUNK_SIZE = _int_env('DEFAULT_CHUNK_SIZE', 1500)
    DEFAULT_CHUNK_OVERLAP = _int_env('DEFAULT_CHUNK_OVERLAP', 100)

    OASIS_DEFAULT_MAX_ROUNDS = _int_env('OASIS_DEFAULT_MAX_ROUNDS', 10)
    OASIS_SIMULATION_DATA_DIR = str(APP_DIR / '..' / 'uploads' / 'simulations')
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]

    REPORT_AGENT_MAX_TOOL_CALLS = _int_env('REPORT_AGENT_MAX_TOOL_CALLS', 5)
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = _int_env('REPORT_AGENT_MAX_REFLECTION_ROUNDS', 2)
    REPORT_AGENT_TEMPERATURE = _float_env('REPORT_AGENT_TEMPERATURE', 0.5)

    @classmethod
    def validate(cls):
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY is not configured")
        if not cls.GRAPHITI_OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY or LLM_API_KEY is required for Graphiti")
        return errors
