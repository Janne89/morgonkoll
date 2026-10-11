"""SHL-matcher (igår till en vecka framåt) från shl.se:s eget API.

Inofficiellt – samma API som shl.se använder. Det tillåter inte anrop från
webbläsaren (CORS), därför hämtas det här och sparas i Supabase.
"""
from datetime import date, datetime, timedelta, timezone

import requests

BAS = "https://www.shl.se/api/sports-v2"
HEADERS = {"User-Agent": "Mozilla/5.0 (Morgonkoll)"}
DAGAR_BAKAT, DAGAR_FRAMAT = 1, 7


def hamta(idag=None):
    idag = idag or date.today()
    # Aktuell säsong, serie (SHL) och matchtyp – samma förval som shl.se.
    filt = requests.get(f"{BAS}/season-series-game-types-filter", headers=HEADERS, timeout=30)
    filt.raise_for_status()
    forval = filt.json()["defaultSsgtFilter"]
    svar = requests.get(f"{BAS}/game-schedule", params={
        "seasonUuid": forval["season"], "seriesUuid": forval["series"], "gameTypeUuid": forval["gameType"],
        "gamePlace": "all", "played": "all",
    }, headers=HEADERS, timeout=30)
    svar.raise_for_status()

    fran = (idag - timedelta(days=DAGAR_BAKAT)).isoformat()
    till = (idag + timedelta(days=DAGAR_FRAMAT)).isoformat()
    hamtad = datetime.now(timezone.utc).isoformat()
    rader = []
    for m in svar.json()["gameInfo"]:
        # startDateTime är svensk tid ("2026-10-10 18:00:00"), rawStartDateTime UTC.
        if not fran <= m["startDateTime"][:10] <= till:
            continue
        hemma, borta = m["homeTeamInfo"], m["awayTeamInfo"]
        mal = lambda lag: lag.get("score") if isinstance(lag.get("score"), int) else None
        rader.append({
            "uuid": m["uuid"],
            "start": m["rawStartDateTime"],
            "status": m["state"],                  # pre-game, live, post-game …
            "hemma": hemma["names"]["short"].strip(),
            "borta": borta["names"]["short"].strip(),
            "hemma_mal": mal(hemma),
            "borta_mal": mal(borta),
            "overtime": bool(m.get("overtime")),
            "straffar": bool(m.get("shootout")),
            "hamtad": hamtad,
        })
    return rader
