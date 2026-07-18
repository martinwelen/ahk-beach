# Inför post mortem — Åhus Beach Handboll 2026

> Samlingsdokument så inget glöms. Post mortem körs **efter turneringens sista dag
> (lördag 18 juli 2026)**. Lägg till nya noteringar löpande under *Löpande noteringar*.
>
> Två spår att hålla isär:
> 1. **Generalisera `ahk-beach`** till en mall för andra cupmanager-cuper (snabb utrullning).
> 2. **Cuptide** — det från-grunden-byggda systemet (eget repo `/home/martin/dev/cuptide/`),
>    separat och långsiktigt.

---

## 1. Vad som funkade (behåll)

- **Uppskattat live:** deltagare och besökande föräldrar gillade lösningen; funkade
  skitbra hela veckan.
- **Livescore slog cupmanagers egen** i snabbhet (klient pollar `MatchResult` direkt).
- **Offline-först installerbar PWA** — fungerade även med skral täckning på arenan.
- **Karta med "var spelar vi nu/härnäst"** + klubbtält — en tydlig differentiator.
- **Klubbkodsdriven data** (inga hårdkodade lag-id) → nästa turnering byts med ett id.
- **U15 kvar på gammal URL** via cross-repo-publicering (installerade hemskärms-appar
  behöll sin länk).
- **Deploy-/verifieringsdisciplin** höll även skarpt läge (se avsnitt 4).

---

## 2. UX-backlog (observerat live — att åtgärda efter turneringen)

Allt nedan ligger i den **delade `template.py`** → hög risk (en bugg slår mot alla
appar). Verifiera i webbläsare, inte bara pytest-substrängar.

1. **Slutspelsträdet blir lite missaligned** — bracket-layouten (`renderBracket` + CSS)
   linjerar inte rundorna/matcherna snyggt.
2. **Bana + tid saknas i slutspelsträdet** — varje match i trädet borde visa bana och
   tid (datan finns redan per match: `bana`, `t`/`ms`).
3. **Klass saknas i filterchipsen** — chipsen (P15, F15 …) visar lagnamn men inte klass,
   och färgnamnen krockar: "AHK Blå" och "Vit" finns i BÅDE P15 och F15 → tvetydigt.
   Lägg klassen bredvid laget i chipet.
4. **Flikraden bör låsas från scroll som filterraden** — filterraden är sticky/pinnad;
   `.tabs` borde bete sig likadant. *Att bekräfta i post mortem:* menas pinnad vertikalt,
   eller att den horisontella scrollen ska bort?
5. **Hoppa-till-"nu"** — i ett långt schema måste man skrolla långt sent i turneringen.
   Vill ha autoscroll till pågående/närmaste match, eller en "Nu"-knapp som scrollar dit.
6. **Separat matchvy (klicka på en match)** — egen vy som öppnas när man klickar på en
   match, med: lagens turneringsstatistik (t.ex. mål för/mot, form, tabellposition) och
   **hela matchens historik mål för mål** (löpande måltavla/tidslinje). Mål-för-mål bör
   åtminstone finnas för **liverapporterade matcher** (samma källa som livescoren matas
   av). *Kräver koll:* exponerar cupmanager-API:t mål-för-mål-händelser och lag-
   turneringsstatistik? (Idag hämtar vi bara `MatchResult` med slutsiffror.) → se
   API-koll nedan. Generaliserbar cup-funktion, inte Åhus-specifik.

*Kandidater att göra generiska/config i ett mall-repo:* punkt 3 (visa klass), punkt 5
(hoppa till nu) och punkt 6 (matchvy) är generella cup-behov, inte Åhus-specifika.

### API-koll för matchvyn (verifierat live 2026-07-18)

Allt matchvyn behöver finns i cupmanager-API:t. Probat mot en liverapporterad
bana 1/2-match (icke-Alingsås, 12–10). Match-entiteten har bl.a. refsen: `matchStats`,
`previousMeetings`, `feed`, `matchStats`, `referees`, `protests`, `roundName`,
`editionRanking`, `roundRank`, `matchNr`, `stage`, `winner`/`loser`,
`nextMatchWinner`/`nextMatchLoser`.

- **Lag-turneringsstatistik:** `matchStats` → `MatchCache$MatchStatistics` =
  `home/awayMadeGoals`, `…LostGoals`, `…Won/Lost/Tied/Played`. ✓
- **Mål-för-mål + matchstatistik:** `MatchFeed({id:<mid>})` →
  - `statistics` → `MatchFeed$EventStatistics` per lag: `shots, goals, lost, saves,
    redCards, yellowCards, greenCards, penaltiesCount/Minutes, one/two/threePointers`
    (sport-agnostiskt), `timeouts, fouls_*, rebounds, steals, formGuide`. ✓
  - `events` → mål-för-mål-tidslinje. Fältet finns; `$events` resolvade inte i snabb-
    anropet (troligen pagerad/lat) → **exakt form återstår att nagla i implementationen.**
- **Inbördes-historik:** `previousMeetings` (lista). ✓
- **`MatchResult`** (redan använt för livescore) bär även `periodScores`, `homePoints`/
  `awayPoints`, `walkover`, `penalties`, `homeSetsWon` — mer än vi visar idag.
- **CORS:** `MatchResult` är verifierat öppet för klientpoll; **kolla CORS för
  `MatchFeed`/`matchStats`** innan klient-sida-hämtning (annars via roboten).

Slutsats: matchvyn (punkt 6) är fullt genomförbar på befintlig datakälla; mål-för-mål
finns för liverapporterade matcher.

---

## 3. Tekniska lärdomar / buggar vi fixade (dissekera i post mortem)

- **TDZ-krasch:** `const liveState` användes av `render()` innan deklaration → hela
  appen dog vid load. Pytest-substrängtester fångade det INTE; hittades via
  node-repro/webbläsare. → *Lärdom: verifiera app-runtime, inte bara att strängar finns.*
- **Hash-vakt-bugg:** `data.json` skrevs aldrig om i produktion för nya fält (id/video)
  eftersom hashen inte inkluderade dem → livescore saknade match-id. → *Lärdom: hashen
  måste täcka allt som ska trigga omskrivning.*
- **Resultat försvann vid refresh — två grundorsaker:**
  (a) bakgrundsuppdateringen läste `sched.json` via HTTP-cachen (Pages `max-age=600`) →
  inaktuell kopia skrev över ett visat resultat → fix `{cache:"no-store"}`.
  (b) livescore-pollfönstret stängde vid start+21min < robotens persistens-latens
  (~25–30 min) → fix `POLL_GRACE_MS = 40 min`.
- **Deploy-race:** CI auto-committar var ~10:e min och kolliderade med manuella pushar →
  race-härdad push (pull --rebase + retry).
- **Concurrency-cancel:** snabba force-runs efter varandra avbröt varandras *väntande*
  körningar (GitHub `cancel-in-progress: false` avbryter äldre pending) → *en deploy i
  taget; vänta tills kön är tom.*
- **CDN gav falska "saknas"-utslag:** Pages OCH `raw.githubusercontent` är CDN-cachade
  ~5–10 min → verifiera mot auktoritativ källa (GitHub contents-API), inte cachad URL.
- **GPS-"du är här" övergavs** — LOO-residualer ~27–67 m, för dåligt (hav/banor delar
  blått). Manuellt uppmätta banpositioner istället.
- **Premature "fixat":** ett fel förklarades löst utan att spåra hela dataflödet →
  *verifiera live innan man säger fixat.*

---

## 4. Deploy-/verifieringsdisciplin som höll (formalisera)

1. Root-cause först; minsta möjliga diff; rör inte orelaterat.
2. Full `pytest` grön + lokal `build_all.py` + (för template) kör appen i webbläsare.
3. Rebase mot origin/main före push (CI-race).
4. Deploy via `gh workflow run "Uppdatera schema" -f force=true` — **en i taget**.
5. Verifiera på auktoritativ deployad källa för BÅDE huvudappen och externa U15-repot.
6. Rollback redo: `git revert` + push + force-run.
7. Roster-ändring: committa ENDAST `roster_data.py` (`git checkout -- .` för resten).

---

## 5. Generalisering till andra cupmanager-cuper

**Redan parametriserat:** `config.py` (`TOURNAMENT_ID`, `CLUB_ID`, `API_HOST`,
`PAGES_BASE`); klubbkodsdriven datahämtning (auto-upptäcker åldersgrupper/lag/färger/
slutspel).

**Troliga anpassningspunkter per cup (att göra till config/mall):**
- Turnerings-/klubb-id.
- Branding: färgpalett, logga, appnamn, og-bilder, analytics-token.
- Områdeskarta + banpositioner (`bana_coords.py`, `karta.png`) — mest cup-specifikt.
- Truppdata (`roster_data.py`) — valfritt.
- Deploy-mål (Pages-bas / ev. cross-repo-publicering).
- Regelprofiler (matchtid/format) om annan sport/regel.

**Bra post-mortem-output:** en "så rullar du ut en ny cup"-checklista som i sig avslöjar
exakt vilka filer som måste bli config.

---

## 6. Öppna frågor / beslut till post mortem

- Hur långt generaliserar vi `ahk-beach` vs. satsar på Cuptide?
- Web push-notiser ("match om 15 min", "slutresultat") — efterfrågat; designa in
  prenumerationsmodell? (Diskuterat tidigare, inte byggt.)
- Tolkning av UX-punkt 4 (flikrad: pinnad vs. horisontell scroll).
- AR-vy med riktningspil ("åt det hållet ska du") — cool men troligen overkill.

---

## Löpande noteringar (lägg till här under dagen)

- _(2026-07-18) … lägg nya observationer här allteftersom._
