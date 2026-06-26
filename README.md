# AHK Beach – Alingsås HK på Åhus Beach Handboll

Installerbara matchscheman (PWA) för **hela Alingsås HK** under Åhus Beach
Handboll – **en app per åldersgrupp** (U8–U18). Allt hostas gratis på GitHub
Pages och uppdateras automatiskt av en robot i GitHubs moln som hämtar från
cupmanager – ingen dator behöver köra något manuellt.

**Live:** https://martinwelen.github.io/ahk-beach/  (hubb → välj åldersgrupp)

> **U15 (P15+F15) bor i ett separat repo:** `alingsas-ahus-beach-2026`
> (https://martinwelen.github.io/alingsas-ahus-beach-2026/). Det repot rördes
> aldrig när det här byggdes – den redan distribuerade U15-appen är orörd.
> Hubben här länkar till U15-appens befintliga URL.

---

## Vad som ingår

| Del | Beskrivning |
|-----|-------------|
| **Hubb** (`index.html`) | Startsida som listar alla åldersgrupps-appar. U15 länkar till live-repot. |
| **9 appar** (`u8/ … u18/`, utom u15) | En installerbar PWA per åldersgrupp. Flikar: **Schema** (alla matcher i tidsordning, "härnäst", filter per kön/lag) och – för Classic – **Tabeller** + **Slutspel** (A/B/C-träd). Egen ikon/identitet, fungerar offline. |
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
        │  fetch_data.py      (filtrerar på klubbkod 73383031, partitionerar per åldersgrupp)
        ▼
   data.json                  ← lag + matcher per åldersgrupp (skrivs bara vid ändring)
        │  fetch_standings.py  (grupptabeller + A/B/C-slutspel, bucketat per åldersgrupp)
        ▼
   standings.json             ← tabeller/slutspel per åldersgrupp (Mini saknar tabeller)
        │
        ├── build_apps.py  → uXX/index.html, manifest.json, sw.js, ikoner  (en PWA per åldersgrupp)
        ├── build_ics.py   → uXX/ics/*.ics
        └── build_hub.py   → index.html (hubben)

build_all.py                  = kör hela kedjan ovan i ordning
.github/workflows/update.yml  → kör allt i molnet (cron + manuellt), committar
                                bara när data.json/standings.json ändrats
```

### Moduler

| Fil | Ansvar |
|-----|--------|
| `config.py` | Konstanter: `TOURNAMENT_ID`, `CLUB_ID`, `API_HOST`, `PAGES_BASE`, färgpalett/-karta, klubbblå. **Byt `TOURNAMENT_ID` nästa år → allt funkar igen.** |
| `derive.py` | Rena härledningar: `slugify`, `parse_category` (kategorinamn → kön/ålder/regel/suffix), `derive_group_colors` (färgregeln). |
| `rules.py` | `rule_profile` per regeltyp: Classic = fullt; **Mini = schema bara** (inga tabeller/slutspel/resultat); okänt/internationellt → fullt (förberedd söm). |
| `api.py` | cupmanager-klient: entitetshjälpare (`ref_id`, `name_of`, `store_get`) + sidad hämtning (`fetch_store`, paging-tak). |
| `fetch_data.py` | Klubbkodsdriven hämtning → `data.json` (lagregister + normaliserade matcher per åldersgrupp), hash-vaktad. |
| `fetch_standings.py` | Grupptabeller + A/B/C-slutspelsträd per åldersgrupp → `standings.json`, hash-vaktad. Speglar API:ts tabellordning. |
| `template.py` | HTML/JS-mallen (kopierad + parametriserad från live `build_site.py`). Dynamiskt könsfilter via `__CLASSES__`, per-app `__APPLABEL__`/`__CACHE__`. |
| `build_apps.py` | Renderar en PWA per åldersgrupp: unik manifest-identitet + unikt SW-cache-namn (`ahk-uXX-v1`), färger utan `#`, Mini döljer resultat. Hoppar över u15. |
| `build_ics.py` | Per-lag-kalendrar per åldersgrupp. |
| `build_hub.py` | Hubbsidan. U15 → live-repots URL. |
| `build_all.py` | Orkestrering (data → standings → appar → ics → hubb). |

### Färgregel (per åldersgrupp)

1. **Ett enda lag** i gruppen → **blå** (klubbens standardfärg).
2. **Alla lag har färgsuffix** (Blå/Vit/Svart/Orange/Gul/Röd…) → respektive färg.
3. **Annars** (siffer- eller blandade suffix) → palett per index.

> Känd nyans: i en P+F-app får t.ex. P-Blå och F-Blå *samma* blå färg (regeln
> mappar "Blå"→blå oavsett kön). Könsfiltret skiljer dem ändå.

### Regeltyper (matchtid & format)

Classic *och* Mini kör **2×5 min + 60 s paus = 11 min**, 1 poäng per mål
(arrangörens regler). Mini har inga tabeller/slutspel. Internationella
set-baserade regler (2 set + shootout) finns i turneringen för andra klubbar men
inte för Alingsås 2026 – datalagret känner igen formatet men renderaren är en
förberedd söm (byggs när det behövs).

---

## Drift & underhåll

- **Bygg lokalt:** `python3 build_all.py` (kräver bara Python 3, inga beroenden).
- **Tester:** `python3 -m pytest` (offline; live-hämtningarna körs av skripten, inte testerna).
- **Robot:** `.github/workflows/update.yml` kör var 30:e minut (var 10:e under
  9–18 juli) och committar/pushar bara när `data.json`/`standings.json` ändrats.
  En mall-/kodändring plockas **inte** upp av roboten – bygg om och pusha manuellt.
- **GitHub Pages:** branch `main`, rot. `.nojekyll` hindrar Jekyll-processning.
- **Lägg till spelartrupper:** finns inte här ännu (fanns i U15-repot). Truppfliken
  döljs automatiskt tills truppdata finns.

### Nästa år
Byt `TOURNAMENT_ID` i `config.py` till nästa turnerings-id. Allt annat
(åldersgrupper, lag, färger, slutspel) upptäcks automatiskt från klubbkoden.

---

## Designdokument

Spec och implementationsplaner ligger i U15-repot (`alingsas-ahus-beach-2026`)
under `docs/superpowers/`:
- `specs/2026-06-26-klubbapp-evergreen-design.md`
- `plans/2026-06-26-ahk-beach-data-layer.md` (Plan 1)
- `plans/2026-06-26-ahk-beach-build-and-hub.md` (Plan 2)
- `plans/2026-06-26-ahk-beach-ci-and-deploy.md` (Plan 3)
