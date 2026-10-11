# Morgonkoll

Daglig morgonöversikt för mig och kollegorna: väder, elpris, SL-avgångar, börs, nyheter, Google-trender, lunch, Systembolagets släpp och dagens namnsdag på en sida.

Live: https://janne89.github.io/morgonkoll/

## Källor i korthet

| Kort | Källa | Hämtas | Uppdateras |
|---|---|---|---|
| Väder | [SMHI](https://www.smhi.se/) öppna prognos-API | I webbläsaren | Varje gång sidan öppnas (SMHI gör ny prognos ungefär varje timme) |
| SL-avgångar: Arenan, Solna station | [SL Transport API](https://www.trafiklab.se/api/our-apis/sl/transport/) (öppet, ingen nyckel) | I webbläsaren | Varje minut medan fliken syns (realtid) |
| Elpris idag/imorgon per elområde (SE1–SE4) | [elprisetjustnu.se](https://www.elprisetjustnu.se/) (Nord Pool) | I webbläsaren | När sidan öppnas och var 15:e min (morgondagens priser ca 13:00) |
| Vädervarningar (gul/orange/röd) för Stockholms län | [SMHI](https://www.smhi.se/) öppna varnings-API | I webbläsaren | När sidan öppnas och var 15:e min |
| Störningar på SL-linjerna | [SL Deviations API](https://www.trafiklab.se/api/our-apis/sl/deviations/) | I webbläsaren | Med avgångarna, högst var 5:e min |
| Soluppgång, solnedgång, dagslängd | Uträknat i webbläsaren (SunCalc-algoritmen) | – | – |
| Dagens prisjämförelse (en vara per dag mot KPI) | [SCB](https://www.scb.se/) KPI per varugrupp | I webbläsaren | När sidan öppnas (SCB publicerar en gång i månaden) |
| Namnsdag, helg- och flaggdag | [Svenska dagar-API](https://sholiday.faboul.se/) | I webbläsaren | Varje gång sidan öppnas |
| Temadagar (kanelbullens dag m.m.) | Egen lista i `index.html` | I webbläsaren | – (fasta datum + uträknade rörliga) |
| Börs: OMXS30, S&P 500, Nasdaq, DAX, olja (Brent), guld, bitcoin | Yahoo Finance (inofficiellt API) | GitHub Actions → Supabase | Var 15:e min vardagar ca 06–22, varje timme helger (för bitcoin) |
| Valuta: USD/SEK, EUR/SEK | [Riksbanken](https://www.riksbank.se/) öppna API | GitHub Actions → Supabase | Med börsen, men Riksbanken publicerar bara en kurs per bankdag |
| Nyheter | RSS från [SVT](https://www.svt.se/nyheter/) (inrikes, utrikes) och [Di](https://www.di.se/), AI-flik med OpenAI, Anthropic, Google, TechCrunch och The Verge | GitHub Actions → Supabase | Var 15:e min vardagar ca 06–22, varje timme helger ca 08–22 |
| Trendar på Google (Sverige) | [Google Trends](https://trends.google.com/trending?geo=SE): internt API (inofficiellt) + RSS | GitHub Actions → Supabase | Med nyheterna |
| Styrräntan, kommande räntebesked, Riksbankens pressmeddelanden (i Verktyg → Ränta) | [Riksbanken](https://www.riksbank.se/): API, kalendersidan och RSS | GitHub Actions → Supabase | Med nyheterna (fångar beskeden 09:30) |
| Systembolaget: kommande släpp (tillfälligt sortiment, webblanseringar, lokalt & småskaligt m.m.) | systembolaget.se:s sök-API (inofficiellt) | GitHub Actions → Supabase | Med lunchen, vardagsmorgnar |
| Lunch: Bättre Mat & Bar, Gärdet | Veckomeny-PDF på [battremat.com](https://www.battremat.com/kopia-p%C3%A5-b%C3%A4ttre-mat-bar-g%C3%A4rdet) | GitHub Actions → Supabase | Vardagar en gång i timmen, 06:17–09:17 (vintertid) / 07:17–10:17 (sommartid) |

Varje kort visar diskret i källraden när datan senast hämtades. Står sidan öppen hämtar den
väder, nyheter och börs på nytt var 15:e minut och SL-avgångarna varje minut (bara när fliken syns).

**Varför två vägar?** SMHI, SL, elprisetjustnu.se och Svenska dagar tillåter anrop direkt från webbläsaren (CORS).
SVT, Di, Yahoo, Riksbanken, Google Trends och Systembolaget gör det inte, och lunchen kräver PDF-tolkning – de hämtas därför
av ett Python-jobb i GitHub Actions och sparas i Supabase, som sidan läser från.

## Schema (GitHub Actions)

[.github/workflows/hamta.yml](.github/workflows/hamta.yml). Cron är i UTC – svensk tid är +1 (vinter) / +2 (sommar).

| Cron (UTC) | Svensk tid (ca) | Kör |
|---|---|---|
| `17 5-8 * * 1-5` | vardagar 06:17–09:17 vinter / 07:17–10:17 sommar, varje timme | allt (lunch, nyheter, börs, trender, Riksbanken, Systembolaget) |
| `*/15 4-20 * * 1-5` | vardagar 05:00–21:45 vinter / 06:00–22:45 sommar, var 15:e min | nyheter + börs + trender + Riksbanken |
| `0 6-20 * * 0,6` | helger 07–21 vinter / 08–22 sommar, varje timme | nyheter + börs + trender + Riksbanken |
| manuellt (Run workflow) | – | allt |

- GitHub fördröjer ofta schemalagda körningar 5–15 min och hoppar ibland över någon.
- Två körningar körs aldrig samtidigt (`concurrency`).
- Lokalt: `python fetch/main.py [lunch] [nyheter] [bors] [systembolaget] [trender] [riksbanken]` – utan argument körs allt.
  Utan `SUPABASE_URL`/`SUPABASE_SECRET_KEY` blir det en torrkörning som bara skriver ut resultatet.
- Varje körning raderar data äldre än 7 dagar (för att hålla sig inom Supabase gratisnivå).

## Upplägg

```
GitHub Pages (index.html)
   ├─ Väder (SMHI), elpris, SL-avgångar, namnsdag (Svenska dagar) och verktygens data: direkt i webbläsaren
   └─ Lunch, nyheter, börs, trender, Riksbanken, Systembolaget: läses från Supabase (publik nyckel + RLS, bara läsning)
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

### Vädervarningar
- `https://opendata-download-warnings.smhi.se/ibww/api/version/1/warning.json` – SMHI:s konsekvensbaserade varningar.
  Bara nivåerna gul, orange och röd där något drabbat område matchar `VARNINGSOMRADE` (Stockholm) visas, överst i
  väderkortet. "Meddelanden" (t.ex. risk för vattenbrist) visas inte. Inga varningar → ingenting syns.

### Soltider
- Räknas i webbläsaren för Stockholm (59,33 N, 18,07 E) med SunCalc-algoritmen; visas i sidhuvudet med dagslängd
  och skillnad mot i går.

### Dagens prisjämförelse
- SCB-tabellen `KPI2020COICOPM` (KPI per varugrupp, index 2020 = 100), de senaste 140 månaderna för varorna i
  `PRISVAROR` i [index.html](index.html) plus totalen (`00`). Samma vara för alla hela dagen (dagnummer modulo antal
  varor), pilarna bläddrar. Visar ändring sedan 2020 och senaste året jämfört med alla priser, och ett diagram.
- Ny vara: en rad i `PRISVAROR` med COICOP-koden (se SCB-tabellens varugrupper) och namn, ev. ett kortare namn
  för diagrammet.

### Elpris
- `https://www.elprisetjustnu.se/api/v1/prices/ÅÅÅÅ/MM-DD_SE3.json` – spotpris per kvart, exkl. moms.
  Kortet visar inkl. 25 % moms (utan nätavgift och elhandlarens påslag), timmedel i diagrammet,
  priset just nu och billigaste 3 timmar i följd framåt. Morgondagen (404 innan ca 13:00) får egen flik.
- Prisnivå: dagens snitt jämfört med snittet för de 7 föregående dagarna (samma API). Minst 15 % under = lågt,
  minst 15 % över = högt, annars normalt.
- Elområdet väljs med knapparna eller i den lilla kartan och sparas i webbläsaren (förvalt SE3).
  Kartan (`ELKARTA` i [index.html](index.html)) är schematisk: Natural Earths län (public domain), förenklade och
  sammanslagna till elområden – SE1 Norrbotten; SE2 Västerbotten, Jämtland, Västernorrland, Gävleborg;
  SE4 Skåne, Blekinge, Kronoberg; resten SE3. De verkliga gränserna följer inte länen exakt.

### SL-avgångar
- `https://transport.integration.sl.se/v1/sites/<id>/departures?forecast=60` – realtid, öppen CORS, ingen nyckel.
- Hållplatserna ligger i `HALLPLATSER` i [index.html](index.html). ID slås upp i
  `https://transport.integration.sl.se/v1/sites` (Arenan = 3555, Solna station = 9509).
- Kortet visar de `ANTAL_AVGANGAR` närmaste avgångarna per hållplats, med spår/läge,
  ⚠ vid störning (meddelandet syns när man håller musen över) och överstruket om turen är inställd.

### Namnsdag och speciella dagar
- `https://sholiday.faboul.se/dagar/v2.1/ÅÅÅÅ/MM/DD` ger namnsdag, helgdag och flaggdag.
- Temadagar som inte finns i API:et ligger i `TEMADAGAR` (nyckel `"MM-DD"`) i [index.html](index.html).
  Rörliga dagar (fettisdagen, mors/fars dag, surströmmingspremiären, Black Friday, advent)
  räknas ut i `rorligaTemadagar()`.

### SL-störningar
- `https://deviations.integration.sl.se/v1/messages?future=false&line=…` för linjerna som går från hållplatserna i
  `HALLPLATSER` (efter filter), plus `site=…` för själva hållplatserna. Störningar skapade senaste dygnet visas direkt
  (troligen akuta, t.ex. signalfel), äldre och långvariga under "Övriga störningar". Detaljtexten syns vid hovring.
- Misslyckas ett avgångsanrop (t.ex. 429, för många anrop) visas senast hämtade avgångar med klockslag.

### Börs & valuta
- Index via Yahoo Finance chart-API (`query1.finance.yahoo.com/v8/finance/chart/<symbol>`):
  `^OMX` (OMXS30), `^GSPC`, `^IXIC`, `^GDAXI`, `BZ=F` (Brent), `GC=F` (guld), `BTC-USD`. Inofficiellt – kan sluta fungera, och är formellt
  emot Yahoos villkor (avtalsfråga, inte olagligt). Fördröjda värden.
- Valuta via Riksbankens öppna API (`api.riksbank.se/swea/v1`): `SEKUSDPMI`, `SEKEURPMI`.
- En månads dagsvärden sparas för minidiagrammen.
- [fetch/sources/bors.py](fetch/sources/bors.py) → tabellen `bors` (en rad per instrument).
  Varje instrument hämtas för sig, så ett fel stoppar inte resten.

### Nyheter – SVT + Dagens industri
- RSS: `svt.se/nyheter/inrikes/rss.xml`, `svt.se/nyheter/utrikes/rss.xml`, `di.se/rss`
  (SVT:s allmänna flöde är mest lokalt och sport). Bara rubrik, ingress och länk sparas.
- AI-fliken (kolumnen `amne = 'ai'`, visas inte under "Alla"):
  - OpenAI: `openai.com/news/rss.xml`. Poster utan kategori (kundcase) hoppas över.
  - Anthropic har inget eget flöde. Vi använder ett som skrapas av community-projektet
    [Olshansk/rss-feeds](https://github.com/Olshansk/rss-feeds) – inofficiellt.
  - Google (Gemini): `blog.google/technology/ai/rss/` och `deepmind.google/blog/rss.xml`.
  - xAI (Grok), Meta och Mistral saknar flöden – deras nyheter fångas av TechCrunch AI och The Verge AI (Atom).
- [fetch/sources/nyheter.py](fetch/sources/nyheter.py) → tabellen `nyheter` (nyckel: länk). Klarar RSS och Atom.

### Lunch – Bättre Mat & Bar, Gärdet
- Knappen "Veckans meny" länkar till en PDF (`/_files/ugd/<id>.pdf`) som får ny adress varje vecka.
- Menyn byts måndag morgon (senast `Last-Modified: mån 07:39`), därför flera hämtningar på morgonen.
- `pdftotext -layout` (poppler) ger bäst resultat – pypdf slår ihop ord. Installeras bara i lunchkörningar.
- [fetch/sources/lunch_battre.py](fetch/sources/lunch_battre.py) → tabellerna `lunch` (en rad per rätt)
  och `lunch_info`. Veckans rader ersätts vid varje hämtning.

### Trendar på Google
- **Listan** kommer från samma interna API som trends.google.se/trending använder
  (`POST trends.google.com/_/TrendsUi/data/batchexecute`, rpc `i0OFE`): alla trender senaste 24 h i Googles
  ordning, med ungefärlig sökvolym och relaterade sökningar. Inofficiellt – kan sluta fungera.
- **Nyhetsartiklar** finns bara i RSS-flödet `trends.google.com/trending/rss?geo=SE`, som i sin tur bara har de
  ~10 *senast startade* trenderna (därför skilde sig RSS-listan från sidan). Rubriken används som förklaring
  när sökordet finns där, annars "Även: <relaterade sökningar>". Fungerar inte det interna API:et används bara RSS.
  (Gamla adressen `.../trends/trendingsearches/daily/rss` är nedlagd.)
- [fetch/sources/trender.py](fetch/sources/trender.py) → tabellen `trender` (de 15 första), som ersätts helt
  vid varje hämtning. Kortet visar de 10 första; sökordet länkar till en Google-sökning, raden under till artikeln.

### Riksbanken – styrränta och räntebesked
- Styrräntan: serien `SECBREPOEFF` i `api.riksbank.se/swea/v1`. Senaste ändringen räknas fram ur serien.
- Kommande räntebesked läses från [kalendersidan](https://www.riksbank.se/sv/press-och-publicerat/kalender/)
  (raderna "Publicering av penningpolitiskt beslut") – inget API eller ics finns, så det kan gå sönder om sidan byggs om.
- Pressmeddelanden: `riksbank.se/sv/rss/pressmeddelanden/`, filtrerat på styrränta/penningpolitik (de 3 senaste).
- [fetch/sources/riksbanken.py](fetch/sources/riksbanken.py) → tabellen `riksbanken` (en rad). Fel i kalender eller
  RSS stoppar inte räntan; då behålls förra hämtningens värden.

### Systembolaget – släpp
- Inget öppet API finns längre (gamla `api-portal.systembolaget.se` är nedlagd). Vi använder samma sök-API
  som webbplatsen: `api-extern.systembolaget.se/sb-api-ecommerce/v1/productsearch/search` med
  `productLaunch.min`/`productLaunch.max`. Nyckeln ligger öppet i deras JavaScript och letas upp där
  vid varje körning (den ligger inte i repot). Inofficiellt – kan sluta fungera. CORS bara för systembolaget.se.
- Hämtar säljstarter de närmaste 28 dagarna. Ordervaror (`BS`) hoppas över – de har "säljstart" nästan varje dag.
- `productLaunchDate` är svensk dag (släppen öppnar kl 10). Obs: startsidan på systembolaget.se visar
  datumen en dag för tidigt (tidszonsfel i deras serverrendering) – API:et har rätt.
- [fetch/sources/systembolaget.py](fetch/sources/systembolaget.py) → tabellen `systembolaget` (en rad per
  produkt), som ersätts helt vid varje hämtning. Kortet grupperar per dag och sortiment och räknar per kategori.

## Verktyg
Hopfällt kort längst ner med en flik per verktyg (öppet/stängt, vald flik och ifyllda lånevärden sparas
i webbläsaren). Allt räknas i webbläsaren, inget hämtas.
- **Löptempo:** fyll i två av distans, tid och tempo/hastighet så räknas resten ut. Ändrar man något räknas
  ett tomt eller uträknat fält om; har man själv fyllt i både distans och tid ändras tiden (distansen behålls).
  Koden ligger i `startaTempo()` i [index.html](index.html).
- **Ränta:** överst styrräntan (senaste ändring), nästa räntebesked och Riksbankens senaste penningpolitiska
  pressmeddelanden. Sedan räknaren: lån och ränta → räntekostnad per månad och år, och efter ränteavdrag (30 % på upp till
  100 000 kr ränta per år och person, 21 % därutöver – `RANTEAVDRAG` i [index.html](index.html)).
  Bara ränta, ingen amortering. Koden ligger i `startaRanta()`.
- **Lön:** månadslön, kommun, trossamfund (inte medlem / Svenska kyrkan med församling / annat med egen
  avgift) och ålder → lön efter skatt, skatt, marginalskatt och avstånd till brytpunkten för statlig skatt.
  Hämtas direkt från Skatteverkets öppna data (CORS tillåtet, först när fliken visas):
  - Skattesatser per församling: rowstore `c67b320b-ffee-4876-b073-dd9236cd2a99` (kommunal-, region-,
    begravnings- och kyrkoavgift). Saknas årets satser används förra årets.
  - Skattetabeller: rowstore `88320397-5c32-4c16-ae79-d36d95b17b95`. Skattesatsen avrundas till närmaste hela
    procent (tabell 29–42); kolumn 1 under 66 år, kolumn 3 för 66 år eller äldre. Upp till 80 000 kr/mån
    står skatten i kronor, därovan som procent av lönen.
  - Brytpunkten räknas fram ur tabellen (där marginalskatten hoppar 20 procentenheter), så inget hårdkodas.
  Koden ligger i `startaLon()`.
- **Inflation:** belopp, från år och till år/i dag → motsvarande belopp, prisökning och snitt per år.
  KPI per månad (juli 1914 = 100) från SCB:s tabell `KPILevindexM`, hämtas när fliken visas. Årtal räknas som
  årets snitt, "i dag" som senaste månaden. Anropet skickas som `text/plain` så att ingen CORS-förfrågan behövs.
  Koden ligger i `startaInflation()`.

## Lägga till en källa
- **Restaurang:** ny modul i `fetch/sources/` med `hamta()` som returnerar samma form som
  `lunch_battre.py`, och lägg till den i `LUNCHKALLOR` i [fetch/main.py](fetch/main.py).
- **Nyhetsflöde:** en rad i `FLODEN` i [fetch/sources/nyheter.py](fetch/sources/nyheter.py) med ämne `"nyheter"` eller `"ai"`.
  Filterknappen på sidan dyker upp av sig själv.
- **Index:** en rad i `INDEX` i [fetch/sources/bors.py](fetch/sources/bors.py), och symbolen i
  `ordning` i `visaBors()` i [index.html](index.html) för att bestämma plats
  (och i `visning` om den behöver enhet eller decimaler).
- **Temadag:** en rad i `TEMADAGAR` i [index.html](index.html).
- **SL-hållplats:** en rad i `HALLPLATSER` i [index.html](index.html). Valfritt `linjer: ["40", "41"]`
  och `riktning: 1` eller `2` för att bara visa vissa linjer eller ena hållet.
