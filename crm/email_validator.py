"""
Dedolytics Pre-send Email Validation

Uses mailcheck.ai (no API key required) to screen disposable and blocked addresses
before SMTP dispatch. Fails open — if the API is unavailable, the send is allowed.
"""

import requests


def validate_email(email: str) -> dict:
    """
    Validates an email address before dispatch.

    Checks:
    - Disposable / throwaway address (Mailinator, Guerrilla Mail, etc.)
    - Blocked domain (known spam/abuse domains)

    Returns:
        {'valid': bool, 'reason': str}
        reason values: 'ok', 'disposable', 'domain_blocked', 'api_unavailable'

    Always fails open: if the API is unreachable, returns valid=True so the
    pipeline is not blocked by a transient network issue.
    """
    try:
        resp = requests.get(
            f"https://api.mailcheck.ai/email/{email}",
            timeout=5,
            headers={"User-Agent": "Dedolytics/1.0"},
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("block"):
                return {"valid": False, "reason": "domain_blocked"}
            if data.get("disposable"):
                return {"valid": False, "reason": "disposable"}
            return {"valid": True, "reason": "ok"}
    except Exception:
        pass  # Network error or timeout — fail open

    return {"valid": True, "reason": "api_unavailable"}
