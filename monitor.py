
"""
MEF Final Results Monitor
Monitors the official emploi-public.ma page for final recruitment
results and sends a Telegram alert when a matching PDF is detected.
"""

import json
import os
import sys
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

CONCOURS_URL = (
    "https://www.emploi-public.ma/fr/concours/details/"
    "5b13aa42-f2db-4399-aa93-732e59d42ae8"
)
BASE_URL = "https://www.emploi-public.ma"
STATE_FILE = "state.json"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

# Keywords indicating final recruitment results.
FINAL_RESULTS_KEYWORDS = [
    "resultat du concours",
    "resultat definitif",
    "resultats finaux",
    "liste des candidats admis",
    "liste des candidats retenus",
    "liste definitive des candidats admis",
    "liste des candidats en attente",
    "liste d'attente",
    "liste d'attente definitive",
    "resultats du concours",
    "final results",
    "final list",
    "successful candidates",
    "النتائج النهائية",
    "لائحة الناجحين",
    "لائحة المقبولين",
]

# These terms should prevent an oral/exam-convocation alert.
EXCLUDED_KEYWORDS = [
    "entretien oral",
    "epreuve orale",
    "convoques a l'oral",
    "convoques pour l'oral",
    "candidats convoques",
    "liste des convoques",
    "epreuve ecrite",
    "convocation",
]

def normalize(text):
    """Normalize common French accents for keyword matching."""
    text = (text or "").lower()
    replacements = {
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "à": "a", "â": "a",
        "î": "i", "ï": "i",
        "ô": "o",
        "ù": "u", "û": "u",
        "ç": "c",
        "’": "'", "–": "-", "—": "-",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return " ".join(text.split())


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "seen_links": data.get("seen_links", [])
                }
        except (json.JSONDecodeError, OSError):
            print("Warning: state file unreadable; starting fresh.")

    return {"seen_links": []}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def fetch_page():
    response = requests.get(
        CONCOURS_URL, headers=HEADERS, timeout=30
    )
    response.raise_for_status()
    return response.text


def extract_download_links(html):
    soup = BeautifulSoup(html, "html.parser")
    links = []

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()

        if "/concours/download/" not in href:
            continue

        full_url = urljoin(BASE_URL, href)

        # Include surrounding text because the download button itself
        # may only say "Télécharger" or "Download".
        context_parts = [anchor.get_text(" ", strip=True)]

        parent = anchor.parent
        for _ in range(3):
            if parent is None:
                break
            context_parts.append(parent.get_text(" ", strip=True))
            parent = parent.parent

        context = normalize(" ".join(context_parts))

        links.append({
            "url": full_url,
            "label": anchor.get_text(" ", strip=True),
            "context": context,
        })

    # Remove duplicate URLs.
    unique = {}
    for link in links:
        unique[link["url"]] = link

    return list(unique.values())


def is_final_results_link(link):
    text = normalize(
        link["url"] + " " + link["label"] + " " + link["context"]
    )

    # Exclude oral/written exam convocations and other non-final notices.
    if any(keyword in text for keyword in EXCLUDED_KEYWORDS):
        return False

    return any(
        normalize(keyword) in text
        for keyword in FINAL_RESULTS_KEYWORDS
    )


def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(
            "Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID environment variables.",
            file=sys.stderr,
        )
        return False

    url = (
        "https://api.telegram.org/bot"
        f"{TELEGRAM_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_web_page_preview": False,
    }

    try:
        response = requests.post(url, data=payload, timeout=20)
        response.raise_for_status()

        result = response.json()
        if not result.get("ok"):
            print(f"Telegram API error: {result}", file=sys.stderr)
            return False

        return True

    except (requests.RequestException, ValueError) as exc:
        print(f"Telegram delivery failed: {exc}", file=sys.stderr)
        return False


def build_alert_message(link):
    return (
        "🚨 MEF ALERT — RÉSULTATS DÉFINITIFS\n\n"
        "Un document correspondant aux résultats du concours "
        "Administrateurs des Finances de 2ᵉ grade vient d’être détecté "
        "sur la page officielle.\n\n"
        f"📄 Document : {link['label'] or 'Résultats du concours'}\n"
        f"🔗 PDF : {link['url']}\n\n"
        "Vérifie le document pour confirmer qu’il s’agit bien "
        "des résultats définitifs."
    )


def main():
    state = load_state()
    seen_links = set(state.get("seen_links", []))

    try:
        html = fetch_page()
    except requests.RequestException as exc:
        print(f"Failed to fetch official page: {exc}", file=sys.stderr)
        sys.exit(1)

    links = extract_download_links(html)
    final_links = [link for link in links if is_final_results_link(link)]

    if not final_links:
        print("No matching final-results document detected.")
    else:
        for link in final_links:
            if link["url"] in seen_links:
                print(f"Already notified: {link['url']}")
                continue

            print(f"New potential final-results document: {link['url']}")

            # Only mark the link as seen after Telegram confirms delivery.
            if send_telegram_message(build_alert_message(link)):
                print("Telegram alert sent.")
                seen_links.add(link["url"])
            else:
                print("Alert not sent; will retry on the next run.")

    state["seen_links"] = sorted(seen_links)
    save_state(state)


if __name__ == "__main__":
    main()
