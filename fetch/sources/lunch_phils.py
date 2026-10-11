"""Lunch på Phils (burgare).

Dagens burgare per veckodag står som text på phils.se/meny/ och hämtas automatiskt.
Resten av lunchmenyn finns bara som bild (länkad från samma sida), så de rätterna är
inskrivna för hand. Byts bilden (annat filnamn än LUNCHBILD) visas en varning.
"""
import re
from datetime import date
from html import unescape

import requests

RESTAURANG = "Phils"
SIDA = "https://www.phils.se/meny/"
LUNCHBILD = "a4-lunch-gron-maj26.jpg"   # bilden som rätterna nedan är inskrivna från
DAGAR = {"mån": "måndag", "tis": "tisdag", "ons": "onsdag", "tors": "torsdag", "fre": "fredag"}

# Lunchpris för burgare 150 g (200/300 g kostar mer), kyckling/halloumi/kronärtskocka enkel.
LUNCHMENY = [
    ("Phil's", "Nötkött, cheddarost, silverlök, krispsallad, Phil's dressing", 139),
    ("Guldburgaren", "Nötkött, cheddar- och emmentalerost, pickles, picklad rödlök, friterad lök, karamelliserad jalapeño, srirachamajo", 149),
    ("Tryffel", "Nötkött, cheddarost, picklad silverlök, pickles, karamelliserad lök, tryffelmajo", 145),
    ("Cheese", "Nötkött, dubbel cheddarost, pickles, silverlök, majonnäs, senap, ketchup", 139),
    ("BBQ Bacon", "Nötkött, bacon, cheddarost, pickles, picklad silverlök, karamelliserad lök, BBQ-sås", 139),
    ("Kyckling", "Friterad kyckling, cheddarost, picklad rödlök, pickles, krispsallad, green garlic dressing", 139),
    ("Halloumi", "Halloumi, wonton, avokadoröra, soltorkad tomat, picklad rödlök, krispsallad, srirachamajo", 139),
    ("Kronärtskocka", "Kronärtskocka, picklad rödlök, krispsallad, pickles, torkade tranbär, green garlic dressing (vegansk)", 139),
    ("Phil's sallad", "Kyckling eller halloumi, salladsmix, edamamebönor, wontonkrisp, tranbär, picklad rödkål, tomat, kikärtor", 155),
    ("Caesarsallad", "Kyckling eller halloumi, romansallad, caesardressing, krutonger, tomat, baconkrisp, parmesan", 155),
]


def burgare(namn):
    """"Guldburgare" på sidan → "Guldburgaren" i menyn."""
    nyckel = re.sub(r"\W", "", namn.lower())[:5]
    return next((r for r in LUNCHMENY if re.sub(r"\W", "", r[0].lower()).startswith(nyckel)), None)


def hamta():
    html = requests.get(SIDA, headers={"User-Agent": "Mozilla/5.0 (Morgonkoll)"}, timeout=30).text
    start = html.find("Lunch 11")
    avsnitt = html[start:start + 2000] if start >= 0 else ""
    # <strong>mån </strong>| Phil’s  <strong>tis </strong>| Guldburgare …
    dagens = []
    for dag, namn in re.findall(r"<strong>\s*(mån|tis|ons|tors|fre)\s*</strong>\s*\|\s*([^<]+?)\s*(?=<strong>|</p>)", avsnitt):
        namn = unescape(namn).replace("’", "'").strip()
        meny = burgare(namn)
        dagens.append({"namn": f"Dagens burgare: {meny[0] if meny else namn}", "beskrivning": meny[1] if meny else None,
                       "pris": None, "sektion": "veckans", "dag": DAGAR[dag]})
    villkor = re.search(r"Lunch serveras[^<]+", avsnitt)
    bild = re.search(r'href="(https?://[^"]+\.(?:jpe?g|png|pdf))"[^>]*>\s*SE LUNCHMENY', avsnitt)

    info = [unescape(villkor.group(0)).strip() if villkor else "Lunch vardagar 11–14, pommes/grönsallad, kaffe & coleslaw ingår"]
    if not bild or LUNCHBILD not in bild.group(1):
        info.insert(0, "Obs: lunchmenyn på phils.se har bytts – rätterna nedan kan vara inaktuella")
    if not dagens:
        info.insert(0, "Hittade inte dagens burgare på phils.se")
    return {
        "restaurang": RESTAURANG,
        "vecka": date.today().isocalendar()[1],
        "info": info,
        "ratter": dagens + [{"namn": n, "beskrivning": b, "pris": p, "sektion": "alltid", "dag": None} for n, b, p in LUNCHMENY],
        "kalla": bild.group(1).replace("http://", "https://") if bild else SIDA,
    }
