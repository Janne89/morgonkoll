"""Vad som trendar på Google – i Sverige (samma lista som trends.google.se/trending), USA, Europa och Asien.

Listan (senaste 24 timmarna, i Googles ordning) och en nyhetsartikel per trend
kommer från det interna API som sidan själv använder – inofficiellt och kan sluta
fungera. Då faller vi tillbaka på RSS-flödet, som bara innehåller de ~10 senast
startade trenderna.

Google Trends finns bara per land. Europa och Asien är därför flera länder ihopslagna
(störst sökvolym först). Asien är engelskspråkiga länder – japanska och koreanska
trender och nyheter går inte att läsa.
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape

import requests

RSS = "https://trends.google.com/trending/rss?geo={}"
INTERNT = "https://trends.google.com/_/TrendsUi/data/batchexecute"
NS = "{https://trends.google.com/trending/rss}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Morgonkoll)"}
# Region → [(land, språk)]
REGIONER = {
    "SE": [("SE", "sv")],
    "US": [("US", "en")],
    "EU": [("GB", "en"), ("DE", "de"), ("FR", "fr"), ("ES", "es"), ("IT", "it")],
    "AS": [("IN", "en"), ("SG", "en"), ("PH", "en")],
}
ANTAL = {"SE": 15}          # övriga regioner: ANTAL_ANNARS
ANTAL_ANNARS = 10
PER_LAND = 6                # i regioner med flera länder
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


def internt(land, sprak, antal):
    """De första trenderna senaste 24 timmarna i ett land, i samma ordning som på trends.google.com.
    Nyhetsartikeln hämtas inte här (_nyhet är id:t), så att den bara hämtas för dem som visas."""
    # Argumenten: [?, ?, land, ?, språk, timmar bakåt, ?]
    lista = anropa("i0OFE", [None, None, land, 0, sprak, 24, 1])[1]
    trender = {}
    for t in lista:
        if len(trender) == antal:
            break
        if t[0] in trender:
            continue
        trender[t[0]] = {
            "sokord": t[0],
            "land": land,
            "trafik": trafiktext(t[6]),
            "trafik_tal": t[6] or 0,
            "relaterade": [r for r in (t[9] or []) if r != t[0]][:4],
            "publicerad": datetime.fromtimestamp(t[3][0], timezone.utc).isoformat(),
            "_nyhet": t[11],
        }
    return list(trender.values())


def falt(element, namn):
    if element is None:
        return None
    return unescape(element.findtext(NS + namn) or "").strip() or None


def rss(land):
    """Reserv: de ~10 senast startade trenderna, störst först."""
    svar = requests.get(RSS.format(land), headers=HEADERS, timeout=30)
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
            "land": land,
            "trafik": trafiktext(trafik),
            "trafik_tal": trafik,
            "relaterade": [],
            "nyhet_rubrik": falt(nyhet, "news_item_title"),
            "nyhet_lank": falt(nyhet, "news_item_url"),
            "nyhet_kalla": falt(nyhet, "news_item_source"),
            "publicerad": parsedate_to_datetime(datum).astimezone(timezone.utc).isoformat(),
        })
    return sorted(trender.values(), key=lambda t: -t["trafik_tal"])


def landets(land, sprak, antal):
    try:
        return internt(land, sprak, antal)
    except Exception as e:
        print(f"Google Trends {land}: internt API fungerade inte ({e}), använder RSS.", file=sys.stderr)
        return rss(land)[:antal]


def nyckel(sokord):
    """"Real Madrid – Villarreal" och "real madrid vs villarreal" ska räknas som samma."""
    return re.sub(r"\b(vs|v)\b|\W", "", sokord.lower())


def region(kod):
    lander, antal = REGIONER[kod], ANTAL.get(kod, ANTAL_ANNARS)
    if len(lander) == 1:
        lista = landets(*lander[0], antal)
    else:
        unika = {}
        for land, sprak in lander:
            for t in landets(land, sprak, PER_LAND):
                k = nyckel(t["sokord"])
                if k not in unika or t["trafik_tal"] > unika[k]["trafik_tal"]:
                    unika[k] = t
        lista = sorted(unika.values(), key=lambda t: -t["trafik_tal"])[:antal]
    for t in lista:
        nyhets_id = t.pop("_nyhet", None)
        if nyhets_id is not None:
            t.update(forsta_nyheten(nyhets_id))
    hamtad = datetime.now(timezone.utc).isoformat()
    return [{**t, "region": kod, "plats": i, "hamtad": hamtad} for i, t in enumerate(lista, 1)]


def hamta():
    """{region: rader}; en region som inte går att hämta saknas och felet följer med."""
    resultat, fel = {}, []
    for kod in REGIONER:
        try:
            resultat[kod] = region(kod)
        except Exception as e:
            fel.append(f"{kod}: {e}")
    return resultat, fel
