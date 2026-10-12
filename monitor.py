import json
import os
import sys
import unicodedata
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

# Intitules possibles des resultats definitifs.
FINAL_KEYWORDS = [
    "resultats definitifs",
    "resultat definitif",
    "resultats finaux",
    "liste des candidats admis",
    "liste des candidats retenus",
    "liste definitive des candidats admis",
    "liste principale des candidats admis",
    "liste d'attente",
    "resultats du concours",
    "final results",
    "final list",
    "successful candidates",
    "النتائج النهائية",
    "لائحة الناجحين",
    "لائحة المقبولين",
]

# Termes indiquant une convocation ou une etape anterieure.
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
    """Supprime les accents et normalise le texte."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.lower().replace("’", "'").split())

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {"seen_links": data.get("seen_links", [])}
        except (json.JSONDecodeError, OSError):
            print("Etat illisible : initialisation d'un nouvel etat.")

    return {"seen_links": []}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def fetch_page():
    response = requests.get(
        CONCOURS_URL,
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    return response.text

def extract_download_links(html):
    soup = BeautifulSoup(html, "html.parser")
    links = {}

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()

        if "/concours/download/" not in href:
            continue

        full_url = urljoin(BASE_URL, href)

        context_parts = [anchor.get_text(" ", strip=True)]
        parent = anchor.parent

        for _ in range(3):
            if parent is None:
                break
            context_parts.append(parent.get_text(" ", strip=True))
            parent = parent.parent

        links[full_url] = {
            "url": full_url,
            "label": anchor.get_text(" ", strip=True),
            "context": " ".join(context_parts),
        }

    return list(links.values())

def is_final_results_link(link):
    text = normalize(
        link["url"] + " " + link["label"] + " " + link["context"]
    )

    if any(normalize(word) in text for word in EXCLUDED_KEYWORDS):
        return False

    return any(normalize(word) in text for word in FINAL_KEYWORDS)

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(
            "ERREUR : TELEGRAM_TOKEN ou TELEGRAM_CHAT_ID manquant.",
            file=sys.stderr,
        )
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    try:
        response = requests.post(
            url,
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "disable_web_page_preview": False,
            },
            timeout=20,
        )
        response.raise_for_status()

        result = response.json()
        if not result.get("ok"):
            print(f"Erreur Telegram : {result}", file=sys.stderr)
            return False

        return True

    except (requests.RequestException, ValueError) as exc:
        print(f"Echec de l'envoi Telegram : {exc}", file=sys.stderr)
        return False

def build_alert_message(link):
    title = link["label"] or "Resultats du concours"

    return (
        "🚨 ALERTE MEF — RÉSULTATS DU CONCOURS\n\n"
        "Un document susceptible de contenir les résultats définitifs "
        "du concours des Administrateurs des Finances de 2e grade "
        "a été détecté sur le site officiel.\n\n"
        f"📄 Document : {title}\n"
        f"🔗 Lien : {link['url']}\n\n"
        "Ouvre le document pour confirmer qu'il s'agit bien "
        "des résultats définitifs."
    )

def main():
    state = load_state()
    seen_links = set(state.get("seen_links", []))

    try:
        html = fetch_page()
    except requests.RequestException as exc:
        print(f"Erreur de consultation de la page : {exc}", file=sys.stderr)
        sys.exit(1)

    links = extract_download_links(html)
    matching_links = [
        link for link in links if is_final_results_link(link)
    ]

    if not matching_links:
        print("Aucun document correspondant aux resultats detecte.")
        return

    for link in matching_links:
        if link["url"] in seen_links:
            print(f"Document deja signale : {link['url']}")
            continue

        print(f"Nouveau document potentiel : {link['url']}")

        if send_telegram_message(build_alert_message(link)):
            seen_links.add(link["url"])
            state["seen_links"] = sorted(seen_links)
            save_state(state)
            print("Alerte Telegram envoyee.")
        else:
            print("Envoi echoue : nouvelle tentative a la prochaine execution.")

    state["seen_links"] = sorted(seen_links)
    save_state(state)

if __name__ == "__main__":
    main()
