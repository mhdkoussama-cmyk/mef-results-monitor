#!/usr/bin/env python3
"""
Standalone Telegram connectivity test.
"""

import os
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def main():
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID env vars.")
        return

    url = "https://api.telegram.org/bot{}/sendMessage".format(TELEGRAM_TOKEN)
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": "\u2705 Test alert: MEF monitor Telegram wiring works correctly.",
        "parse_mode": "HTML",
    }
    r = requests.post(url, data=payload, timeout=20)
    print(r.status_code, r.text)

if __name__ == "__main__":
    main()
