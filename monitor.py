#!/usr/bin/env python3
"""
MEF Oral List Monitor
Watches the emploi-public.ma concours page for the publication of the
"Liste des candidats convoques a l'entretien oral" PDF and sends a
Telegram alert the moment a new download link appears.
"""

import json
import os
import sys
import requests
from bs4 import BeautifulSoup

CONCOURS_URL = "https://www.emploi-public.ma/fr/concours/details/5b13aa42-f2db-4399-aa93-732e59d42ae8"
BASE_URL = "https://www.emploi-public.ma"
STATE_FILE = "state.json"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

ORAL_KEYWORDS = [
    "entretien oral",
    "epreuve orale",
    "convoques_oral",
    "list_convoques_oral",
    "oral",
]


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {"seen_links": []}
    return {"seen_links": []}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def fetch_page():
    resp = requests.get(CONCOURS_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def extract_download_links(html):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/concours/download/" in href:
            full_url = href if href.startswith("http") else BASE_URL + href
            label = a.get_text(strip=True)
            links.append({"url": full_url, "label": label})
    return links


def is_oral_link(link):
    haystack = (link["url"] + " " + link["label"]).lower()
    return any(kw in haystack for kw in ORAL_KEYWORDS)


def send_telegram_message(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID env vars.", file=sys.stderr)
        return
    url = "https://api.telegram.org/bot{}/sendMessage".format(TELEGRAM_TOKEN)
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    r = requests.post(url, data=payload, timeout=20)
    if r.status_code != 200:
        print("Telegram error: {} {}".format(r.status_code, r.text), file=sys.stderr)


def build_alert_message(link):
    return (
        "\U0001F6A8 <b>MEF ALERT</b>\n\n"
        "La liste des candidats convoques a l'entretien oral pour le concours "
        "<b>Administrateurs des Finances de 2eme grade</b> vient d'etre publiee.\n\n"
        "\U0001F4C4 PDF direct : {}".format(link["url"])
    )


def main():
    state = load_state()
    seen_links = set(state.get("seen_links", []))

    try:
        html = fetch_page()
    except requests.exceptions.RequestException as exc:
        print("Failed to fetch page: {}".format(exc), file=sys.stderr)
        sys.exit(0)

    links = extract_download_links(html)
    current_links = {l["url"] for l in links}
    new_links = [l for l in links if l["url"] not in seen_links]

    if new_links:
        print("Found {} new document link(s).".format(len(new_links)))
        for link in new_links:
            print(" - {} -> {}".format(link["label"], link["url"]))
            if is_oral_link(link):
                send_telegram_message(build_alert_message(link))
                print("Telegram alert sent for oral exam list.")
    else:
        print("No new links detected.")

    state["seen_links"] = list(current_links | seen_links)
    save_state(state)


if __name__ == "__main__":
    main()
