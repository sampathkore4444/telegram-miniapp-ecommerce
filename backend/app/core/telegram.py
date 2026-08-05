"""Telegram WebApp authentication helpers.

initData signature validation follows the Telegram documented algorithm:
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""
import hashlib
import hmac
import json
import logging
import time
from typing import Any
from urllib.parse import parse_qsl

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_HASH_FIELD = "hash"


class TelegramAuthError(Exception):
    pass


def _bot_secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def validate_init_data(init_data: str, bot_token: str | None = None) -> dict[str, str]:
    """Validate raw initData and return the parsed key/values.

    Raises TelegramAuthError when the payload is invalid or expired.
    """
    token = bot_token or settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise TelegramAuthError("TELEGRAM_BOT_TOKEN is not configured")

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    signature = parsed.pop(_HASH_FIELD, None)
    if not signature:
        raise TelegramAuthError("missing hash in initData")

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )
    computed = hmac.new(
        _bot_secret_key(token), data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed, signature):
        raise TelegramAuthError("invalid initData signature")

    auth_date = int(parsed.get("auth_date", "0"))
    max_age = settings.TELEGRAM_AUTH_MAX_AGE_SECONDS
    if max_age > 0 and (time.time() - auth_date) > max_age:
        raise TelegramAuthError("initData is expired")

    return parsed


def extract_user(parsed: dict[str, str]) -> dict[str, Any]:
    """Extract a normalized user dict from validated initData."""
    user = json.loads(parsed.get("user", "{}"))
    if not isinstance(user, dict) or not user.get("id"):
        raise TelegramAuthError("initData does not contain a valid user")

    return {
        "telegram_id": int(user["id"]),
        "username": (user.get("username") or "").strip() or None,
        "first_name": (user.get("first_name") or "").strip() or None,
        "last_name": (user.get("last_name") or "").strip() or None,
        "photo_url": (user.get("photo_url") or "").strip() or None,
        "auth_date": parsed.get("auth_date"),
        "start_param": parsed.get("start_param"),
    }


async def send_telegram_message(chat_id: int, text: str, bot_token: str | None = None) -> bool:
    """Send a plain message to a Telegram user. Returns True on success.

    Failures are logged and swallowed: messaging must never break a request.
    """
    token = bot_token or settings.TELEGRAM_BOT_TOKEN
    if not token:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                url, json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
            )
            if resp.status_code != 200:
                logger.warning("telegram send failed: %s %s", resp.status_code, resp.text)
                return False
            return True
    except httpx.HTTPError as exc:
        logger.warning("telegram send error: %s", exc)
        return False


async def notify_admins(text: str, bot_token: str | None = None) -> int:
    """Send a message to every configured admin. Returns how many were delivered."""
    sent = 0
    for admin_id in settings.admin_ids:
        ok = await send_telegram_message(admin_id, text, bot_token=bot_token)
        if ok:
            sent += 1
    return sent
