# AHK Beach – Alingsås HK på Åhus Beach Handboll

Installerbara matchscheman (PWA) för **hela Alingsås HK** under Åhus Beach
Handboll – **en app per åldersgrupp** (U8–U18). Allt hostas gratis på GitHub
Pages och uppdateras automatiskt av en robot i GitHubs moln som hämtar från
cupmanager – ingen dator behöver köra något manuellt.

**Live:** https://martinwelen.github.io/ahk-beach/  (hubb → välj åldersgrupp)

> **U15 (P15+F15)** byggs numera av det här repot men **publiceras till sitt gamla
> repo** `alingsas-ahus-beach-2026`
> (https://martinwelen.github.io/alingsas-ahus-beach-2026/) så att redan
> installerade hemskärms-appar behåller sin URL. Se *U15-publicering* nedan.

---

## Vad som ingår

| Del | Beskrivning |
|-----|-------------|
| **Hubb** (`index.html`) | Startsida som listar alla åldersgrupps-appar. U15 länkar till sitt live-repo (oförändrad URL). |
| **Appar** (`u8/ … u18/` + U15) | En installerbar PWA per åldersgrupp. Flikar: **Schema**, för Classic **Tabeller** + **Slutspel** (A/B/C-träd), **Trupp** (om truppdata finns), och **Karta** (zoombar områdeskarta). Egen ikon/identitet, fungerar offline. |
| **Schema-detaljer** | Alla matcher i tidsordning, multi-"härnäst" (alla live / alla samtidigt-nästa), filter per kön/lag, **livescore** och **videolänk** (se nedan). |
| **Kalendrar** (`uXX/ics/`) | En `.ics` per lag + en samlad per åldersgrupp. Prenumereras på. |
| **Besöksstatistik** | Cloudflare Web Analytics (cookielöst, ingen samtyckesruta) på hubb + alla appar. |

Klubben har **43 lag i ~10 åldersgrupper**. Varje åldersgrupp spelar sina egna
2 dagar någon gång under 9–18 juli 2026 (P och F i samma ålder samma dagar).

---

## Arkitektur / dataflöde

Hela datalagret drivs av **klubbkoden** `NameClub({id:73383031})` – inga
hårdkodade lag-id. Lägg till/ta bort lag i cupmanager → roboten plockar upp det
automatiskt.

```
cupmanager (publikt API, tournamentId 70944382)
        │  fetch_data.py   (klubbkod 73383031; per match: id + video-URL för bana 1–2)
        ▼
   data.json              ← lag + matcher per åldersgrupp (skrivs bara när hash ändras)
        │  fetch_standings.py
        ▼
   standings.json         ← tabeller/slutspel per åldersgrupp (Mini saknar tabeller)
        │
        ├── build_apps.py  → uXX/index.html (+manifest/sw/ikoner/karta.png); U15 → dist-u15/
        ├── build_ics.py   → uXX/ics/*.ics; U15 → dist-u15/ics/ med gamla filnamn
        └── build_hub.py   → index.html (hubben)

build_all.py                  = kör hela kedjan i ordning
.github/workflows/update.yml  → kör allt i molnet, committar bara när data ändrats
scripts/deploy_u15.sh         → publicerar dist-u15/ till repot alingsas-ahus-beach-2026
```

**Livescore** och **karta-zoom** körs helt **klient-sida** i webbläsaren – inget
robotberoende (se nedan).

### Moduler

| Fil | Ansvar |
|-----|--------|
| `config.py` | Konstanter: `TOURNAMENT_ID`, `CLUB_ID`, `API_HOST`, `PAGES_BASE`, U15-konstanter, färgpalett. **Byt `TOURNAMENT_ID` nästa år → allt funkar igen.** |
| `derive.py` | Rena härledningar: `slugify`, `parse_category`, `derive_group_colors`. |
| `rules.py` | `rule_profile` per regeltyp: Classic = fullt; **Mini = schema bara**. |
| `api.py` | cupmanager-klient: entitetshjälpare + sidad hämtning (`fetch_store`). |
| `fetch_data.py` | Klubbkodsdriven hämtning → `data.json`. Per match: `id` (för livescore-poll) och `video` (solidsport-URL, bara bana 1–2). Hash-vaktad – **hashen inkluderar `id`+`video`** så nya fält faktiskt skrivs om. |
| `fetch_standings.py` | Grupptabeller + A/B/C-slutspelsträd → `standings.json`, hash-vaktad. |
| `roster_data.py` | Statiska spelartrupper per lag (cupmanager saknar spelardata). Keyad på team-slug (`u15-p-bla` …). Bäddas in via `__ROSTERS__`; Trupp-fliken göms tills data finns. |
| `bana_coords.py` | Manuellt uppmätta pixelpositioner per bana (`BANA_PX`) + klubbtält, på `karta.png`. `bana_fractions()`/`klubbtalt_fraction()` → andelar, inbäddade som `BANA_XY`/`KLUBBTALT` för kartmarkörerna. |
| `template.py` | HTML/JS-mallen. Könsfilter, multi-hero, **livescore-poll** (`MatchResult`), **videolänk**, **Karta-flik** (zoombar overlay + **live/nästa-markörer** + klubbtält). `user-scalable=no` + scrollbara flik-/filterrader (mobil). |
| `build_apps.py` | Renderar en PWA per åldersgrupp (unik manifest + SW-cache `ahk-uXX-v1`, kopierar `karta.png` + AHK-loggan). Bäddar in match-`id`/`video`, trupper, `BANA_XY`, `API_HOST`/`TOURNAMENT_ID`. **U15 byggs till `dist-u15/`** med extern og-bas. |
| `build_ics.py` | Per-lag-kalendrar. U15 → `dist-u15/ics/` med de gamla `alingsas-*.ics`-filnamnen (bevarar prenumerationer). |
| `build_hub.py` | Hubbsidan. U15-kortet länkar till det externa repots URL. |
| `build_all.py` | Orkestrering (data → standings → appar → ics → hubb). |
| `scripts/deploy_u15.sh` | Publicerar `dist-u15/` till roten av `alingsas-ahus-beach-2026` via SSH deploy key (secret `U15_DEPLOY_KEY`). |

### Livescore & video (klient-sida)

cupmanager-API:t har CORS öppet för `martinwelen.github.io`, så apparna pollar det
direkt från webbläsaren:

- **Livescore:** för varje match i sitt tidsfönster pollas `MatchResult({id})` var
  ~10:e sekund → 🔴 LIVE h–a på kortet. Faller tillbaka på nedräkning (ingen
  live-data) eller slutresultat (klar). Pausar när fliken är dold. Kräver match-`id`
  i `data.json`. Live-inmatning sker bara på vissa banor (1/2/5 …) – därför avgörs
  det per match via `MatchResult.live`, inte via en fast banlista.
- **Video:** matcher på **bana 1 & 2** filmas (solidsport). `fetch_data` resolvar
  `Match($video)` → `externalLink`; kortet får en ▶ Video-länk (scheme-validerad).

**Att ett slutresultat inte får försvinna (två gotchas):**

- **Pollfönstret måste överstiga robotens persistens-latens.** In-memory-`liveState`
  (som visar "Slut h–a" innan roboten hunnit skriva sparat resultat) töms vid refresh.
  Efter reload pollas en match bara medan `now < start + DUR + POLL_GRACE_MS`. Roboten
  kan dröja ~25–30 min med att persista slutresultatet (matchslut + missad cykel +
  CI-körtid), så `POLL_GRACE_MS = 40 min` – annars blir kortet blankt i glappet.
- **Bakgrundsuppdateringen måste kringgå HTTP-cachen.** GitHub Pages serverar
  `sched.json` med `Cache-Control: max-age=600`. `refreshData` hämtar därför med
  `{cache:"no-store"}`; annars kan en inaktuell (cachead) `sched.json` skriva över ett
  redan visat resultat tills cachen löper ut (~10 min). Offline-fallbacken är
  oförändrad – service workern lägger ändå kopian i CacheStorage (no-store rör bara
  HTTP-cachen).

### Karta

`karta.png` (arrangörens områdeskarta) bäddas in i varje app och kopieras per
app-katalog. Karta-fliken visar den; tryck öppnar ett helskärms-overlay med
nyp-zoom + panorering (vanilla Pointer Events, ingen lib).

**Markörer** visar var Alingsås spelar: 🔴 pågående (`state==="live"`) och 🟠 nästa
(alla som delar tidigaste kommande starttid) på rätt bana. Positionerna kommer från
`bana_coords.py` (manuellt uppmätta pixlar per bana → andelar, inbäddade som
`BANA_XY`). En **klubbtält-markör** (AHK-loggan) är alltid synlig. Markörerna finns
i både flik-kartan och helskärm; i helskärm ligger de i en gemensam "stage" med
bilden så de **följer med zoom/panorering**. Tryck på en markör (i helskärm) →
info-panel med klass + lag + bana + tid (+ livescore om live); tältet → "Klubbtält".
Respekterar det aktiva schema-filtret. Uppdateras via `mapMarkers()` vid render (30 s)
och bakgrundsrefresh (60 s).

### U15-publicering

U15 byggs av det här repot (`dist-u15/`) men publiceras till det **gamla** repot
`alingsas-ahus-beach-2026` så installerade appar behåller sin URL. PWA-identiteten
är relativ (`start_url:"."`, `scope:"./"`), så samma-URL-utbyte uppdaterar
installerade appar sömlöst. Deploy sker i CI via `scripts/deploy_u15.sh`. Det gamla
repots egen robot är avstängd. **Gotcha:** CacheStorage är origin-delad – en app:s
service worker får bara radera sin egen `LEGACY`-cache, aldrig syskonappars.

### Färgregel (per åldersgrupp)

1. **Ett enda lag** i gruppen → **blå** (klubbens standardfärg).
2. **Alla lag har färgsuffix** (Blå/Vit/Svart/Orange/Gul/Röd…) → respektive färg.
3. **Annars** (siffer- eller blandade suffix) → palett per index.

### Regeltyper (matchtid & format)

Classic *och* Mini kör **2×5 min + 60 s paus = 11 min**, 1 poäng per mål. Mini har
inga tabeller/slutspel. Internationella set-baserade regler känns igen men
renderaren är en förberedd söm.

---

## Drift & underhåll

- **Bygg lokalt:** `python3 build_all.py` (kräver bara Python 3, inga beroenden).
- **Tester:** `python3 -m pytest` (offline; live-hämtningarna körs av skripten).
- **Robot:** `.github/workflows/update.yml` kör var 30:e min (var 10:e under 9–18
  juli, triggat av homelab CT 130) och committar bara när `data.json`/`standings.json`
  ändrats. Pushen är **race-härdad** (pull --rebase + retry).
- **Deploya en kod-/trupp-/mall-ändring (viktigt):** roboten bygger bara om vid
  *dataändring*, så kodändringar deployas inte av sig själva under stiltje. Tvinga
  fram det: **`gh workflow run "Uppdatera schema" -f force=true`** → bygger om allt,
  committar och kör U15-deployen oavsett datan. Använd detta för att se en ändring
  live före matchdag.
- **Spelartrupper:** redigera `roster_data.py` (keyad på team-slug), sen force-run.
- **GitHub Pages:** branch `main`, rot. `.nojekyll` hindrar Jekyll.

### Nästa år
Byt `TOURNAMENT_ID` i `config.py`. Allt annat (åldersgrupper, lag, färger,
slutspel) upptäcks automatiskt från klubbkoden.

---

## Designdokument

Spec och implementationsplaner ligger i `docs/superpowers/`:
- `specs/2026-07-12-u15-in-i-delad-pipeline-design.md` + plan
- `specs/2026-07-12-omradeskarta-flik-design.md` + plan
- `specs/2026-07-14-livescore-och-video-design.md` + plan

Äldre specar (evergreen-design, datalager, bygge/hubb, CI) ligger i U15-repot.
