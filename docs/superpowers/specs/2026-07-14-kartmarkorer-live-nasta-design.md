# Design: markera live/nästa AHK-match på kartan

**Datum:** 2026-07-14
**Status:** Godkänd design, redo för implementationsplan

## Bakgrund

Apparna har en zoombar områdeskarta (Karta-flik + `#mapzoom`-helskärmsoverlay) där
alla banor (1–19) är utritade och numrerade. Appen vet redan, per match, vilken
`bana` matchen spelas på och kan räkna ut live/nästa via `state()` (samma logik som
hero-toppen). Varje app är klubb-filtrerad → **alla matcher är Alingsås-matcher**.

Vi vill visa på kartan **var Alingsås spelar nu** och **var nästa match spelas**.
Detta är *inte* GPS-problemet (som misslyckades pga icke-skalenlig illustration) –
banorna sitter på fasta, utritade positioner, så en statisk pixel-tabell räcker.

## Krav

1. Markera banor där Alingsås har en **pågående** match (🔴 spelas nu) och där
   **nästa** match spelas (🟠 nästa = alla matcher som delar tidigaste kommande
   starttid, som hero-logiken).
2. Markörerna ska synas **både** i flik-kartan och i det **zoombara helskärmsläget**,
   där de **följer med** när man nyper/panorerar (sitter kvar på rätt bana).
3. **Tryck på en markör → info-panel** med **klass** (P14/F14…) + **lagen**
   (hemma–borta), samt tid och livescore om matchen spelas nu.
4. Respektera det aktiva schema-filtret (lag/klass).
5. Ingen ny körtidsdependens (vanilla JS/CSS).

## Arkitektur

### A. Statisk bandata (`bana_coords.py`)
Ny modul: `BANA_XY = {1: [x, y], …, 19: [x, y]}` där `x`/`y` är banans position som
**andel av kartbilden** (0–1, upplösningsoberoende). Lokaliseras en gång mot
`karta.png`. `build_apps` bäddar in den som JS-konstant via platshållaren
`__BANA_XY__` (mönster som `roster_data`/`__ROSTERS__`).

### B. Markör-overlay (template.py)
Ett markör-lager ovanpå kartbilden med absolutpositionerade element vid
`left:x*100% / top:y*100%`. Två typer:
- 🔴 **nu**: pulserande röd prick (`state==="live"`).
- 🟠 **nästa**: orange prick (alla `state==="up"` med `ms === tidigaste up-ms`).

En bana med både live och nästa → live vinner. Okänd bana (saknas i `BANA_XY`) →
hoppas över (defensivt).

### C. Zoom-följning (helskärm)
Idag transformeras `#mapzoom-img` direkt. Vi lindar **bild + markör-lager** i en
gemensam `#mapzoom-stage` och flyttar transformen (nyp/panorera) till stagen. Då
skalas/panoreras markörerna **tillsammans med** bilden och sitter kvar på rätt bana.
Pinch/pan-hanteraren pekas om från img → stage (clamp använder stagens/bildens mått).

### D. Info-panel (tryck på markör)
Markörerna är `<button>`. Tryck → en **skärm-fäst** info-panel (t.ex. fixerad rad i
nederkant av kart-vyn/overlay, **utanför** zoom-transformen så texten inte skalas)
visar: `${klass} · ${hemma} – ${borta}` + tid, och `🔴 LIVE h–a` om matchen spelas
nu (från `liveState`). Tryck på annan markör → byt; tryck utanför/stäng → dölj.

### E. Uppdatering
`mapMarkers()` räknar ut live/nästa bland de filtrerade matcherna och (om)ritar
markörlagret. Körs vid vy-byte till Karta, vid `render()` (30 s) och vid
bakgrundsrefresh (60 s), så markörerna hålls aktuella. En liten teckenförklaring
(🔴 spelas nu · 🟠 nästa) under kartan.

## Dataflöde

```
bana_coords.py (statisk %-tabell)
        │  build_apps → __BANA_XY__
        ▼
   appens JS: const BANA_XY
        │  mapMarkers() (filtrerade MATCHES + state()) → markörlager
        ▼
   karta (inline + helskärm), tryck → info-panel
```

## Felhantering
- Bana saknas i `BANA_XY` → hoppa över den markören.
- Inga live/nästa → inga markörer (ren karta).
- Info-panel stängs vid vy-byte/ommritning om matchen inte längre är relevant.

## Testning
- **Bygg-nivå (pytest):** `bana_coords.BANA_XY` har alla 19 banor med par i [0,1];
  `build_apps` bäddar in `__BANA_XY__` (ingen kvarvarande platshållare); mallen
  innehåller `mapMarkers`, markör-CSS och info-panel-logiken.
- **Manuell webbläsarverifiering:** markörerna hamnar på rätt banor; följer med vid
  zoom/pan i helskärm; tryck visar rätt klass+lag; nu/nästa uppdateras över tid.

## Icke-mål / utanför scope
- Fler markörtyper än nu/nästa.
- Markera andra klubbars matcher.
- "Du är här"/GPS (avfärdat tidigare).
- Ruttdragning/pil till banan.
