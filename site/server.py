#!/usr/bin/env python3
"""ShopTrolley marketing site — static server + signup email relay (Python stdlib only).

Serves the static site and accepts POST /api/signup, emailing each signup via
smtplib to your own mailbox. No third-party form service required.

Usage:
    cp .env.example .env      # fill in your SMTP credentials
    python3 server.py         # serves http://localhost:8090
    PORT=8080 python3 server.py

Environment variables (also read from site/.env):
    SMTP_HOST       SMTP server, e.g. smtp.gmail.com / smtp.zoho.com
    SMTP_PORT       usually 587 (STARTTLS) or 465 (SSL)
    SMTP_USER       login / From address
    SMTP_PASS       app password (not your normal password)
    SMTP_USE_SSL    "1" to use implicit SSL (port 465)
    MAIL_TO         where signups are delivered (defaults to SMTP_USER)
    PORT            HTTP port for the site (default 8090)
"""
from __future__ import annotations

import json
import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def send_signup_email(payload: dict) -> None:
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASS"]
    to = os.environ.get("MAIL_TO", user)
    use_ssl = os.environ.get("SMTP_USE_SSL", "").lower() in ("1", "true", "yes")

    subject = f"[ShopTrolley] New signup: {payload.get('store_name', '?')} ({payload.get('market', '?')})"

    rows = [
        ("Store name", payload.get("store_name", "")),
        ("Your name", payload.get("name", "")),
        ("Email", payload.get("email", "")),
        ("Primary market", payload.get("market", "")),
        ("Telegram", payload.get("telegram") or "—"),
        ("Language", payload.get("language", "")),
    ]
    text = "New ShopTrolley signup\n\n" + "\n".join(f"{k}: {v}" for k, v in rows)
    html = (
        "<h2 style='margin:0 0 12px'>New ShopTrolley signup</h2>"
        "<table cellpadding='6' style='border-collapse:collapse;font-family:Arial,sans-serif;font-size:14px'>"
        + "".join(
            f"<tr><td style='color:#5b6479;font-weight:bold;padding-right:16px'>{k}</td>"
            f"<td>{v}</td></tr>"
            for k, v in rows
        )
        + "</table>"
    )

    msg = MIMEMultipart("alternative")
    msg["From"] = f"ShopTrolley Signups <{user}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    if use_ssl:
        server = smtplib.SMTP_SSL(host, port, timeout=20)
    else:
        server = smtplib.SMTP(host, port, timeout=20)
        server.starttls()
    try:
        server.login(user, password)
        server.send_message(msg)
    finally:
        server.quit()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _json(self, status: int, obj: dict) -> None:
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/signup":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            payload = {}

        store = str(payload.get("store_name", "")).strip()
        name = str(payload.get("name", "")).strip()
        email = str(payload.get("email", "")).strip()

        if not (store and name and email and EMAIL_RE.match(email)):
            self._json(400, {"ok": False, "error": "invalid"})
            return

        try:
            send_signup_email(
                {
                    **payload,
                    "store_name": store,
                    "name": name,
                    "email": email,
                    "language": str(payload.get("language", "en")),
                }
            )
        except Exception as exc:  # noqa: BLE001 - surface any SMTP failure
            print(f"[signup] email failed: {exc}")
            self._json(500, {"ok": False, "error": "email_failed"})
            return

        print(f"[signup] {email} — {store} ({payload.get('market', '?')})")
        self._json(200, {"ok": True})


def main() -> None:
    load_env(ROOT / ".env")
    port = int(os.environ.get("PORT", "8090"))
    httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"ShopTrolley site: http://localhost:{port}  (signups via SMTP)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
