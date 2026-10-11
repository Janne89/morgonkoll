"""Styrräntan, kommande räntebesked och senaste penningpolitiska nyheterna från Riksbanken.

Räntan kommer från Riksbankens öppna API. Kommande besked läses från kalendersidan
(ingen API eller ics-länk finns), så den delen kan gå sönder om sidan byggs om.
"""
import html
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests

SERIE = "https://api.riksbank.se/swea/v1/Observations/SECBREPOEFF/{}/{}"
KALENDER = "https://www.riksbank.se/sv/press-och-publicerat/kalender/"
PRESS = "https://www.riksbank.se/sv/rss/pressmeddelanden/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Morgonkoll)"}
MANADER = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "maj": 5, "jun": 6,
           "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dec": 12}
PENNINGPOLITIK = re.compile(r"styrränt|penningpolitisk", re.I)
ANTAL_NYHETER = 3


def styrranta(idag):
    """Nuvarande styrränta och senaste ändringen (från vilken nivå, och från när)."""
    svar = requests.get(SERIE.format((idag - timedelta(days=4 * 365)).isoformat(), idag.isoformat()),
                        headers=HEADERS, timeout=30)
    svar.raise_for_status()
    serie = svar.json()
    nu = serie[-1]
    forra, andrad = None, None
    for foregaende, denna in zip(reversed(serie[:-1]), reversed(serie)):
        if foregaende["value"] != nu["value"]:
            forra, andrad = foregaende["value"], denna["date"]
            break
    return {"styrranta": nu["value"], "datum": nu["date"], "forra_styrranta": forra, "andrad": andrad}


def kommande_besked(idag):
    """Datum då kommande penningpolitiska beslut publiceras, enligt kalendersidan."""
    sida = requests.get(KALENDER, headers=HEADERS, timeout=30).text
    sida = re.sub(r"<script.*?</script>|<style.*?</style>", "", sida, flags=re.S)
    rader = [r.strip() for r in html.unescape(re.sub(r"<[^>]+>", "\n", sida)).split("\n") if r.strip()]
    besked = {}
    for i, rad in enumerate(rader):
        # Dag och "nov. 2026" står på raderna före rubriken.
        if not rad.startswith("Publicering av penningpolitiskt beslut") or i < 2:
            continue
        traff = re.match(r"(\w{3})\w*\.? (\d{4})$", rader[i - 1])
        if not (rader[i - 2].isdigit() and traff and traff.group(1).lower() in MANADER):
            continue
        dag = date(int(traff.group(2)), MANADER[traff.group(1).lower()], int(rader[i - 2]))
        if dag >= idag:
            besked[dag.isoformat()] = {"datum": dag.isoformat(), "rubrik": rad}
    return sorted(besked.values(), key=lambda b: b["datum"])


def nyheter():
    """De senaste pressmeddelandena om penningpolitiken."""
    svar = requests.get(PRESS, headers=HEADERS, timeout=30)
    svar.raise_for_status()
    lista = []
    for item in ET.fromstring(svar.content).iter("item"):
        rubrik = (item.findtext("title") or "").strip()
        if PENNINGPOLITIK.search(rubrik) and item.findtext("pubDate"):
            lista.append({
                "rubrik": rubrik,
                "lank": (item.findtext("link") or "").strip(),
                "publicerad": parsedate_to_datetime(item.findtext("pubDate")).astimezone(timezone.utc).isoformat(),
            })
    return sorted(lista, key=lambda n: n["publicerad"], reverse=True)[:ANTAL_NYHETER]


def hamta(idag=None):
    idag = idag or date.today()
    rad = {"id": "styrranta", **styrranta(idag), "hamtad": datetime.now(timezone.utc).isoformat()}
    # Kalender och pressmeddelanden är extra – ett fel där ska inte stoppa räntan.
    for falt, hamtare in (("kommande", lambda: kommande_besked(idag)), ("nyheter", nyheter)):
        try:
            rad[falt] = hamtare()
        except Exception as e:
            print(f"Riksbanken: kunde inte hämta {falt} ({e})", file=sys.stderr)
    return rad
