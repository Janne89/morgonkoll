"""Skriver till Supabase via PostgREST med den hemliga nyckeln.

Kräver miljövariablerna SUPABASE_URL och SUPABASE_SECRET_KEY.
"""
import os
from datetime import datetime, timedelta, timezone

import requests

DAGAR_KVAR = 7


class Databas:
    def __init__(self, url, nyckel):
        self.bas = url.rstrip("/") + "/rest/v1/"
        self.session = requests.Session()
        # Nya sb_secret-nycklar skickas bara som apikey (inte som Bearer-JWT).
        self.session.headers.update({
            "apikey": nyckel,
            "Content-Type": "application/json",
        })

    @classmethod
    def fran_miljo(cls):
        url = os.environ.get("SUPABASE_URL")
        nyckel = os.environ.get("SUPABASE_SECRET_KEY")
        if not url or not nyckel:
            return None
        return cls(url, nyckel)

    def _anrop(self, metod, tabell, **kw):
        svar = self.session.request(metod, self.bas + tabell, timeout=30, **kw)
        if not svar.ok:
            raise RuntimeError(f"{metod} {tabell}: {svar.status_code} {svar.text}")
        return svar

    def ersatt_lunch(self, meny, ar):
        """Byter ut restaurangens rader för veckan mot de nyss hämtade."""
        filter = {
            "restaurang": f"eq.{meny['restaurang']}",
            "ar": f"eq.{ar}",
            "vecka": f"eq.{meny['vecka']}",
        }
        gemensamt = {
            "restaurang": meny["restaurang"],
            "ar": ar,
            "vecka": meny["vecka"],
            "kalla": meny["kalla"],
        }
        self._anrop("DELETE", "lunch", params=filter)
        self._anrop("POST", "lunch", json=[{**gemensamt, **r} for r in meny["ratter"]])
        self.upsert("lunch_info", [{**gemensamt, "info": meny["info"],
                                    "hamtad": datetime.now(timezone.utc).isoformat()}],
                    "restaurang,ar,vecka")

    def ersatt_alla(self, tabell, rader, nyckel):
        """Byter ut hela tabellens innehåll mot de nyss hämtade raderna.

        Skriver först och raderar sedan det som inte kom med (äldre hamtad),
        så att ett fel inte lämnar tabellen tom. Alla rader ska ha samma hamtad.
        """
        if not rader:
            return
        self.upsert(tabell, rader, nyckel)
        self._anrop("DELETE", tabell, params={"hamtad": f"lt.{rader[0]['hamtad']}"})

    def upsert(self, tabell, rader, nyckel):
        if rader:
            self._anrop(
                "POST", tabell,
                params={"on_conflict": nyckel},
                headers={"Prefer": "resolution=merge-duplicates"},
                json=rader,
            )

    def rensa_gammalt(self):
        """Raderar allt som är äldre än DAGAR_KVAR dagar."""
        grans = (datetime.now(timezone.utc) - timedelta(days=DAGAR_KVAR)).isoformat()
        for tabell, kolumn in (("lunch", "hamtad"), ("lunch_info", "hamtad"),
                               ("nyheter", "publicerad"), ("bors", "hamtad")):
            self._anrop("DELETE", tabell, params={kolumn: f"lt.{grans}"})
