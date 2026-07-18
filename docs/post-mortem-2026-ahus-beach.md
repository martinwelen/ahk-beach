# Post mortem — Åhus Beach Handboll 2026 (Alingsås HK)

**Period:** ~9–18 juli 2026 (turneringsveckan) · **Repo:** `ahk-beach` · **Status:** avslutad, lyckad
**Underlag:** ~65 substantiella commits + 471 automatiska datauppdateringar, samt användarens
löpande feedback/idéer. Kompletterar den råa noteringssamlingen i `docs/infor-post-mortem.md`.

---

## 1. Sammanfattning

Vi byggde och drev en installerbar, offline-först PWA-lösning för **hela Alingsås HK** (43 lag i
~10 åldersgrupper, U8–U18) under Åhus Beach Handboll — en app per åldersgrupp, gratis hostad på
GitHub Pages, automatiskt uppdaterad av en molnrobot som hämtar från cupmanager. Under själva
turneringsveckan lyfte vi in U15 i den delade pipelinen (utan att byta URL), byggde zoombar
områdeskarta med live-markörer, klient-sida livescore som **slog cupmanagers egen i hastighet**,
videolänkar, multi-hero, slutspelsrunda-etiketter, bakgrundsuppdatering och en härdad deploy-slinga.

**Utfall:** lösningen uppskattades av deltagare och besökande föräldrar och höll hela veckan.
Den var dessutom skarp-testad under press — inklusive truppändringar och tröjnummer inmatade live
på matchdag med noll driftstörning.

> **⭐ Viktigaste lärdomen (läs denna om inget annat):** Varenda bugg som *spelade roll* levde i
> sömmarna mellan cachar — HTTP-cache, service worker, CDN, pollfönster, robot-latens — för att
> *färskhet hanterades ad hoc i stället för att designas*. I en offline-först, fler-cache,
> robot-matad pipeline **är färskhetsmodellen arkitekturen**: ett versionerat manifest, en explicit
> data-epok som propageras hela vägen, och en monitor som larmar när produktion är inaktuell. Designa
> det först nästa gång, så inträffar inte halva bugglistan från juli (TDZ-kraschen undantagen).
> Följdsatsen: **produkten var aldrig appen — den var dataflödet. Äg det medvetet.**

---

## 2. Vad vi levererade (scope & tidslinje)

| Datum | Leverans |
|-------|----------|
| 10 jul | Korrekt målskillnad + klasschip per match; inga tomma slutspelstabeller |
| 12 jul | **U15 in i delad pipeline** — samma URL via cross-repo-publicering (deploy key), portade trupper, SW-cache-hygien (origin-delad CacheStorage-gotcha) |
| 12 jul | **Zoombar områdeskarta** som egen flik (nyp/panorera, helskärm), sid-zoom avstängd |
| 14 jul | **Livescore** (klient pollar `MatchResult`), **videolänk** (solidsport bana 1–2), **multi-hero** (alla live / alla samtidigt-nästa), match-id i data.json |
| 14 jul | **Slutspelsrunda** på kort, pre-persist "Slut"-siffra (~10 min→~10 s), **bakgrundsuppdatering** (per-app `sched.json`, 60 s) |
| 14 jul | **Kartmarkörer** (live/nästa på rätt bana, klickbar info-panel) + **klubbtält-markör**; uppmätta banpositioner (`bana_coords.py`) |
| 14 jul | **Force-rebuild-workflow** (`-f force=true`) + race-härdad push |
| 15 jul | **Resultat-försvinner-fix** (no-store + `POLL_GRACE_MS`), privat CF Analytics-dashboard (Worker + `/diag`) |
| 17 jul | Trupp-/positions-/**tröjnummer**-inmatning live (P15 Blå/Orange/Vit) |
| 18 jul | Post-mortem-underlag + verifierad API-koll för framtida matchvy |

**Skala:** roboten körde ~471 datauppdateringar över veckan (var 10:e min under turneringen, triggat
av homelab CT 130). Klienten pollade livescore direkt från webbläsaren (CORS öppet för vår origin).

---

## 3. Vad som funkade bra (behåll)

1. **Klient-sida livescore** var den stora vinsten — snabbare än cupmanagers egen widget, ingen
   robot-latens i kritiska ögonblick.
2. **Offline-först installerbar PWA** — fungerade på arenan trots skral täckning; "lägg till på
   hemskärmen" gav app-känsla.
3. **Karta med "var spelar vi nu/härnäst" + klubbtält** — en differentiator ingen konkurrent gör bra.
4. **Klubbkodsdriven data** (inga hårdkodade lag-id) — hela klubben upptäcks automatiskt; nästa
   turnering byts med ett `TOURNAMENT_ID`.
5. **U15 kvar på gammal URL** — cross-repo-publicering bevarade installerade hemskärms-appar.
6. **Deploy-/verifieringsdisciplin** — härdad push, force-rebuild och "verifiera på deployad sida"
   höll även under skarp matchdag.
7. **Noll runtime-beroenden** — vanilla JS/CSS i en mall; gratis hosting; inga servrar att drifta.

---

## 4. Vad som gick fel — incidenter & rotorsaker

Sammanfattning av de buggar/fällor som kostade tid, med rotorsak och åtgärd. Dessa är själva
guldet i post mortem.

1. **TDZ-krasch (hela appen dog vid load).** `const liveState` användes av `render()` innan
   deklaration. **Pytest-substrängtester fångade det inte** — hittades via kodgranskning +
   node-repro. → *Lärdom: verifiera app-**runtime** (webbläsare/node-eval), inte bara att
   strängar finns i mallen.*
2. **Hash-vakt-bugg (fält deployades aldrig).** `data.json` skrevs bara om vid hash-ändring, men
   hashen inkluderade inte `id`/`video` → livescore saknade match-id i produktion. Diagnosen kom
   av att köra hämtningen lokalt (funkade) mot deployad (0 id). → *Lärdom: hashen måste täcka allt
   som ska trigga omskrivning.*
3. **Resultat försvann vid refresh — två oberoende rotorsaker.**
   (a) Bakgrundsuppdateringen läste `sched.json` via HTTP-cachen (Pages `max-age=600`) → en
   inaktuell kopia skrev över ett visat resultat i upp till 10 min. Fix: `fetch(..., {cache:"no-store"})`.
   (b) Livescore-pollfönstret stängde vid start+21 min < robotens persistens-latens (~25–30 min) →
   glapp där varken live-"Slut" eller sparat resultat visades. Fix: `POLL_GRACE_MS = 40 min`.
   → *Lärdom: både klient-cache och latens-fönster måste överstiga den långsammaste
   persistensvägen.*
4. **CI-push-race.** Robotens auto-commits var 10:e min kolliderade med manuella pushar. Fix:
   race-härdad push (pull --rebase + retry, snäll skip vid äkta konflikt).
5. **Concurrency-cancel (nummer deployades inte).** Snabba force-runs efter varandra avbröt
   varandras *väntande* körningar (GitHub `cancel-in-progress: false` avbryter äldre pending). En
   alex/herou-körning avbröts och numren kom ut först vid en ren, ensam körning. → *Lärdom: en
   deploy i taget; vänta tills kön är tom.*
6. **CDN gav falska "saknas"-utslag.** Både Pages och `raw.githubusercontent` är CDN-cachade
   ~5–10 min → verifiera mot **auktoritativ källa** (GitHub contents-API), inte cachad URL.
7. **GPS "du är här" övergavs.** LOO-residualer ~27–67 m (hav och banor delar blått) → för dåligt.
   Manuellt uppmätta banpositioner istället — enklare och pålitligare.
8. **`_runda_sv`-robusthet.** Källan sa "Semi final", inte "1/2 Final" → gjorde mappningen robust
   mot ord-/bråk-/versalvarianter. Fångades av integrationskörning, inte enhetstest.
9. **Prematurt "fixat".** Ett fel förklarades löst utan att spåra hela dataflödet → återkom och
   skapade (befogad) frustration. → *Lärdom: verifiera live innan man säger fixat.*

**Röd tråd:** de dyraste buggarna var alla **klient-/cache-/timing-relaterade** och osynliga för
substrängtester. De fångades av systematisk felsökning, node-/webbläsar-repro och verifiering mot
auktoritativ deployad källa.

---

## 5. Process- & arbetslärdomar

- **Systematisk felsökning slog gissningar** varje gång — rotorsak före fix, mät verkligt beteende
  (lokal vs deployad, live-API), en hypotes i taget.
- **Substrängtester räcker inte för runtime.** Komplettera med node-eval av JS och en faktisk
  webbläsarladdning för mall-ändringar.
- **Verifiera mot auktoritativ källa, inte CDN-cache.**
- **En deploy i taget** under skarp drift.
- **Minsta möjliga diff** live; för roster committa *enbart* `roster_data.py` (`git checkout -- .`
  för genererade artefakter).
- **Match-day zero-breakage-protokollet** (nu vilande, återaktiveras för framtida live-cuper) var
  rätt disciplin och bör vara standard nästa gång.
- **Testslutsatsen (viktig):** eftersom varje allvarlig bugg satt i cache-/timing-/deploy-sömmar och
  var osynlig för enhetstester → inför en **syntetisk end-to-end-koll mot den *deployade* artefakten**
  (hämta prod, verifiera färskhet + schema), inte fler substrängtester. Vi hade ingen
  färskhets-/staleness-monitor — det borde vi ha.

---

## 6. Driftsmodell (arkitektur i praktiken)

- **Datalager:** `fetch_data.py`/`fetch_standings.py` (klubbkodsdrivet) → hash-vaktade
  `data.json`/`standings.json`.
- **Bygge:** `build_apps.py`/`build_ics.py`/`build_hub.py` → en PWA per åldersgrupp (+ U15 till
  `dist-u15/`), kalendrar, hubb.
- **Robot:** GitHub Actions (`update.yml`), var 10:e min under turneringen (homelab CT 130-trigger
  eftersom GitHubs schema är opålitligt), commit bara vid dataändring, race-härdad push,
  `force=true` för kod-/trupp-ändringar.
- **U15-publicering:** `scripts/deploy_u15.sh` → externa repot via deploy key (behåller gammal URL).
- **Klient-realtid:** webbläsaren pollar `MatchResult` direkt (CORS öppet); bakgrundsrefresh av
  `sched.json`.
- **Analys:** Cloudflare Web Analytics (cookielöst) + privat Worker-dashboard.

---

## 7. Backlog — förbättringar observerade live

Alla i den **delade `template.py`** → hög risk (en bugg slår mot alla appar); verifiera i webbläsare.

1. **Slutspelsträdet är lite missaligned** — layouten linjerar inte rundorna/matcherna snyggt.
2. **Bana + tid saknas i slutspelsträdet** — datan finns per match.
3. **Klass i filterchipsen** — "AHK Blå"/"Vit" krockar mellan P15 och F15; visa klass bredvid laget.
4. **Flikraden låst från scroll som filterraden** (tolkning att bekräfta: pinnad vs. horisontell scroll).
5. **Hoppa-till-"nu"** — autoscroll/"Nu"-knapp i långa scheman sent i turneringen.
6. **Separat matchvy (klick på match)** — lagstatistik + hela matchens historik mål för mål.

**Verifierat 18 juli att matchvyn är genomförbar på befintlig datakälla** (probat mot live
bana 1/2-match):
- `matchStats` → per-lags turneringsaggregat (mål/V/O/F/spelade).
- `MatchFeed({id})` → `events` (mål-för-mål) + `statistics` (skott, räddningar, kort, 1/2/3-poängare
  **sport-agnostiskt**, foul, timeouts, formGuide). *`events` var pagerad/lat — exakt form naglas i bygget.*
- `previousMeetings` → inbördes-historik.
- *Att kontrollera:* CORS för `MatchFeed`/`matchStats` (bara `MatchResult` är verifierat öppet).

---

## 8. Feedback & idéer från användaren (inför post mortem)

- **Web push-notiser** ("match om 15 min", "slutresultat") — efterfrågat/undrat; designa in
  prenumerationsmodell tidigt (iOS PWA-push kräver installerad app + user gesture — genomförbart men
  plattformskänsligt).
- **AR-vy med riktningspil** ("åt det hållet ska du") — coolt men troligen overkill i nuläget.
- **Matchvy med statistik + mål-för-mål** (punkt 6 ovan) — nu verifierad som genomförbar.
- **Namngivning → "Cuptide"** för ett framtida generellt system (`.app` primär, `.com` säkrad);
  vision i separat repo `/home/martin/dev/cuptide/`.
- **Generalisering** till andra cupmanager-cuper "med några få anpassningar" (avsnitt 9).

---

## 9. Risker & blinda fläckar (prioriterat)

Punkter en gedigen post mortem för *just den här sortens projekt* måste ta på allvar. Ordnade efter
hur allvarliga de är.

1. **⚠️ Barns namn i ett publikt repo (GDPR) — kan avsluta projektet.** Trupper med minderåriga,
   kopplade till lag, arena och minutexakt schema, publicerade på Pages **och permanenta i
   git-historiken**. Under GDPR krävs rättslig grund; "klubben tyckte det var okej" är inte det
   samtycke *föräldrarna* gett. Behövs: samtyckesprocess, dataminimering (endast förnamn/initialer),
   plan för att skrubba git-historiken, och en takedown-rutin. **Detta rankar över alla tekniska
   fynd.**
2. **Beroenderisk mot cupmanager — nämnd men inte kostnadssatt.** Ingen ToS-granskning, ingen
   rate-limit-överenskommelse; en robot som slår mot deras API var 10:e min i all evighet, plus
   öppen CORS de kan stänga i en deploy. Kvantifiera: vad går sönder, hur upptäcker vi det (en
   *staleness-monitor* på våra egna artefakter — som vi saknar), och vad är degraderat läge.
   Mitigering: **prata med cupmanager** (se rekommendation).
3. **Homelab i produktionsloopen.** CT 130:s cron triggar uppdateringarna (GitHubs schema är
   opålitligt). En "gratis, noll-infra GitHub-lösning" som i tysthet hänger på en burk hemma är en
   bus-factor- och reproducerbarhetsrisk. Antingen dokumentera som accepterad risk med en runbook,
   eller flytta triggern till en hostad schemaläggare.
4. **Testslutsatsen** (se avsnitt 5): syntetisk E2E mot deployad artefakt + staleness-monitor, inte
   fler enhetstester.
5. **Mindre men reella:** deploy-nyckelns scope/lagring/rotation; Actions-förbrukning utanför säsong
   (**stäng av roboten** mellan cuper — även goodwill mot cupmanager); den ~800-rader delade mallens
   öde (generaliseringen i spår A är *precis* där den antingen faktoriseras eller fossiliseras —
   budgetera för det, forka inte per cup); **tillgänglighet** (a11y) är outforskad för en publik
   klubbapp; och ett **repetitionsfönster före 2027** eftersom cupmanagers odokumenterade schema kan
   ha drivit i tysthet.

---

## 10. Strategiskt: generalisera `ahk-beach` vs. bygga `Cuptide`

Två spår som svarar på olika frågor:

**A. Generalisera `ahk-beach` till en mall** (snabb utrullning, låg risk)
Redan parametriserat: `config.py` (`TOURNAMENT_ID`/`CLUB_ID`/`API_HOST`/`PAGES_BASE`),
klubbkodsdriven auto-upptäckt. Troliga anpassningspunkter att lyfta till config/mall:
turnerings-/klubb-id, branding (färger/logga/namn/analytics), områdeskarta + banpositioner (mest
cup-specifikt), truppdata, deploy-mål, regelprofiler. **Bra output:** en "så rullar du ut en ny
cup"-checklista som avslöjar exakt vilka filer som måste bli config.
*Fynd som stärker spåret:* cupmanager bär mer struktur än vi trodde (sport-agnostisk statistik),
så mer kan återanvändas rakt av.

**B. `Cuptide`** (från grunden, äga domänen + datalagret)
Långsiktigt, större; svarar på cupmanagers svagheter (inmatnings-UX, äkta realtid, multi-tenant).
Se `/home/martin/dev/cuptide/README.md`.

*Rekommendation nedan (avsnitt 11) — skärpt efter en oberoende review (Fable).*

---

## 11. Rekommendation & nästa steg

**Kör A nu. Avvisa B i dess nuvarande form — men behåll `cuptide.app` som billig option.**

Motiveringen är inte "B är stort och riskabelt" (det vet vi). Det är att veckan bevisade något
*mycket smalare* än vad B kräver. Vad som validerades: att en ensam utvecklare kan bygga ett
**överlägset konsument-läslager ovanpå någon annans system of record**. Vad B kräver: att *vara*
system of record — schemaläggning, domartillsättning, bankonflikter, anmälan, betalning/återbetalning,
arrangörssupport kl. 07 på matchdag, och svårast av allt: B2B-försäljning till cup-arrangörer som är
volontärer med inrotade vanor och befintliga cupmanager-avtal. Det är en annan verksamhet med en
annan kärnkompetens, och inget av det de-riskades i juli. De två cupmanager-svagheter B siktar på
(arrangörs-/sekretariats-UX, realtid) är *precis* det som en konsument-PWA-vecka inte lärde oss något
om — vi rörde aldrig skriv-vägen.

**Skärpt A — vidga vallgraven med datan vi verifierade men inte skeppade.** `MatchFeed`-events,
inbördes-möten, per-lags-aggregat: en mall som renderar mål-för-mål-tidslinjer och form-guide
*snabbare än cupmanagers egen widget* är en synbart bättre produkt för nära noll marginalkostnad —
och det sport-agnostiska schemat gör att det generaliserar bortom handboll gratis. Det är
differentiering-per-ansträngning i maximum.

**Det viktigaste draget slår all kod: prata med cupmanager.** Hela tillgången vilar på odokumenterade
endpoints och en CORS-header de kan stänga i en enda deploy. Just nu *är* det din existentiella risk.
En konversation gör om den till antingen (a) sanktionerad åtkomst, kanske ett dokumenterat API — risk
undanröjd, (b) ett partnerskap/acquihire — "er egen widget är långsammare än min skrapa byggd på en
vecka" är en stark öppning, eller (c) ett nej — då har du lärt dig A:s tak billigt. Blir B någonsin
av bör det bli *deras* arrangörs-UX, inte en konkurrent byggd från grunden.

**Realistisk väg:**
1. **Off-season:** stäng av roboten mellan cuper; åtgärda GDPR-punkten (avsnitt 9.1) och skrubba
   git-historik; härda + generalisera mallen (en "så rullar du ut en ny cup"-checklista är
   acceptanskriteriet, inte fork-per-cup); lägg till staleness-monitor + syntetisk E2E.
2. **Kontakta cupmanager** — sanktionerad åtkomst eller åtminstone klarhet om A:s tak.
3. **Bevisa på en mindre cup våren 2027** som ren config-utrullning (det *är* acceptanstestet).
4. **Åhus 2027** som andra datapunkt — nu med analytics-worker som mäter faktisk användning, så
   "uppskattat" blir en *siffra* innan mer ambition.

Behåll `cuptide.app/.com` som option; investera inte i B förrän (a) A:s tak är känt via
cupmanager-samtalet och (b) det finns uppmätt efterfrågan.

---

## 12. Bilaga — nyckeltal

- ~65 substantiella commits (feat/fix/docs) + 471 auto-datauppdateringar (~9–18 juli).
- 10 byggda appar (U8–U18 + U15 externt), 43 lag, ~10 åldersgrupper.
- 110 gröna enhetstester; noll driftstörningar under matchdagarna.
- Kända kvarvarande: `MatchFeed.events` exakt form, CORS-koll för feed/stats, 6 UX-backlog-punkter.
