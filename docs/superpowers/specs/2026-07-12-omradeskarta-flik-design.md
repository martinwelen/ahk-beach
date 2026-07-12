# Design: zoombar områdeskarta som egen flik

**Datum:** 2026-07-12
**Status:** Godkänd design, redo för implementationsplan

## Bakgrund

Arrangören publicerar en områdeskarta över Åhus Beach Handboll som PNG
(`842×1191 px`, ~468 KB, A3 stående) på
`https://ahusbeach.com/app/uploads/2026/06/Omradeskarta_Handboll-A3-2026_webb.png`.
Klubbens appar (en installerbar PWA per åldersgrupp, byggda av `ahk-beach`) har i
dag flikarna Schema / Tabeller / Slutspel / Trupp men ingen karta. En zoombar
karta hjälper besökare att hitta rätt på arenan.

Apparna är **offline-först** och **helt beroendefria** (ingen JS-lib). Det styr
lösningen.

## Krav

1. Kartan ska finnas i **alla appar** (u8–u18 + U15), eftersom arenan är gemensam.
2. Kartan ska **bäddas in** (offline-kopia), inte hotlänkas.
3. Interaktion: kartan visas i en flik; **tryck öppnar helskärm med nyp-zoom och
   panorering**.
4. Ingen ny körtidsdependens (behåll beroendefri, vanilla JS/CSS).
5. Får inte bryta befintliga vyer/flikar eller live-apparna.

## Arkitektur

Kartan hakar in i mallens befintliga flik-/vy-system (`template.py`):
- Flikknappar togglas i `tabsWrap`; `setView(v)` (kring rad 406) sätter `.hidden`
  per vy-sektion.
- Data-flikar (Tabeller/Slutspel/Trupp) göms tills data finns. **Karta-fliken är
  alltid synlig** — kartan är statisk och gemensam.

### Komponenter

| Del | Ansvar |
|-----|--------|
| Karta-flik | `<button class="tab" id="tab-karta" data-view="karta">Karta</button>` i flikraden, **utan** `hidden`. |
| Kartvy | `<section id="map" hidden>` med `<img>` (full bredd), hint "Tryck för helskärm", samt diskret "Källa: ahusbeach.com". |
| `setView`-utökning | Lägg `elMap.hidden = v!=="karta"` och se till att hero/list göms när `v==="karta"`. |
| Helskärms-overlay | `<div id="mapzoom" hidden>` — fixed, täcker viewporten, mörk bakgrund, stäng-knapp. Innehåller kartbilden. |
| Nyp/panorera-hanterare | Liten vanilla-JS med Pointer Events: 2 fingrar = zooma (skala kring mittpunkt), 1 finger = panorera, dubbeltryck = återställ, tryck utanför / stäng-knapp / Esc = stäng. `touch-action: none` på overlay. Skala klampas (t.ex. 1–6×). |
| `karta.png` | Statisk bild i repo-roten, kopieras in i varje app-katalog av `build_apps.py` (samma mekanik som ikonerna). |

### Dataflöde / bygge

1. `karta.png` läggs i repo-roten (nedladdad från arrangörens URL, en gång).
2. `build_apps.py` kopierar `karta.png` till varje app-katalog (u8–u18 samt
   `dist-u15/`), på samma sätt som `_ICONS` redan kopieras.
3. Service workern (nätverk-först, cache-vid-hämtning) cachar `karta.png` vid
   första visning online → tillgänglig offline därefter. Ingen precache behövs
   (konsekvent med hur appen redan cachar allt annat).

## Varför lite egen zoom-JS (och inte "native")

Appens viewport tillåter sid-zoom (`initial-scale=1`, ingen `user-scalable=no`),
men äkta **element**-nyp-zoom är inte pålitlig cross-browser utan egen kod, och
att förlita sig på sid-zoom för ett overlay blir hackigt. En liten självständig
Pointer-Events-hanterare (~50–70 rader) ger en nativt kännande gest, fungerar på
iOS/Android/desktop och håller appen beroendefri. Detta är den enda nya JS-logiken.

## Testning

- **Bygg-nivå (Python/pytest):** `build_apps` kopierar `karta.png` till varje
  byggd app-katalog och till `dist-u15/`; mallen innehåller Karta-fliken och
  `#map`/`#mapzoom`-sektionerna.
- **Interaktion (zoom-gest):** kan inte enhetstestas i det Python-baserade
  bygget → verifieras manuellt i webbläsare/mobil (via `/run` eller på enhet).

## Icke-mål / utanför scope

- **AR-vy** med riktningspil mot arenapunkter (kamera/kompass/GPS). Tekniskt
  oproportionerligt (dåligt/inget stöd i iOS Safari, tillståndsfriktion,
  kalibrering) och bryter offline/beroendefri-filosofin. Uttryckligt icke-mål.
- **"Du är här"-markör** inritad på kartan — möjlig framtida pyttenick, byggs inte
  nu (YAGNI).
- Bild-optimering/omkodning av kartan (468 KB är acceptabelt).
