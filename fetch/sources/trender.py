"""Vad som trendar på Google i Sverige, med en förklarande nyhetsartikel per sökord."""
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape

import requests

URL = "https://trends.google.com/trending/rss?geo=SE"
NS = "{https://trends.google.com/trending/rss}"


def falt(element, namn):
    if element is None:
        return None
    return unescape(element.findtext(NS + namn) or "").strip() or None


def tolka(xml, hamtad):
    trender = {}
    for item in ET.fromstring(xml).iter("item"):
        sokord = (item.findtext("title") or "").strip()
        datum = item.findtext("pubDate")
        if not sokord or not datum:
            continue
        trafik = falt(item, "approx_traffic") or ""
        nyhet = item.find(NS + "news_item")      # första artikeln förklarar trenden bäst
        trender.setdefault(sokord, {                # samma sökord kan dyka upp två gånger
            "sokord": sokord,
            "trafik": trafik or None,
            # "1000+" → 1000, för att kunna sortera på sidan.
            "trafik_tal": int(re.sub(r"\D", "", trafik) or 0),
            "nyhet_rubrik": falt(nyhet, "news_item_title"),
            "nyhet_lank": falt(nyhet, "news_item_url"),
            "nyhet_kalla": falt(nyhet, "news_item_source"),
            "publicerad": parsedate_to_datetime(datum).astimezone(timezone.utc).isoformat(),
            "hamtad": hamtad,
        })
    return list(trender.values())


def hamta():
    svar = requests.get(URL, headers={"User-Agent": "Mozilla/5.0 (Morgonkoll)"}, timeout=30)
    svar.raise_for_status()
    return tolka(svar.content, datetime.now(timezone.utc).isoformat())
