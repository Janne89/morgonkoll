"""Lunch på Zaap Thai.

Veckomenyn läggs upp som bild på Facebook, som inte går att hämta automatiskt.
Rätterna är därför inskrivna här för hand från bilden – uppdatera RATTER om menyn ändras.
Priset beror på protein, inte på rätt, så det står i inforaden i stället för per rätt.
"""
from datetime import date

RESTAURANG = "Zaap Thai"
FACEBOOK = "https://www.facebook.com/ZaapThaiFood"

RATTER = [
    ("måndag", "Gaeng Phed – röd curry", "Röd currypasta, kokosmjölk, grönsaker. Serveras med ris."),
    ("måndag", "Pad Kratium – vitlök och peppar wok", "Ostronsås, grönsaker. Serveras med ris."),
    ("tisdag", "Gaeng Panaeng – panangcurry", "Panangcurrypasta, kokosmjölk, grönsaker. Serveras med ris."),
    ("tisdag", "Pad Gra Prow – stark basilikawok", "Basilika, chili, vitlök, fisksås, grönsaker. Serveras med ris."),
    ("onsdag", "Gaeng Keow Wan – grön curry", "Grön currypasta, kokosmjölk, grönsaker. Serveras med ris."),
    ("onsdag", "Ostronsåswok", "Grönsaker. Serveras med ris."),
    ("torsdag", "Gaeng Panaeng – panangcurry", "Panangcurrypasta, kokosmjölk, grönsaker. Serveras med ris."),
    ("torsdag", "Gai Pad Med Mamuang – cashewwok", "Chilipasta, grönsaker, cashewnötter. Serveras med ris."),
    ("fredag", "Gaeng Massaman – massamancurry", "Massamancurrypasta, kokosmjölk, grönsaker, jordnötter. Serveras med ris."),
    ("fredag", "Pad Prik Gaeng – röd currywok", "Röd currypasta, grönsaker. Serveras med ris."),
]
INFO = [
    "Vegetarisk/tofu 145 kr · kyckling 145 kr · fläsk/biff 155 kr · räkor 155 kr",
    "Inkl. dryck, 11.00–14.30",
    "Inskriven från veckomenyn på Facebook – kan ha ändrats",
]


def hamta():
    return {
        "restaurang": RESTAURANG,
        "vecka": date.today().isocalendar()[1],
        "info": INFO,
        "ratter": [{"namn": n, "beskrivning": b, "pris": None, "sektion": "veckans", "dag": d} for d, n, b in RATTER],
        "kalla": FACEBOOK,
    }
