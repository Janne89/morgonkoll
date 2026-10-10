"""Nyhetsrubriker från RSS-flöden. Vi sparar bara rubrik, ingress och länk."""
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape

import requests

FLODEN = [
    ("SVT", "https://www.svt.se/nyheter/inrikes/rss.xml"),
    ("SVT", "https://www.svt.se/nyheter/utrikes/rss.xml"),
    ("Di", "https://www.di.se/rss"),
]
PER_FLODE = 15


def rensa(text):
    text = re.sub(r"<[^>]+>", " ", unescape(text or ""))
    return re.sub(r"\s+", " ", text).strip() or None


def tolka(kalla, xml):
    artiklar = []
    for item in ET.fromstring(xml).iter("item"):
        lank = (item.findtext("link") or "").strip()
        rubrik = rensa(item.findtext("title"))
        datum = item.findtext("pubDate")
        if not lank or not rubrik or not datum:
            continue
        artiklar.append({
            "kalla": kalla,
            "rubrik": rubrik,
            "ingress": rensa(item.findtext("description")),
            "lank": lank,
            "publicerad": parsedate_to_datetime(datum).astimezone(timezone.utc).isoformat(),
        })
    artiklar.sort(key=lambda a: a["publicerad"], reverse=True)
    return artiklar[:PER_FLODE]


def hamta():
    headers = {"User-Agent": "Mozilla/5.0 (Morgonkoll)"}
    artiklar = {}
    # Sätts på alla rader varje gång, så att sidan kan visa när vi senast hämtade.
    hamtad = datetime.now(timezone.utc).isoformat()
    for kalla, url in FLODEN:
        svar = requests.get(url, headers=headers, timeout=30)
        svar.raise_for_status()
        for a in tolka(kalla, svar.content):
            artiklar[a["lank"]] = {**a, "hamtad": hamtad}     # samma artikel kan ligga i flera flöden
    return list(artiklar.values())
