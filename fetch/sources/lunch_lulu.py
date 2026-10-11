"""Lunchmenyn på Restaurang Lulu (samma lunchmeny på alla Lulu, bl.a. Gärdet).

Menyn är fast (inte veckomeny) och ligger som text på restauranglulu.se/lunch/,
byggd med Elementor: rubriker (h5, ibland h3) är rätter, textstycken beskrivningar.
"""
import re
from datetime import date
from html import unescape

import requests

RESTAURANG = "Lulu"
SIDA = "https://restauranglulu.se/lunch/"
SLUT = "Nibbles & Extra"         # tillbehören efter detta tas inte med
WIDGET = re.compile(r'data-widget_type="([a-z-]+)\.default".*?<div class="elementor-widget-container">(.*?)</div>\s*</div>', re.S)


def text(inner):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", inner))).replace("​", "").strip()


def snyggt(namn):
    """"SUSHI MORrIWASe" → "Sushi Morriwase"; namn med blandade versaler lämnas."""
    return namn.capitalize() if sum(c.isupper() for c in namn) > len(namn) / 2 or re.search(r"[a-z][A-Z]", namn) else namn


def tolka(html):
    # Rubriken "Lunch 155kr" anger priset för allt som inte har eget pris.
    rubrik = re.search(r"Lunch\s*(\d+)\s*kr", html, re.I)
    baspris = int(rubrik.group(1)) if rubrik else None
    start = rubrik.start() if rubrik else 0
    element = []
    for m in WIDGET.finditer(html[start:]):
        typ, inner = m.groups()
        tagg = re.search(r"<(h\d|p)\b", inner)
        element.append((typ, tagg.group(1) if tagg else "", text(inner)))

    info, ratter = [], []
    for i, (typ, tagg, t) in enumerate(element):
        if t == SLUT:
            break
        foreg = element[i - 1] if i else ("", "", "")
        nasta = element[i + 1] if i + 1 < len(element) else ("", "", "")
        if not t:
            continue
        if typ == "heading" and not tagg and not ratter and not re.search(r"\d+\s*kr", t, re.I):
            info.append(t.capitalize())                         # "INK. dryck, lulu miso …", öppettider
        elif tagg == "h3" and nasta[1] == "h5" and re.match(r"\d", nasta[2]):
            ratter.append({"namn": snyggt(t), "beskrivning": nasta[2], "pris": baspris})   # SUSHI MORRIWASE + "11 bitar"
        elif tagg == "h5" and not (foreg[1] == "h3" and re.match(r"\d", t)):
            ratter.append({"namn": snyggt(t), "beskrivning": None, "pris": baspris})
        elif typ == "text-editor" and ratter and not ratter[-1]["beskrivning"]:
            ratter[-1]["beskrivning"] = t
        elif typ == "heading" and ratter and re.fullmatch(r"(\d+)\s*(:-|kr)", t):
            ratter[-1]["pris"] = int(re.match(r"\d+", t).group())  # avvikande pris, t.ex. "169:-"
    return info, ratter


def hamta():
    html = requests.get(SIDA, headers={"User-Agent": "Mozilla/5.0 (Morgonkoll)"}, timeout=30).text
    info, ratter = tolka(html)
    if len(ratter) < 3:
        raise RuntimeError(f"Lulu: hittade bara {len(ratter)} rätter – har sidan ändrats?")
    return {
        "restaurang": RESTAURANG,
        "vecka": date.today().isocalendar()[1],
        "info": info,
        "ratter": [{**r, "sektion": "alltid", "dag": None} for r in ratter],
        "kalla": SIDA,
    }
