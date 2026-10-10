# Morgonkoll

Daglig morgonöversikt för mig och kollegorna: väder, börs, nyheter, lunch och dagens namnsdag på en sida.

Live: https://janne89.github.io/morgonkoll/

## Källor i korthet

| Kort | Källa | Hämtas | Uppdateras |
|---|---|---|---|
| Väder | [SMHI](https://www.smhi.se/) öppna prognos-API | I webbläsaren | Varje gång sidan öppnas (SMHI gör ny prognos ungefär varje timme) |
| Namnsdag, helg- och flaggdag | [Svenska dagar-API](https://sholiday.faboul.se/) | I webbläsaren | Varje gång sidan öppnas |
| Temadagar (kanelbullens dag m.m.) | Egen lista i `index.html` | I webbläsaren | – (fasta datum + uträknade rörliga) |
| Börs: OMXS30, S&P 500, Nasdaq, DAX | Yahoo Finance (inofficiellt API) | GitHub Actions → Supabase | Var 15:e min vardagar, ca 06–22 |
| Valuta: USD/SEK, EUR/SEK | [Riksbanken](https://www.riksbank.se/) öppna API | GitHub Actions → Supabase | Med börsen, men Riksbanken publicerar bara en kurs per bankdag |
| Nyheter | RSS från [SVT](https://www.svt.se/nyheter/) (inrikes, utrikes) och [Di](https://www.di.se/) | GitHub Actions → Supabase | Var 15:e min vardagar ca 06–22, varje timme helger ca 08–22 |
| Lunch: Bättre Mat & Bar, Gärdet | Veckomeny-PDF på [battremat.com](https://www.battremat.com/kopia-p%C3%A5-b%C3%A4ttre-mat-bar-g%C3%A4rdet) | GitHub Actions → Supabase | Vardagar en gång i timmen, 06:17–09:17 (vintertid) / 07:17–10:17 (sommartid) |

Varje kort visar diskret i källraden när datan senast hämtades. Står sidan öppen hämtar den
väder, nyheter och börs på nytt var 15:e minut (bara när fliken syns).

**Varför två vägar?** SMHI och Svenska dagar tillåter anrop direkt från webbläsaren (CORS).
SVT, Di, Yahoo och Riksbanken gör det inte, och lunchen kräver PDF-tolkning – de hämtas därför
av ett Python-jobb i GitHub Actions och sparas i Supabase, som sidan läser från.

## Schema (GitHub Actions)

[.github/workflows/hamta.yml](.github/workflows/hamta.yml). Cron är i UTC – svensk tid är +1 (vinter) / +2 (sommar).

| Cron (UTC) | Svensk tid (ca) | Kör |
|---|---|---|
| `17 5-8 * * 1-5` | vardagar 06:17–09:17 vinter / 07:17–10:17 sommar, varje timme | allt (lunch, nyheter, börs) |
| `*/15 4-20 * * 1-5` | vardagar 05:00–21:45 vinter / 06:00–22:45 sommar, var 15:e min | nyheter + börs |
| `0 6-20 * * 0,6` | helger 07–21 vinter / 08–22 sommar, varje timme | nyheter |
| manuellt (Run workflow) | – | allt |

- GitHub fördröjer ofta schemalagda körningar 5–15 min och hoppar ibland över någon.
- Två körningar körs aldrig samtidigt (`concurrency`).
- Lokalt: `python fetch/main.py [lunch] [nyheter] [bors]` – utan argument körs allt.
  Utan `SUPABASE_URL`/`SUPABASE_SECRET_KEY` blir det en torrkörning som bara skriver ut resultatet.
- Varje körning raderar data äldre än 7 dagar (för att hålla sig inom Supabase gratisnivå).

## Upplägg

```
GitHub Pages (index.html)
   ├─ Väder (SMHI) och dagens namnsdag/helgdag (Svenska dagar): direkt i webbläsaren
   └─ Lunch, nyheter, börs: läses från Supabase (publik nyckel + RLS, bara läsning)
                ↑
GitHub Actions (se schema ovan)
   └─ fetch/ (Python): hämtar källorna och skriver till Supabase med hemlig nyckel
```

### Beslut
- **Hämtning:** GitHub Actions + Python (inte Supabase Edge Functions).
  Obs: GitHub stänger av schemalagda körningar efter 60 dagar utan commits – slå på igen i Actions-fliken.
- **Supabase:** eget projekt `morgonkoll`, region Stockholm. Data API på, auto-expose av, automatic RLS på.
  Tabeller och rättigheter: [supabase/tabeller.sql](supabase/tabeller.sql) (går att köra flera gånger).
- **Hemligheter:** repot är publikt. Hemlig Supabase-nyckel bara som GitHub Secret
  (`SUPABASE_URL`, `SUPABASE_SECRET_KEY`), aldrig i koden. Den publika nyckeln ligger i `index.html`.
- **Stil i koden:** svenska namn och kommentarer.

## Detaljer per källa

### Väder – SMHI
- `https://opendata-download-metfcst.smhi.se/api/category/snow1g/version/1/geotype/point/lon/18.07/lat/59.33/data.json`
- Licens CC BY 4.0 – SMHI anges som källa. (Open-Meteo valdes bort: bara gratis för icke-kommersiellt bruk.)
- Timvärden: `air_temperature`, `precipitation_amount_mean`, `probability_of_precipitation`,
  `wind_speed`, `symbol_code` (Wsymb2, 1–27). Kortet visar nuläge, 16 timmar framåt och 5 dagar.

### Namnsdag och speciella dagar
- `https://sholiday.faboul.se/dagar/v2.1/ÅÅÅÅ/MM/DD` ger namnsdag, helgdag och flaggdag.
- Temadagar som inte finns i API:et ligger i `TEMADAGAR` (nyckel `"MM-DD"`) i [index.html](index.html).
  Rörliga dagar (fettisdagen, mors/fars dag, surströmmingspremiären, Black Friday, advent)
  räknas ut i `rorligaTemadagar()`.

### Börs & valuta
- Index via Yahoo Finance chart-API (`query1.finance.yahoo.com/v8/finance/chart/<symbol>`):
  `^OMX` (OMXS30), `^GSPC`, `^IXIC`, `^GDAXI`. Inofficiellt – kan sluta fungera, och är formellt
  emot Yahoos villkor (avtalsfråga, inte olagligt). Fördröjda värden.
- Valuta via Riksbankens öppna API (`api.riksbank.se/swea/v1`): `SEKUSDPMI`, `SEKEURPMI`.
- En månads dagsvärden sparas för minidiagrammen.
- [fetch/sources/bors.py](fetch/sources/bors.py) → tabellen `bors` (en rad per instrument).
  Varje instrument hämtas för sig, så ett fel stoppar inte resten.

### Nyheter – SVT + Dagens industri
- RSS: `svt.se/nyheter/inrikes/rss.xml`, `svt.se/nyheter/utrikes/rss.xml`, `di.se/rss`
  (SVT:s allmänna flöde är mest lokalt och sport). Bara rubrik, ingress och länk sparas.
- [fetch/sources/nyheter.py](fetch/sources/nyheter.py) → tabellen `nyheter` (nyckel: länk).

### Lunch – Bättre Mat & Bar, Gärdet
- Knappen "Veckans meny" länkar till en PDF (`/_files/ugd/<id>.pdf`) som får ny adress varje vecka.
- Menyn byts måndag morgon (senast `Last-Modified: mån 07:39`), därför flera hämtningar på morgonen.
- `pdftotext -layout` (poppler) ger bäst resultat – pypdf slår ihop ord. Installeras bara i lunchkörningar.
- [fetch/sources/lunch_battre.py](fetch/sources/lunch_battre.py) → tabellerna `lunch` (en rad per rätt)
  och `lunch_info`. Veckans rader ersätts vid varje hämtning.

## Lägga till en källa
- **Restaurang:** ny modul i `fetch/sources/` med `hamta()` som returnerar samma form som
  `lunch_battre.py`, och lägg till den i `LUNCHKALLOR` i [fetch/main.py](fetch/main.py).
- **Nyhetsflöde:** en rad i `FLODEN` i [fetch/sources/nyheter.py](fetch/sources/nyheter.py).
  Filterknappen på sidan dyker upp av sig själv.
- **Index:** en rad i `INDEX` i [fetch/sources/bors.py](fetch/sources/bors.py), och symbolen i
  `ordning` i `visaBors()` i [index.html](index.html) för att bestämma plats.
- **Temadag:** en rad i `TEMADAGAR` i [index.html](index.html).
