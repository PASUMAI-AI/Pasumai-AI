"""Telegram long-polling runner, for local development without a public URL.

Telegram's webhook mode requires an HTTPS URL it can reach, which localhost
is not. This script pulls updates itself (long polling) and feeds them into
the exact same handlers telegram_api.py uses for the webhook, so behaviour
is identical - this is only a different transport for reaching Telegram.

Run it alongside the FastAPI server:

    python telegram_poll.py

Ctrl+C to stop. Do not run this while a webhook is registered with Telegram -
it calls deleteWebhook on startup to make sure getUpdates is allowed.
"""
import os, time
from dotenv import load_dotenv

load_dotenv()

import requests

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
if not TOKEN:
    raise SystemExit("TELEGRAM_BOT_TOKEN is not set in .env")

API_URL = f"https://api.telegram.org/bot{TOKEN}"

from whatsapp_api import init_whatsapp_schema
from telegram_api import init_telegram_schema, process_update

init_whatsapp_schema()
init_telegram_schema()


def main():
    requests.post(f"{API_URL}/deleteWebhook", timeout=15)
    print("[TELEGRAM] Webhook cleared. Polling for updates. Press Ctrl+C to stop.", flush=True)

    offset = None
    while True:
        try:
            params = {"timeout": 30}
            if offset is not None:
                params["offset"] = offset
            r = requests.get(f"{API_URL}/getUpdates", params=params, timeout=40)
            r.raise_for_status()
            for update in r.json().get("result", []):
                offset = update["update_id"] + 1
                try:
                    process_update(update)
                except Exception as e:
                    print(f"[TELEGRAM] Update handling failed: {e}")
        except requests.exceptions.RequestException as e:
            print(f"[TELEGRAM] Poll error: {e}")
            time.sleep(3)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[TELEGRAM] Stopped.")
