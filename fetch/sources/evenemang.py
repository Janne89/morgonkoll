"""Evenemang i Stockholm från Visit Stockholms öppna API (CC BY 4.0, Stockholm Business Region).

Två delar:
- Stora evenemang med förväntat antal besökare (forecast-events) – konserter på arenorna m.m.
- Kortare evenemang (högst DAGAR_MAX dagar långa) den närmaste veckan. Långa utställningar
  och liknande sorteras bort, annars drunknar resten.
"""
from datetime import date, datetime, timedelta, timezone

import requests

BAS = "https://api.visitstockholm.com/api/v1"
HEADERS = {"User-Agent": "Mozilla/5.0 (Morgonkoll)"}
DAGAR_FRAMAT = 7
DAGAR_MAX = 3
STORA_DAGAR_FRAMAT = 60
MAX_SIDOR = 40          # 16 per sida


def stora(idag, hamtad):
    svar = requests.get(f"{BAS}/forecast-events/", headers=HEADERS, timeout=30)
    svar.raise_for_status()
    till = (idag + timedelta(days=STORA_DAGAR_FRAMAT)).isoformat()
    return [{
        "id": f"stort-{e['external_id']}",
        "titel": e["title"].strip(),
        "start": e["start_date"],
        "slut": e.get("end_date") or e["start_date"],
        "plats": e.get("location"),
        "kategori": None,
        "lank": e.get("more_info_url"),
        "besokare": e.get("expected_attendees"),
        "stort": True,
        "hamtad": hamtad,
    } for e in svar.json()
        if (e.get("end_date") or e["start_date"]) >= idag.isoformat() and e["start_date"] <= till]


def korta(idag, hamtad):
    rader, sida = {}, 1
    while sida and sida <= MAX_SIDOR:
        svar = requests.get(f"{BAS}/singulareventdates/", params={
            "date_from": idag.isoformat(), "date_to": (idag + timedelta(days=DAGAR_FRAMAT)).isoformat(), "page": sida,
        }, headers=HEADERS, timeout=30)
        svar.raise_for_status()
        data = svar.json()
        for e in data["results"]:
            start, slut = date.fromisoformat(e["start_date"]), date.fromisoformat(e["end_date"])
            if (slut - start).days >= DAGAR_MAX:
                continue
            rader[f"vs-{e['id']}"] = {
                "id": f"vs-{e['id']}",
                "titel": e["title"].strip(),
                "start": e["start_date"],
                "slut": e["end_date"],
                "plats": e.get("venue_name") or e.get("address"),
                "kategori": (e.get("category") or {}).get("title"),
                "lank": e.get("external_website_url") or None,
                "besokare": None,
                "stort": False,
                "hamtad": hamtad,
            }
        sida = data.get("next")
    return list(rader.values())


def hamta(idag=None):
    idag = idag or date.today()
    hamtad = datetime.now(timezone.utc).isoformat()
    return stora(idag, hamtad) + korta(idag, hamtad)
