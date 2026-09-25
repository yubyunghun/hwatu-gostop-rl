from functools import lru_cache

from api.bot_inference import load_search_bot_policy
from api.session_manager import SessionManager


@lru_cache
def get_session_manager() -> SessionManager:
    return SessionManager()


@lru_cache
def get_bot_policy():
    return load_search_bot_policy()
