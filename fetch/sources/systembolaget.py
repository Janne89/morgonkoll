"""Kommande släpp på Systembolaget (tillfälligt sortiment, webblanseringar m.m.).

Systembolaget har inget öppet API längre. Det här är samma sök-API som deras
webbplats använder – inofficiellt och kan sluta fungera. Nyckeln ligger öppet i
sidans JavaScript och letas upp där vid varje körning (så den inte ligger i repot).
"""
import re
from datetime import date, datetime, timedelta, timezone

import requests

SOK = "https://api-extern.systembolaget.se/sb-api-ecommerce/v1/productsearch/search"
WEBB = "https://www.systembolaget.se"
HEADERS = {"User-Agent": "Mozilla/5.0 (Morgonkoll)"}
DAGAR_FRAMAT = 28
# Ordervaror är beställningssortiment med "säljstart" nästan varje dag – inga släpp.
UTESLUTNA_SORTIMENT = {"BS"}


def hitta_nyckel():
    """Letar upp API-nyckeln i webbplatsens JavaScript."""
    sida = requests.get(WEBB + "/", headers=HEADERS, timeout=30).text
    for skript in dict.fromkeys(re.findall(r'/_next/static/[^"]+\.js', sida)):
        text = requests.get(WEBB + skript, headers=HEADERS, timeout=30).text
        traff = re.search(r'NEXT_PUBLIC_API_KEY_APIM:"([0-9a-f]{32})"', text)
        if traff:
            return traff.group(1)
    raise RuntimeError("Hittade ingen API-nyckel på systembolaget.se")


def sok(nyckel, fran, till):
    produkter, sida = [], 1
    while sida > 0:
        svar = requests.get(SOK, params={
            "size": 30, "page": sida,
            "productLaunch.min": fran.isoformat(), "productLaunch.max": till.isoformat(),
        }, headers={**HEADERS, "Ocp-Apim-Subscription-Key": nyckel}, timeout=30)
        svar.raise_for_status()
        data = svar.json()
        produkter += data["products"]
        sida = data["metadata"]["nextPage"]
    return produkter


def hamta(idag=None):
    fran = idag or date.today()
    till = fran + timedelta(days=DAGAR_FRAMAT)
    produkter = sok(hitta_nyckel(), fran, till)

    hamtad = datetime.now(timezone.utc).isoformat()
    return [{
        "artikelnummer": p["productNumber"],
        "namn": p["productNameBold"],
        "namn2": p.get("productNameThin"),
        "kategori": p.get("categoryLevel1"),
        "typ": p.get("categoryLevel2"),
        "land": p.get("country"),
        "pris": p.get("price"),
        "volym_ml": p.get("volume"),
        "sortiment": p["assortmentText"],
        # Lokal säljstart, t.ex. "2026-10-16T00:00:00". Släppen öppnar kl 10.
        "saljstart": p["productLaunchDate"][:10],
        "hamtad": hamtad,
    } for p in produkter if p.get("assortment") not in UTESLUTNA_SORTIMENT]
