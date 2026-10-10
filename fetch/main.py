"""Hämtar alla källor och skriver till Supabase.

Utan SUPABASE_URL/SUPABASE_SECRET_KEY blir det en torrkörning som bara skriver
ut vad som hämtades.
"""
import json
import sys
import traceback
from datetime import date

from db import Databas
from sources import lunch_battre

LUNCHKALLOR = [lunch_battre]


def ar_for_vecka(vecka, idag=None):
    """Menyn anger bara vecka – gissa år utifrån dagens ISO-vecka (kring nyår)."""
    ar, nu, _ = (idag or date.today()).isocalendar()
    if vecka > 50 and nu < 3:
        return ar - 1
    if vecka < 3 and nu > 50:
        return ar + 1
    return ar


def main():
    db = Databas.fran_miljo()
    if db is None:
        print("Torrkörning: SUPABASE_URL/SUPABASE_SECRET_KEY saknas, skriver inget.")

    fel = 0
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
                print(json.dumps(meny, ensure_ascii=False, indent=2))
        except Exception:
            fel += 1
            print(f"Fel i {kalla.__name__}:", file=sys.stderr)
            traceback.print_exc()

    if db:
        db.rensa_gammalt()
    return 1 if fel else 0


if __name__ == "__main__":
    sys.exit(main())
