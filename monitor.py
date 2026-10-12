
name: MEF Final Results Monitor

on:
  schedule:
    - cron: "*/5 * * * *"
  workflow_dispatch: {}

permissions:
  contents: read

concurrency:
  group: mef-monitor-v2
  cancel-in-progress: true
jobs:
  monitor:
    runs-on: ubuntu-latest
    timeout-minutes: 3

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        timeout-minutes: 1

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt
        timeout-minutes: 1

      - name: Test Telegram (manual runs only)
        if: github.event_name == 'workflow_dispatch'
        env:
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: |
          python -u - <<'PY'
          import os
          import requests
          import sys

          token = os.getenv("TELEGRAM_TOKEN")
          chat_id = os.getenv("TELEGRAM_CHAT_ID")

          if not token or not chat_id:
              sys.exit("ERROR: Telegram secrets are missing.")

          url = f"https://api.telegram.org/bot{token}/sendMessage"

          try:
              response = requests.post(
                  url,
                  data={
                      "chat_id": chat_id,
                      "text": "✅ Test réussi : GitHub Actions peut envoyer des messages Telegram."
                  },
                  timeout=10,
              )
              print("Telegram HTTP status:", response.status_code)
              response.raise_for_status()

              result = response.json()
              if not result.get("ok"):
                  sys.exit("Telegram API rejected the message.")

              print("SUCCESS: Telegram test message sent.")
          except requests.RequestException as exc:
              sys.exit(f"Telegram test failed: {exc}")
          PY
        timeout-minutes: 1

      - name: Check official MEF page
        env:
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python -u monitor.py
        timeout-minutes: 1
