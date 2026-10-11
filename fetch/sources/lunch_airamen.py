"""Lunch på Ai Ramen Kita.

Menyn finns bara som bild på airamen.se/menu-kita, så rätterna är inskrivna här för hand.
Vid varje hämtning kontrolleras att menybilden är densamma – har den bytts visas en
varning i kortet tills rätterna nedan har uppdaterats (och MENYBILD ändrats).
"""
import re
from datetime import date

import requests

RESTAURANG = "Ai Ramen Kita"
SIDA = "https://www.airamen.se/menu-kita"
MENYBILD = "KITA+Meny+FINAL.png"      # filnamnet på bilden som rätterna är inskrivna från

RATTER = [
    ("Sthlm Shoyu", "Kyckling- och fläskbuljong, shoyu – pork belly, menma, salladslök, marinerat ägg", 155),
    ("Red Hot", "Kyckling- och fläskbuljong, het miso – pork belly, silverlök, pak choy, salladslök, marinerat ägg", 155),
    ("Tori Tantan", "Kombubuljong, sesam – kyckling, pak choy, salladslök, koriander, chili, marinerat ägg", 155),
    ("Bebikón", "Kombubuljong, miso – smörstekt majs, brysselkål, tofu, salladslök, marinerat ägg (vegetarisk)", 155),
    ("Donburi Chicken", "Ris, friterad het kyckling, kimchi, gurka, böngroddar, salladslök, majonnäs, ägg", 160),
    ("Donburi Tofu", "Ris, friterad het tofu, kimchi, gurka, böngroddar, salladslök, majonnäs, ägg", 160),
    ("Spicy Pulled Pork", "Ris, het pulled pork, kimchi, grönsallad, silverlök, nori, majonnäs, friterad vitlök", 145),
]


def hamta():
    html = requests.get(SIDA, headers={"User-Agent": "Mozilla/5.0 (Morgonkoll)"}, timeout=30).text
    bild = re.search(r'https://images\.squarespace-cdn\.com/[^"\s]+?\.(?:png|jpe?g|webp)', html)
    info = ["Alla ramen serveras med hemgjorda vetenudlar"]
    if not bild or MENYBILD not in bild.group(0):
        info.insert(0, "Obs: menybilden på airamen.se har bytts – rätterna nedan kan vara inaktuella")
    return {
        "restaurang": RESTAURANG,
        "vecka": date.today().isocalendar()[1],
        "info": info,
        "ratter": [{"namn": n, "beskrivning": b, "pris": p, "sektion": "alltid", "dag": None} for n, b, p in RATTER],
        "kalla": bild.group(0) if bild else SIDA,
    }
