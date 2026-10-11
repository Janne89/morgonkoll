"""Hämtar källorna och skriver till Supabase.

    python main.py                 # allt
    python main.py nyheter bors    # bara vissa delar (lunch, nyheter, bors, systembolaget, trender, riksbanken, shl, evenemang)

Utan SUPABASE_URL/SUPABASE_SECRET_KEY blir det en torrkörning som bara skriver
ut vad som hämtades.
"""
import json
import sys
import traceback
from collections import Counter
from datetime import date

from db import Databas
from sources import bors, evenemang, lunch_airamen, lunch_battre, lunch_lulu, lunch_zaap, nyheter, riksbanken, shl, systembolaget, trender

LUNCHKALLOR = [lunch_battre, lunch_lulu, lunch_airamen, lunch_zaap]


def ar_for_vecka(vecka, idag=None):
    """Menyn anger bara vecka – gissa år utifrån dagens ISO-vecka (kring nyår)."""
    ar, nu, _ = (idag or date.today()).isocalendar()
    if vecka > 50 and nu < 3:
        return ar - 1
    if vecka < 3 and nu > 50:
        return ar + 1
    return ar


def lunch(db):
    # Varje restaurang för sig – en trasig meny ska inte stoppa de andra.
    fel = []
    for kalla in LUNCHKALLOR:
        try:
            meny = kalla.hamta()
            if not meny["vecka"] or not meny["ratter"]:
                raise RuntimeError(f"Tom eller otolkbar meny: {meny}")
            ar = ar_for_vecka(meny["vecka"])
            print(f"{meny['restaurang']}: vecka {meny['vecka']} {ar}, "
                  f"{len(meny['ratter'])} rätter")
            if db:
                db.ersatt_lunch(meny, ar)
            else:
                print(json.dumps(meny, ensure_ascii=False, indent=2)[:600])
        except Exception as e:
            fel.append(f"{kalla.__name__}: {e}")
    if fel:
        raise RuntimeError("Lunch: " + "; ".join(fel))


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
        db.ersatt_alla("systembolaget", produkter, "artikelnummer")


def googletrender(db):
    regioner, fel = trender.hamta()
    for kod, rader in regioner.items():
        print(f"Google Trends {kod}: {len(rader)} sökord")
        for t in rader[:5]:
            print(f"  {t['plats']:>2}. {t['land']} {t['trafik'] or '':>9} {t['sokord']} – {t['nyhet_rubrik'] or ', '.join(t['relaterade'])}")
        if db:
            db.ersatt_alla("trender", rader, "region,sokord", {"region": f"eq.{kod}"})
    if fel or not any(regioner.values()):
        raise RuntimeError("Google Trends: " + ("; ".join(fel) or "tomt flöde – har formatet ändrats?"))


def styrranta(db):
    rad = riksbanken.hamta()
    print(f"Riksbanken: styrränta {rad['styrranta']} % ({rad['datum']}), "
          f"ändrad {rad['andrad']} från {rad['forra_styrranta']} %")
    for b in rad.get("kommande", []):
        print(f"  besked {b['datum']}")
    for n in rad.get("nyheter", []):
        print(f"  {n['publicerad'][:10]} {n['rubrik']}")
    if db:
        db.upsert("riksbanken", [rad], "id")


def shlmatcher(db):
    filt = shl.forval()
    matcher = shl.hamta(filt=filt)
    tabell = shl.hamta_tabell(filt)
    topp = ", ".join(f"{r['plats']}. {r['lag']} {r['poang']}p" for r in tabell[:5])
    print(f"SHL-tabell: {topp} …")
    print(f"SHL: {len(matcher)} matcher")
    for m in matcher[:12]:
        resultat = f"{m['hemma_mal']}–{m['borta_mal']}" if m["hemma_mal"] is not None else ""
        print(f"  {m['start'][:16]} {m['status']:9} {m['hemma']} – {m['borta']} {resultat}")
    if db:
        if matcher:
            db.ersatt_alla("shl", matcher, "uuid")
        else:
            db._anrop("DELETE", "shl", params={"uuid": "not.is.null"})   # uppehåll – töm
        db.ersatt_alla("shl_tabell", tabell, "plats")


def stockholmsevenemang(db):
    rader = evenemang.hamta()
    stora = [r for r in rader if r["stort"]]
    print(f"Evenemang: {len(stora)} stora, {len(rader) - len(stora)} kortare")
    for r in stora[:5]:
        print(f"  {r['start']} {r['titel']} – {r['plats']} ({r['besokare']} besökare)")
    if not rader:
        raise RuntimeError("Evenemang: inga alls – har API:et ändrats?")
    if db:
        db.ersatt_alla("evenemang", rader, "id")


DELAR = {"lunch": lunch, "nyheter": nyhetsrubriker, "bors": borsdata, "systembolaget": slapp,
         "trender": googletrender, "riksbanken": styrranta, "shl": shlmatcher, "evenemang": stockholmsevenemang}


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
