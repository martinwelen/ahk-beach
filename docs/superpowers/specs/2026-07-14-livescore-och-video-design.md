# Design: livescore + videolänk i apparna

**Datum:** 2026-07-14
**Status:** Godkänd design, redo för implementationsplan

## Bakgrund

cupmanager-API:t (`ahusbeachhandboll.cupmanager.net/rest/results_api`) exponerar
två saker vi idag inte använder:

1. **Video** – varje match har en `video`-referens som, när den resolvas, ger en
   `Video`-entitet med `externalLink` (en titta-URL på **solidsport.com**),
   `thumbnail` och `provider`. Verifierat: **bara matcher på Bana 1 & 2 filmas**
   (resolvar till en Video), alla andra banor ger tomt.
2. **Livescore** – `MatchResult({id})` returnerar `homeGoals`, `awayGoals`,
   `live` (bool), `finished` (bool), uppdaterad löpande under en live-scoutad
   match. Live-inmatning sker på minst bana 1, 2 och 5 – **inte en fast banlista**,
   så det avgörs bäst i realtid via `live`-flaggan per match.

**CORS:** API:t svarar `access-control-allow-origin` för `martinwelen.github.io`
(preflight `*`). Alltså kan appen **polla direkt från webbläsaren** – ingen
server/proxy behövs.

Dagens app: matchkort visar nedräkning eller slutresultat; hero-rutan ("härnäst")
visar **exakt en** match (första live, annars första kommande). Ingen video, ingen
löpande livescore.

## Krav

1. **Videolänk:** matcher på Bana 1 & 2 får en liten play-logga som öppnar
   solidsport-URL:en i ny flik.
2. **Livescore:** en pågående, live-scoutad match visar löpande ställning
   ("🔴 LIVE 10–8") på sitt kort i schemat; faller tillbaka på nedräkning där
   live-data saknas, och på slutresultat när matchen är klar.
3. **Multi-hero:** toppen visar **alla** relevanta matcher samtidigt, inte en:
   - alla matcher i `live`-tillstånd, annars
   - alla kommande matcher som delar den **tidigaste** starttiden.
   Måste hantera ett **godtyckligt antal** samtidiga (3 P15 + 3 F15 kan krocka, och
   fler klasser/lag kan spela samtidigt – ingen fast övre gräns). Layouten ska
   **degradera snyggt**: ett kort = stor hero-ruta (som idag), flera = **kompakta
   staplade rader** så toppen förblir skannbar och inte trycker ner schemat.
4. Inga nya körtidsberoenden (vanilla JS/CSS). Får inte bryta befintliga vyer.

## Arkitektur

Tre delar som hakar in i befintlig pipeline:

### A. Datalager (`fetch_data.py`) – bygg-tid, via roboten
- Lägg **`id`** (cupmanagers numeriska match-id, redan i store som `m['id']`) på
  varje match i `data.json`. Krävs för klientens poll.
- För Alingsås-matcher på **bana 1 & 2**: resolva `Match({id})$video` och spara
  `video` = `externalLink` (annars utelämnat/`null`). Litet urval → billigt.
  Videolänkar dyker upp när matchen filmats; roboten (var 10:e min) plockar upp dem.

### B. Bygge (`build_apps.py` / `template.py`)
- `_js_matches` skickar med `id` och (ev.) `video` i JS-matchobjekten.
- Bädda in **`API_HOST`** och **`TOURNAMENT_ID`** (från `config.py`) i mallen så
  klienten kan bygga poll-URL:er. Templatas in som nya platshållare.

### C. Klient-JS (mallen) – realtid
- **Video:** om matchen har `video` → play-logga på kortet (öppnar `externalLink`,
  `target="_blank" rel="noopener"`). Endast bana 1–2 (där datan finns).
- **Livescore-poll:** en modul som var **~10:e sekund** pollar `MatchResult({id})`
  för matcher vars tidsfönster är nu (`start ≤ nu ≤ start + längd + buffert`) och
  ej klara. Per svar:
  - `finished:true` → visa slutställning
  - `live:true` → **🔴 LIVE h–a** (badge + löpande siffra), på kortet **och** i hero
  - annars → nedräkning (oförändrat)
- **Multi-hero:** hero blir en **lista** av featured-kort:
  - `liveOnes = rows.filter(live)`; om icke-tom → featured = liveOnes
  - annars: `firstUp = rows.find(up)`; featured = alla `up` med `ms === firstUp.ms`
  - inga → "Alla matcher spelade" (oförändrat)
  - Ett featured → stor hero-ruta (som idag). **Flera featured → kompakta staplade
    rader** (mindre kort), godtyckligt antal, var och en med egen
    nedräkning/livescore/video. Toppen ska aldrig svälla så att schemat trycks bort.

### Poll-URL (verifierad)
```
GET https://{API_HOST}/rest/results_api/call
    ?call=MatchResult({id:<id>})&lang=sv&tournamentId={TOURNAMENT_ID}
```
Svar → `responses[...]["entity"]` med `__typename:"MatchResult"`,
`homeGoals`, `awayGoals`, `live`, `finished`.

## Dataflöde

```
Roboten (var 10:e min):
  fetch_data → data.json (nu med match-id + video-URL + slutresultat) → build_apps → appar

Klienten (medan appen är öppen):
  för varje match i tidsfönster → fetch MatchResult var ~10:e s → uppdatera kort/hero
```

Roboten och klienten är oberoende: roboten ger schema/slutresultat/videolänkar,
klienten ger den löpande siffran mellan robotkörningarna.

## Sparsamhet & felhantering

- Polla **bara** när minst en match är i fönster **och** `document.visibilityState
  === "visible"`. Pausa polling när fliken är dold; återuppta när synlig.
- Sluta polla en match när `finished` eller när fönstret passerats.
- Poll-fel (nät) → behåll senaste kända värde / fall tillbaka på nedräkning, försök
  igen nästa tick. Ingen aggressiv retry.
- ~6 parallella pollar i värsta fall = trivial last (var 10:e s).

## Testning

- **Bygg-nivå (pytest):**
  - `fetch_data` inkluderar `id` per match, och `video` för bana 1–2 (mockat API);
    ingen video för andra banor.
  - `build_apps`/mallen bäddar in `id`/`video` i matchobjekten samt `API_HOST` +
    `TOURNAMENT_ID`.
  - Mallen innehåller poll-modulen och multi-hero-logiken (markörer/strukturkoll).
- **Klient-live-UI:** kan inte enhetstestas i Python-bygget → **manuell verifiering
  i webbläsare mot en live-match** (nästa matchsession): livescore uppdateras,
  multi-hero visar flera samtidiga, video-loggan öppnar solidsport, polling pausar
  när fliken döljs.

## Icke-mål / utanför scope

- Video på andra banor än 1–2 (finns inte i datan).
- Egen inbäddad video-spelare (vi länkar bara till solidsport).
- Server/proxy för polling (CORS gör det onödigt).
- Push-notiser / ljudeffekter (widgeten har ljud; vi gör det inte).
- Målhändelse-flöde / statistik (`MatchFeed`) – bara ställningen `MatchResult`.

## Bygg-ordning (för planen)

1. Datalager: `id` + `video` i `data.json` (trivialt, testbart).
2. Video-loggan på korten (trivialt).
3. Livescore-poll + kort-badge.
4. Multi-hero (bygger på live/next-logiken).
