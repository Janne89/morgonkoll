"""Nyhetsrubriker från RSS- och Atom-flöden. Vi sparar bara rubrik, ingress och länk."""
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape

import requests

# (källa, url, ämne). Ämnet "ai" hamnar under egen flik på sidan, inte under "Alla".
FLODEN = [
    ("SVT", "https://www.svt.se/nyheter/inrikes/rss.xml", "nyheter"),
    ("SVT", "https://www.svt.se/nyheter/utrikes/rss.xml", "nyheter"),
    ("Di", "https://www.di.se/rss", "nyheter"),
    ("OpenAI", "https://openai.com/news/rss.xml", "ai"),
    # Anthropic har inget eget flöde – det här skrapas av ett community-projekt på GitHub.
    ("Anthropic", "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml", "ai"),
    ("Google", "https://blog.google/technology/ai/rss/", "ai"),
    ("Google", "https://deepmind.google/blog/rss.xml", "ai"),
    ("TechCrunch", "https://techcrunch.com/category/artificial-intelligence/feed/", "ai"),
    ("The Verge", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "ai"),
]
PER_FLODE = 15
ATOM = "{http://www.w3.org/2005/Atom}"


def rensa(text):
    text = re.sub(r"<[^>]+>", " ", unescape(text or ""))
    return re.sub(r"\s+", " ", text).strip() or None


def rss(rot, kalla):
    for item in rot.iter("item"):
        # OpenAI:s kundcase saknar kategori – de hoppar vi över.
        if kalla == "OpenAI" and not item.findtext("category"):
            continue
        datum = item.findtext("pubDate")
        yield (item.findtext("link"), item.findtext("title"), item.findtext("description"),
               datum and parsedate_to_datetime(datum))


def atom(rot):
    for entry in rot.iter(ATOM + "entry"):
        lankar = entry.findall(ATOM + "link")
        lank = next((l.get("href") for l in lankar if l.get("rel", "alternate") == "alternate"), None)
        datum = entry.findtext(ATOM + "published") or entry.findtext(ATOM + "updated")
        yield (lank, entry.findtext(ATOM + "title"), entry.findtext(ATOM + "summary"),
               datum and datetime.fromisoformat(datum))


def tolka(kalla, amne, xml):
    rot = ET.fromstring(xml)
    artiklar = []
    for lank, rubrik, ingress, datum in (atom(rot) if rot.tag == ATOM + "feed" else rss(rot, kalla)):
        lank, rubrik, ingress = (lank or "").strip(), rensa(rubrik), rensa(ingress)
        if not lank or not rubrik or not datum:
            continue
        artiklar.append({
            "kalla": kalla,
            "amne": amne,
            "rubrik": rubrik,
            "ingress": ingress if ingress != rubrik else None,
            "lank": lank,
            "publicerad": datum.astimezone(timezone.utc).isoformat(),
        })
    artiklar.sort(key=lambda a: a["publicerad"], reverse=True)
    return artiklar[:PER_FLODE]


def hamta():
    headers = {"User-Agent": "Mozilla/5.0 (Morgonkoll)"}
    artiklar = {}
    # Sätts på alla rader varje gång, så att sidan kan visa när vi senast hämtade.
    hamtad = datetime.now(timezone.utc).isoformat()
    for kalla, url, amne in FLODEN:
        svar = requests.get(url, headers=headers, timeout=30)
        svar.raise_for_status()
        for a in tolka(kalla, amne, svar.content):
            artiklar[a["lank"]] = {**a, "hamtad": hamtad}     # samma artikel kan ligga i flera flöden
    return list(artiklar.values())
