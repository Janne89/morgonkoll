"""Vad som trendar på Google i Sverige – samma lista som trends.google.se/trending.

Listan (senaste 24 timmarna, i Googles ordning) och en nyhetsartikel per trend
kommer från det interna API som sidan själv använder – inofficiellt och kan sluta
fungera. Då faller vi tillbaka på RSS-flödet, som bara innehåller de ~10 senast
startade trenderna.
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape

import requests

RSS = "https://trends.google.com/trending/rss?geo=SE"
INTERNT = "https://trends.google.com/_/TrendsUi/data/batchexecute"
NS = "{https://trends.google.com/trending/rss}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Morgonkoll)"}
ANTAL = 15
UTAN_NYHET = {"nyhet_rubrik": None, "nyhet_lank": None, "nyhet_kalla": None}


def trafiktext(tal):
    return f"{tal:,}+".replace(",", " ") if tal else None


def anropa(rpc, argument):
    frage = [[[rpc, json.dumps(argument), None, "generic"]]]
    svar = requests.post(INTERNT, data={"f.req": json.dumps(frage)}, headers=HEADERS, timeout=30)
    svar.raise_for_status()
    # Svaret börjar med )]}' och en tom rad; själva datan är JSON i en JSON-sträng.
    return json.loads(json.loads(svar.text.split("\n", 2)[2])[0][2])


def forsta_nyheten(nyhets_id):
    """Rubrik, länk och källa för den första artikeln om en trend."""
    if not nyhets_id:
        return UTAN_NYHET
    try:
        artiklar = (anropa("w4opAf", [nyhets_id, 1]) or [None])[0]
    except Exception as e:
        print(f"Google Trends: inga nyheter ({e})", file=sys.stderr)
        return UTAN_NYHET
    if not artiklar:
        return UTAN_NYHET
    rubrik, lank, kalla = artiklar[0][:3]
    return {"nyhet_rubrik": unescape(rubrik), "nyhet_lank": lank, "nyhet_kalla": kalla}


def internt():
    """De ANTAL första trenderna senaste 24 timmarna, i samma ordning som på trends.google.se."""
    # Argumenten: [?, ?, land, ?, språk, timmar bakåt, ?]
    lista = anropa("i0OFE", [None, None, "SE", 0, "sv", 24, 1])[1]
    trender = {}
    for t in lista:
        if len(trender) == ANTAL:
            break
        if t[0] in trender:
            continue
        trender[t[0]] = {
            "sokord": t[0],
            "trafik": trafiktext(t[6]),
            "trafik_tal": t[6] or 0,
            "relaterade": [r for r in (t[9] or []) if r != t[0]][:4],
            "publicerad": datetime.fromtimestamp(t[3][0], timezone.utc).isoformat(),
            **forsta_nyheten(t[11]),
        }
    return list(trender.values())


def falt(element, namn):
    if element is None:
        return None
    return unescape(element.findtext(NS + namn) or "").strip() or None


def rss():
    """Reserv: de ~10 senast startade trenderna, störst först."""
    svar = requests.get(RSS, headers=HEADERS, timeout=30)
    svar.raise_for_status()
    trender = {}
    for item in ET.fromstring(svar.content).iter("item"):
        sokord = (item.findtext("title") or "").strip()
        datum = item.findtext("pubDate")
        if not sokord or not datum:
            continue
        nyhet = item.find(NS + "news_item")      # första artikeln förklarar trenden bäst
        trafik = int(re.sub(r"\D", "", falt(item, "approx_traffic") or "") or 0)
        trender.setdefault(sokord, {
            "sokord": sokord,
            "trafik": trafiktext(trafik),
            "trafik_tal": trafik,
            "relaterade": [],
            "nyhet_rubrik": falt(nyhet, "news_item_title"),
            "nyhet_lank": falt(nyhet, "news_item_url"),
            "nyhet_kalla": falt(nyhet, "news_item_source"),
            "publicerad": parsedate_to_datetime(datum).astimezone(timezone.utc).isoformat(),
        })
    return sorted(trender.values(), key=lambda t: -t["trafik_tal"])


def hamta():
    try:
        lista = internt()
    except Exception as e:
        print(f"Google Trends internt API fungerade inte ({e}), använder RSS.", file=sys.stderr)
        lista = rss()
    hamtad = datetime.now(timezone.utc).isoformat()
    return [{**t, "plats": i, "hamtad": hamtad} for i, t in enumerate(lista, 1)]
