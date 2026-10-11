"""Hämtar källorna och skriver till Supabase.

    python main.py                 # allt
    python main.py nyheter bors    # bara vissa delar (lunch, nyheter, bors, systembolaget)

Utan SUPABASE_URL/SUPABASE_SECRET_KEY blir det en torrkörning som bara skriver
ut vad som hämtades.
"""
import json
import sys
import traceback
from collections import Counter
from datetime import date

from db import Databas
from sources import bors, lunch_battre, nyheter, systembolaget

LUNCHKALLOR = [lunch_battre]


def ar_for_vecka(vecka, idag=None):
    """Menyn anger bara vecka – gissa år utifrån dagens ISO-vecka (kring nyår)."""
    ar, nu, _ = (idag or date.today()).isocalendar()
    if vecka > 50 and nu < 3:
        return ar - 1
    if vecka < 3 and nu > 50:
        return ar + 1
    return ar


def lunch(db):
    for kalla in LUNCHKALLOR:
        meny = kalla.hamta()
        if not meny["vecka"] or not meny["ratter"]:
            raise RuntimeError(f"Tom eller otolkbar meny: {meny}")
        ar = ar_for_vecka(meny["vecka"])
        print(f"{meny['restaurang']}: vecka {meny['vecka']} {ar}, "
              f"{len(meny['ratter'])} rätter")
        if db:
            db.ersatt_lunch(meny, ar)
        else:
            print(json.dumps(meny, ensure_ascii=False, indent=2))


def nyhetsrubriker(db):
    artiklar = nyheter.hamta()
    print(f"Nyheter: {len(artiklar)} rubriker")
    if db:
        db.upsert("nyheter", artiklar, "lank")
    else:
        for a in sorted(artiklar, key=lambda a: a["publicerad"], reverse=True)[:10]:
            print(f"  {a['kalla']:4} {a['publicerad'][:16]} {a['rubrik']}")


def borsdata(db):
    instrument, fel = bors.hamta()
    for i in instrument:
        print(f"  {i['namn']:8} {i['varde']:>10} {i['forandring_pct']:+.2f}% ({i['datum']})")
    if db:
        db.upsert("bors", instrument, "symbol")
    if fel:
        raise RuntimeError("Börs: " + "; ".join(fel))


def slapp(db):
    produkter = systembolaget.hamta()
    if not produkter:
        raise RuntimeError("Systembolaget: inga kommande släpp – har API:et ändrats?")
    antal = Counter((p["saljstart"], p["sortiment"]) for p in produkter)
    for (dag, sortiment), n in sorted(antal.items()):
        print(f"  {dag} {sortiment}: {n} produkter")
    if db:
        db.ersatt_systembolaget(produkter)


DELAR = {"lunch": lunch, "nyheter": nyhetsrubriker, "bors": borsdata, "systembolaget": slapp}


def main(namn):
    okanda = set(namn) - DELAR.keys()
    if okanda:
        sys.exit(f"Okända delar: {', '.join(okanda)} (finns: {', '.join(DELAR)})")
    delar = [DELAR[n] for n in namn] or list(DELAR.values())

    db = Databas.fran_miljo()
    if db is None:
        print("Torrkörning: SUPABASE_URL/SUPABASE_SECRET_KEY saknas, skriver inget.")

    # Varje del körs för sig så att ett fel inte stoppar resten.
    fel = 0
    for del_ in delar:
        try:
            del_(db)
        except Exception:
            fel += 1
            print(f"Fel i {del_.__name__}:", file=sys.stderr)
            traceback.print_exc()

    if db:
        db.rensa_gammalt()
    return 1 if fel else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
