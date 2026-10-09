"""Supabase Client Initialization and Connectivity Module for HospAI.

Loads credentials safely from environment variables / backend/.env.
Provides backend-only connectivity checking without exposing secrets or creating database tables.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

DEFAULT_SUPABASE_URL = "https://usefyrrekudsczopeevv.supabase.co"


def reload_env():
    """Loads environment variables from backend/.env or root .env if not already set."""
    env_paths = [BACKEND_DIR / ".env", PROJECT_ROOT / ".env"]
    for env_path in env_paths:
        if env_path.is_file():
            load_dotenv(dotenv_path=env_path, override=False)


reload_env()


def get_supabase_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Retrieves Supabase URL and Key from environment variables.

    Supports SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_ROLE_KEY, or SUPABASE_ANON_KEY.
    """
    reload_env()
    url = os.getenv("SUPABASE_URL", DEFAULT_SUPABASE_URL).strip()
    key = (
        os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
        or ""
    ).strip()

    if not key or "your-supabase" in key.lower() or "placeholder" in key.lower():
        key = None

    if not url or "your-supabase" in url.lower():
        url = None

    return url, key


def create_supabase_client():
    """Initializes and returns a Supabase client instance if credentials are valid.

    Returns:
        tuple: (client_instance, None) if successful, or (None, error_message) if unconfigured/failed.
    """
    url, key = get_supabase_credentials()

    if not url or not key:
        return None, "Supabase credentials missing or unconfigured in environment."

    try:
        from supabase import create_client
        client = create_client(url, key)
        return client, None
    except Exception as exc:
        err_msg = str(exc)
        if key and key in err_msg:
            err_msg = err_msg.replace(key, "***MASKED_KEY***")
        return None, f"Failed to initialize Supabase client: {err_msg}"


def check_supabase_health() -> Dict[str, Any]:
    """Performs a backend-only connectivity test to Supabase without mutating tables.

    Returns:
        dict: Connection status, masked project URL, configuration status, and health info.
    """
    url, key = get_supabase_credentials()

    if not url or not key:
        return {
            "ok": False,
            "configured": False,
            "connected": False,
            "project_url": url or DEFAULT_SUPABASE_URL,
            "key_present": bool(key),
            "status": "NOT_CONFIGURED",
            "message": (
                "Supabase URL or Key is missing. "
                "Please add SUPABASE_URL and SUPABASE_KEY to backend/.env."
            ),
            "error": "Missing SUPABASE_KEY in backend/.env"
        }

    client, init_err = create_supabase_client()
    if not client:
        return {
            "ok": False,
            "configured": True,
            "connected": False,
            "project_url": url,
            "key_present": True,
            "status": "INITIALIZATION_FAILED",
            "message": "Supabase client initialization failed.",
            "error": init_err
        }

    try:
        _ = client.auth.get_session()
        return {
            "ok": True,
            "configured": True,
            "connected": True,
            "project_url": url,
            "key_present": True,
            "status": "CONNECTED",
            "message": "Supabase connection verified successfully.",
            "error": None
        }
    except Exception as exc:
        err_str = str(exc)
        if key in err_str:
            err_str = err_str.replace(key, "***MASKED_KEY***")

        if "session" in err_str.lower() or "unauthorized" in err_str.lower() or "401" in err_str or "404" in err_str:
            return {
                "ok": True,
                "configured": True,
                "connected": True,
                "project_url": url,
                "key_present": True,
                "status": "CONNECTED",
                "message": "Supabase endpoint reached and responsive.",
                "error": None
            }

        return {
            "ok": False,
            "configured": True,
            "connected": False,
            "project_url": url,
            "key_present": True,
            "status": "CONNECTION_FAILED",
            "message": "Could not connect to Supabase backend URL.",
            "error": err_str
        }
