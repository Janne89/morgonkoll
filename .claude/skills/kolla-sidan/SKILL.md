---
name: kolla-sidan
description: Öppna Morgonkoll i webbläsaren med Playwright-MCP:n och kontrollera att alla kort laddar – felmeddelanden, kort som fastnat på "Hämtar…", konsol- och nätverksfel, mobilbredd och mörkt läge. Använd efter ändringar i index.html, när ett kort ser trasigt ut, eller när användaren ber om en skärmdump eller en koll av live-sidan.
---

# Kolla sidan

Sidan är en enda `index.html` med 13 kort (`<section class="kort" id="…">`). Varje kort har
`#<id>-innehall` (startar som "Hämtar …"), visar fel som `<span class="fel">Kunde inte hämta …</span>`
och har en tidsstämpel i `#<id>-tid`.

## 1. Välj vilken sida

- **Live:** `https://janne89.github.io/morgonkoll/` – för "är något trasigt just nu?".
- **Lokalt:** för ändringar som inte är pushade. Playwright blockerar `file://`, så starta en server
  i bakgrunden (`run_in_background`) från repots rot:
  `python -m http.server 8765 --bind 127.0.0.1` och öppna `http://127.0.0.1:8765/`.
  Stoppa servern när du är klar.

## 2. Ladda och vänta

`browser_navigate` till sidan, sedan `browser_wait_for` med texten `Hämtar` borta (eller vänta ~8 s –
några kort hämtar från långsamma API:er). Kör sedan detta med `browser_evaluate`:

```js
() => [...document.querySelectorAll("section.kort")].map(k => {
  const inne = k.querySelector(`#${k.id}-innehall`) ?? k;
  return {
    kort: k.id,
    fastnat: /^\s*Hämtar/.test(inne.textContent),
    fel: [...k.querySelectorAll(".fel")].map(e => e.textContent.trim()),
    tid: k.querySelector(`#${k.id}-tid`)?.textContent.trim() ?? "",
  };
})
```

Hämta även `browser_console_messages` (fel och varningar) och `browser_network_requests`
(leta efter 4xx/5xx och CORS-fel).

## 3. Visuellt

- `browser_take_screenshot` med `fullPage: true` i normal bredd.
- `browser_resize` till 390×844 och ta en till – mobilregeln är `@media (max-width: 480px)`.
- Mörkt läge följer `prefers-color-scheme`. Kontrollera vid behov med
  `browser_evaluate` att text och bakgrund går att läsa, eller be användaren byta systemtema.

## 4. Rapportera

En kort tabell: kort · status (ok / fel / fastnat) · orsak. Skilj på:

- **Webbläsarkällor** (väder, elpris, SL, sport, polymarket, priser, namnsdag) – felet syns i
  konsolen/nätverket; ofta ett ändrat eller nere API.
- **Supabase-källor** (nyheter, trender, börs, lunch, systembolaget, evenemang, SHL, Riksbanken) – tom
  eller gammal data betyder att jobbet inte startats eller fallerat. Kolla
  `gh run list --workflow=hamta.yml --limit 5` och `gh run view <id> --log-failed`. Saknas körningar:
  Supabase pg_cron startar dem, så kolla `net._http_response` (ska vara 204; 401 = GitHub-token i
  Vault har gått ut) och `cron.job_run_details` med Supabase-MCP:n – se `supabase/hamtning.sql`.

ESPN svarar 403 utan CORS-huvud till webbläsare som säger "HeadlessChrome". Därför sätter
`.mcp.json` en vanlig `--user-agent`. Ser du CORS-fel mot `site.api.espn.com`, jämför först med
`curl -H "Origin: https://janne89.github.io" <url>` innan du kallar det ett fel på sidan.

Gammal tidsstämpel är bara ett fel om den är äldre än schemat i README:n tillåter
(t.ex. lunch hämtas bara vardagsmorgnar, evenemang bara på morgnarna).
