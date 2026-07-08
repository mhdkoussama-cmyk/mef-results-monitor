import hashlib
import os
import requests
from bs4 import BeautifulSoup

URL = "https://www.emploi-public.ma/fr/concours/details/5b13aa42-f2db-4399-aa93-732e59d42ae8"

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(URL, headers=HEADERS, timeout=20)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

text = soup.get_text(" ", strip=True)

fingerprint = hashlib.sha256(text.encode()).hexdigest()

old = ""

if os.path.exists("fingerprint.txt"):
    with open("fingerprint.txt") as f:
        old = f.read().strip()

if old != "" and old != fingerprint:

    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": f"🚨 The Emploi Public page changed!\n\n{URL}"
        }
    )

with open("fingerprint.txt","w") as f:
    f.write(fingerprint)

print("Finished successfully.")
