import hmac
import hashlib
import json
from urllib.parse import parse_qs, unquote
from datetime import datetime, timedelta
from typing import Optional

def verify_telegram_init_data(init_data: str, bot_token: str) -> Optional[dict]:
    """
    Verify Telegram initData signature.
    Returns parsed data if valid, else None.
    """
    if not init_data:
        return None

    # Parse the query string
    parsed = parse_qs(init_data)
    received_hash = parsed.pop('hash', [None])[0]
    if not received_hash:
        return None

    # Sort keys and create data-check-string
    items = []
    for key in sorted(parsed.keys()):
        values = parsed[key]
        # For auth_date, user, etc. we need to handle properly
        # The value should be unquoted
        val = values[0]
        items.append(f"{key}={unquote(val)}")

    data_check_string = "\n".join(items)

    # Compute secret key from bot token
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()

    # Compute hash
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if computed_hash != received_hash:
        return None

    # Parse user data (JSON)
    user_str = parsed.get('user', [None])[0]
    if user_str:
        try:
            user_data = json.loads(unquote(user_str))
        except:
            user_data = {}
    else:
        user_data = {}

    return {
        "telegram_id": user_data.get("id"),
        "username": user_data.get("username"),
        "first_name": user_data.get("first_name"),
        "auth_date": parsed.get('auth_date', [None])[0],
    }

def is_bonus_available(last_bonus_time: Optional[datetime]) -> bool:
    if last_bonus_time is None:
        return True
    now = datetime.utcnow()
    return (now - last_bonus_time) > timedelta(hours=22)
