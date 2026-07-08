import os
import json
import requests
from bs4 import BeautifulSoup

URLS = [
    "https://e-recrutement.finances.gov.ma/index.aspx?ReturnUrl=%2f",
    "https://www.emploi-public.ma/fr/concours/details/5b13aa42-f2db-4399-aa93-732e59d42ae8"
]

STATE_FILE = "state.json"

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


def send(msg):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": msg
        }
    )


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


state = load_state()

for url in URLS:

   try:
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    r = requests.get(
        url,
        headers=headers,
        timeout=20
    )

    r.raise_for_status()

except Exception as e:
    print(f"Could not access {url}: {e}")
    continue

soup = BeautifulSoup(r.text, "html.parser")

    text = soup.get_text(" ", strip=True).lower()

    trigger = (
        "épreuve orale" in text
        or "entretien oral" in text
        or "convocation pour l'entretien oral" in text
    )

    previous = state.get(url, False)

    if trigger and not previous:
        send(
            f"🚨 MEF UPDATE DETECTED!\n\nSomething related to the oral examination appeared.\n\n{url}"
        )

    state[url] = trigger

save_state(state)
