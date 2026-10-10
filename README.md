# Morgonkoll

Daglig morgonöversikt för mig och kollegorna: lunchmenyer, väder, nyheter och börs på en sida.

Live (när den är publicerad): https://janne89.github.io/morgonkoll/

## Upplägg

```
GitHub Pages (den här repon)   
   ├─ Väder: hämtas direkt från SMHI i webbläsaren (sparas inte)
   └─ Lunch, nyheter, börs: läses från Supabase (publik nyckel + RLS, bara läsning)
                ↑
GitHub Actions, vardagar flera gånger på morgonen
   └─ fetch/ (Python): hämtar källorna, skriver till Supabase med hemlig nyckel
      och raderar data äldre än 7 dagar (för att hålla sig inom gratisnivån)
```

### Beslut som är tagna
- **Hämtning:** GitHub Actions + Python (inte Supabase Edge Functions).
  Obs: GitHub stänger av schemalagda körningar efter 60 dagar utan commits – slå på igen i Actions-fliken.
- **Supabase:** eget projekt `morgonkoll` (inte babatravels-projektet). Region Stockholm.
  Security: Data API på, auto-expose av, automatic RLS på.
- **Lagring:** max 7 dagars data per källa.
- **Hemligheter:** repot är publikt. Hemlig Supabase-nyckel bara som GitHub Secret
  (`SUPABASE_URL`, `SUPABASE_SECRET_KEY`), aldrig i koden. Den publika nyckeln får ligga i frontend.
- **Stil i koden:** svenska namn och kommentarer.

## Källor

### Lunch – Bättre Mat & Bar, Gärdet ✅ tolkare klar
- Sida: https://www.battremat.com/kopia-p%C3%A5-b%C3%A4ttre-mat-bar-g%C3%A4rdet
- Knappen "Veckans meny" länkar till en PDF (`/_files/ugd/<id>.pdf`) som får ny adress varje vecka.
- PDF:en har riktig text. `pdftotext -layout` (poppler) ger bäst resultat – pypdf slår ihop ord.
  I Actions: `sudo apt-get install -y poppler-utils`.
- Menyn byts måndag morgon (senast `Last-Modified: mån 07:39`), så hämta flera gånger på morgonen.
- [fetch/sources/lunch_battre.py](fetch/sources/lunch_battre.py) returnerar vecka, info och rätter
  (sektion `veckans`/`alltid`, namn, beskrivning, pris, `dag` för dagsspecifika rätter som
  "Raggmunk (endast tisdagar)"). Testad mot vecka 41 – alla 9 rätter tolkas rätt.
- Fler restauranger kommer – en modul per restaurang i `fetch/sources/`.

### Väder – SMHI ✅ API utrett
- `https://opendata-download-metfcst.smhi.se/api/category/snow1g/version/1/geotype/point/lon/18.07/lat/59.33/data.json`
- Tillåter anrop från webbläsaren (CORS `*`), fri licens (CC BY 4.0 – ange SMHI som källa).
  (Open-Meteo valdes bort: bara gratis för icke-kommersiellt bruk.)
- Timvis: `air_temperature`, `precipitation_amount_mean`, `probability_of_precipitation`,
  `wind_speed`, `symbol_code` (SMHI Wsymb2, 1–27: 1 klart … 6 mulet, 18–20 regn, 25–27 snö).
- Önskemål: snygg, överskådlig bild över dagen (temperaturkurva, regnstaplar, symboler).

### Nyheter – SVT + Dagens industri ✅
- RSS: `svt.se/nyheter/inrikes/rss.xml`, `svt.se/nyheter/utrikes/rss.xml`, `di.se/rss`
  (SVT:s allmänna flöde är mest lokalt och sport). Bara rubrik, ingress och länk sparas.
- [fetch/sources/nyheter.py](fetch/sources/nyheter.py) → tabellen `nyheter` (nyckel: länk).

### Börs & valuta ✅
- Index via Yahoo Finance chart-API (inofficiellt, kan sluta fungera – villkorsfråga, inte olagligt):
  `^OMX` (OMXS30), `^GSPC`, `^IXIC`, `^GDAXI`. En månads dagsstängningar för minidiagram.
- Valuta via Riksbankens öppna API (`api.riksbank.se/swea/v1`): `SEKUSDPMI`, `SEKEURPMI`.
- [fetch/sources/bors.py](fetch/sources/bors.py) → tabellen `bors` (en rad per instrument, senaste läget).

## Nästa steg
1. ✅ Skapa Supabase-projektet `morgonkoll` och kör [supabase/tabeller.sql](supabase/tabeller.sql)
   i SQL Editor (tabellerna `lunch` och `lunch_info`, RLS: anon får bara läsa).
2. ✅ Lägg `SUPABASE_URL` och `SUPABASE_SECRET_KEY` som GitHub Secrets och kör workflowet
   "Hämta" manuellt i Actions-fliken för att se att det skriver.
3. ✅ [fetch/main.py](fetch/main.py) + [fetch/db.py](fetch/db.py) och
   [.github/workflows/hamta.yml](.github/workflows/hamta.yml) (vardagar 05:17–08:17 UTC + manuellt).
   Utan miljövariablerna blir `python fetch/main.py` en torrkörning som skriver ut menyn.
4. ✅ Frontend: [index.html](index.html) med väderkort (SMHI: kurva, regnstaplar, 5 dagar) och
   lunchkort (dagens rätter först). Kräver att GitHub Pages är på (Settings → Pages → main, /root).
5. ✅ Nyheter och börs. Kör om [supabase/tabeller.sql](supabase/tabeller.sql) (går att köra flera gånger)
   för tabellerna `nyheter` och `bors`.
