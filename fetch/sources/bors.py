"""Börsindex från Yahoo Finance och växelkurser från Riksbanken.

Yahoos chart-API är inofficiellt och kan sluta fungera. Därför hämtas varje
instrument för sig, så att ett fel inte stoppar resten.
"""
from datetime import date, datetime, timedelta, timezone

import requests

INDEX = [
    ("^OMX", "OMXS30"),
    ("^GSPC", "S&P 500"),
    ("^IXIC", "Nasdaq"),
    ("^GDAXI", "DAX"),
]
VALUTOR = [
    ("SEKUSDPMI", "USD/SEK"),
    ("SEKEURPMI", "EUR/SEK"),
]
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{}"
RIKSBANKEN = "https://api.riksbank.se/swea/v1/Observations/{}/{}/{}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Morgonkoll)"}


def instrument(symbol, namn, typ, historik, kalla):
    """historik: [(datum, värde), ...] i tidsordning, minst två punkter."""
    (_, forra), (datum, varde) = historik[-2], historik[-1]
    return {
        "symbol": symbol,
        "namn": namn,
        "typ": typ,
        "varde": round(varde, 4),
        "forandring_pct": round((varde / forra - 1) * 100, 2),
        "datum": datum,
        "historik": [[d, round(v, 4)] for d, v in historik],
        "kalla": kalla,
        "hamtad": datetime.now(timezone.utc).isoformat(),
    }


def yahoo(symbol, namn):
    svar = requests.get(YAHOO.format(symbol), params={"range": "1mo", "interval": "1d"},
                        headers=HEADERS, timeout=30)
    svar.raise_for_status()
    resultat = svar.json()["chart"]["result"][0]
    stangningar = resultat["indicators"]["quote"][0]["close"]
    historik = [
        (datetime.fromtimestamp(t, timezone.utc).date().isoformat(), v)
        for t, v in zip(resultat["timestamp"], stangningar) if v is not None
    ]
    # Sista punkten är dagens kurs om börsen är öppen, annars senaste stängning.
    return instrument(symbol, namn, "index", historik, "Yahoo Finance")


def riksbanken(serie, namn):
    idag = date.today()
    url = RIKSBANKEN.format(serie, (idag - timedelta(days=45)).isoformat(), idag.isoformat())
    svar = requests.get(url, headers=HEADERS, timeout=30)
    svar.raise_for_status()
    historik = [(o["date"], o["value"]) for o in svar.json()]
    return instrument(serie, namn, "valuta", historik, "Riksbanken")


def hamta():
    """Returnerar (instrument, fel)."""
    resultat, fel = [], []
    for hamtare, lista in ((yahoo, INDEX), (riksbanken, VALUTOR)):
        for symbol, namn in lista:
            try:
                resultat.append(hamtare(symbol, namn))
            except Exception as e:
                fel.append(f"{namn}: {e!r}")
    return resultat, fel
