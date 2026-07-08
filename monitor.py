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
