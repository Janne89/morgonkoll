"""Bättre Mat & Bar, Gärdet – veckomeny som PDF på restaurangens hemsida.

Sidan länkar alltid till veckans PDF ("Veckans meny"). När menyn byts får
PDF:en en ny adress, så vi letar upp länken varje gång och tolkar texten.
"""
import os
import re
import subprocess
import tempfile

import requests

RESTAURANG = "Bättre Mat & Bar"
SIDA = "https://www.battremat.com/kopia-p%C3%A5-b%C3%A4ttre-mat-bar-g%C3%A4rdet"

DAGAR = ["måndag", "tisdag", "onsdag", "torsdag", "fredag"]
PRIS = re.compile(r"(\d+)\s*:\s*-|(\d+)\s*kr", re.I)


def hitta_pdf(html):
    m = re.search(r'https://www\.battremat\.com/_files/ugd/[\w]+\.pdf', html)
    if not m:
        raise RuntimeError("Hittade ingen meny-PDF på sidan")
    return m.group(0)


def pdf_till_text(data):
    # pdftotext (poppler) behåller både blocken och mellanslagen bäst. Det är ett
    # kommandoradsprogram, inte ett Python-paket – det måste finnas installerat.
    with tempfile.TemporaryDirectory() as mapp:
        path = os.path.join(mapp, "meny.pdf")
        with open(path, "wb") as f:
            f.write(data)
        return subprocess.run(
            ["pdftotext", "-layout", "-enc", "UTF-8", path, "-"],
            check=True, capture_output=True,
        ).stdout.decode("utf-8")


def pris(text):
    m = PRIS.search(text)
    return int(m.group(1) or m.group(2)) if m else None


def utan_pris(text):
    text = PRIS.sub("", text)
    return re.sub(r"\s+", " ", text).strip(" ,")


def tolka(text):
    """Gör om menytexten till (vecka, info, rätter)."""
    vecka = re.search(r"vecka\s+(\d+)", text, re.I)
    vecka = int(vecka.group(1)) if vecka else None

    # Block = rader som hänger ihop, separerade av tomrader.
    block = [
        [rad.strip() for rad in b.splitlines() if rad.strip()]
        for b in re.split(r"\n\s*\n", text)
    ]
    block = [b for b in block if b]

    info = []
    ratter = []
    sektion = None
    for rader in block:
        forsta = rader[0].lower()
        if forsta.startswith("lunchmeny"):
            info += rader[1:]          # t.ex. "Sallad, bröd ... ingår"
            continue
        if forsta.startswith("veckans rätter"):
            sektion, rader = "veckans", rader[1:]
        elif forsta.startswith("alltid på menyn"):
            sektion, rader = "alltid", rader[1:]
        elif forsta.startswith(("barnmeny", "öppetider")):
            break
        elif forsta.startswith("lunchdryck"):
            info.append(rader[0])
            continue
        elif not sektion:
            # Före första sektionen är allt info. Beroende på poppler-version kan
            # "Sallad, bröd ... ingår" hamna i ett eget block efter rubriken.
            info += rader
            continue
        if not rader:
            continue

        titel = rader[0]
        dag = re.search(r"endast\s+(\w+?)ar\b", titel, re.I)
        dag = dag.group(1).lower() if dag and dag.group(1).lower() in DAGAR else None
        titel = re.sub(r"\(endast\s+\w+\)", "", titel)

        # Rader inom parentes är tillägg ("pannkakor ... 45:-") – behåll priset där.
        beskrivning = [r if r.startswith("(") else utan_pris(r) for r in rader[1:]]
        beskrivning = [b for b in beskrivning if b]

        ratter.append({
            "sektion": sektion,
            "namn": utan_pris(titel),
            "beskrivning": " ".join(beskrivning) or None,
            "pris": pris("\n".join(rader)),
            "dag": dag,
        })
    return vecka, info, ratter


def hamta():
    headers = {"User-Agent": "Mozilla/5.0 (Morgonkoll)"}
    html = requests.get(SIDA, headers=headers, timeout=30).text
    pdf_url = hitta_pdf(html)
    pdf = requests.get(pdf_url, headers=headers, timeout=30)
    pdf.raise_for_status()
    vecka, info, ratter = tolka(pdf_till_text(pdf.content))
    return {
        "restaurang": RESTAURANG,
        "vecka": vecka,
        "info": info,
        "ratter": ratter,
        "kalla": pdf_url,
    }
