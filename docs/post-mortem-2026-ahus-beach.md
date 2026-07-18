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

1. **Barns namn & GDPR — hanterat för i år; designas på riktigt i Cuptide.** *Förtydligande från
   användaren:* denna vecka är **godkänd av föräldrarna** och omfattar **enbart Alingsås-spelare** —
   den akuta risken är alltså hanterad för det här instansen. Kvarstående att vara medveten om vid
   *fortsatt* bruk: (a) git-historiken är permanent, så om namn ska tas bort senare krävs
   historik-skrubbning; (b) vid **återanvändning för andra cuper/klubbar** måste samtyckesgrunden
   etableras på nytt — andra klubbars spelare omfattas inte av Alingsås-föräldrarnas godkännande.
   Den **fullständiga GDPR-/samtyckesmodellen ägs av Cuptide-projektet** (eget repo), där den
   aktualiseras skarpt.
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

## 10. Strategiskt: två lager i samma plan (inte konkurrenter)

*Förtydligande från användaren:* det här systemet och Cuptide är **inte** ett antingen/eller. De är
två lager i samma roadmap:

- **Det här systemet = konsument-/publiklagret.** Det ska (1) **återanvändas för Alingsås egna
  deltaganden i andra cuper**, och (2) **inkorporeras i Cuptide** som dess publika lager (med de
  anpassningar som krävs där).
- **Cuptide = helhetssystemet för att *arrangera* en cup** (eget repo `/home/martin/dev/cuptide/`):
  äger datamodellen, skriv-vägen (sekretariat/domare), realtid, regler, multi-tenant. Det svarar på
  cupmanagers svagheter som konsumentlagret aldrig rör.

Det som **överförs** till Cuptide är alltså *konsumentupplevelsen* — offline-först-PWA:n, områdeskartan,
den snabba livescore-UX:en, matchvyn, multi-hero — **inte** cupmanager-skrapnings-plumbingen. Skrapningen
är en övergångslösning tills Cuptide äger sin egen data.

**Redan parametriserat (bra startläge för återanvändning):** `config.py`
(`TOURNAMENT_ID`/`CLUB_ID`/`API_HOST`/`PAGES_BASE`), klubbkodsdriven auto-upptäckt. Anpassningspunkter
att lyfta till config/mall: turnerings-/klubb-id, branding (färger/logga/namn/analytics), områdeskarta +
banpositioner (mest cup-specifikt), truppdata, deploy-mål, regelprofiler. Fyndet att cupmanager bär ett
**sport-agnostiskt** statistik-schema stärker både återanvändning *och* Cuptide-datamodellen.

---

## 11. Rekommendation & nästa steg

Med den korrigerade ramen (två lager, inte val) blir rekommendationen en **sekvens**, inte ett vägval:

**1. Nu → generalisera konsumentlagret för egen återanvändning.** Gör `ahk-beach` mallbar (en "så
rullar du ut en ny cup"-checklista är acceptanskriteriet — *inte* fork-per-cup, annars fossiliserar
den ~800-rader-mallen). Detta betjänar Alingsås nästa cup direkt och är samtidigt ritningen för
Cuptides publika lager.

**2. Vidga vallgraven med datan vi verifierade men inte skeppade.** `MatchFeed`-events (mål-för-mål),
inbördes-möten, per-lags-aggregat → matchvy + form-guide *snabbare än cupmanagers egen widget*. Nära
noll marginalkostnad, och det sport-agnostiska schemat generaliserar bortom handboll. Dessa UX-mönster
är precis det som sedan portas in i Cuptide.

**3. Hantera interim-beroendet på cupmanager medvetet.** Så länge konsumentlagret skrapar cupmanager
vilar det på odokumenterade endpoints + öppen CORS de kan stänga i en deploy. Det är inte
*existentiellt* (Cuptide är slutmålet som tar bort beroendet), men för mellantiden: (a) lägg en
**staleness-monitor** på egna artefakter så tyst drift upptäcks, (b) **stäng av roboten mellan cuper**
(mindre last, goodwill), och (c) *överväg* ett samtal med cupmanager för sanktionerad/dokumenterad
åtkomst — billig riskreducering, ingen brådska.

**4. Mät användning.** Låt analytics-workern göra "uppskattat" till en *siffra* (unika enheter, återbesök,
flik-användning) — underlag för hur mycket som är värt att bära över i Cuptide.

**5. GDPR:** hanterat för i år (föräldrasamtycke, endast Alingsås). Den fullständiga samtyckes-/
dataminimeringsmodellen designas i **Cuptide**; vid återanvändning för andra klubbar dessförinnan
måste samtyckesgrunden etableras per klubb (avsnitt 9.1).

**6. För in i Cuptide.** När Cuptides datalager finns: portera konsumentlagrets mönster (PWA/offline,
karta, livescore-UX, matchvy) ovanpå Cuptides *egen* data i stället för cupmanagers — då stängs
interim-beroendet.

**Röd tråd:** det överlägsna vi byggde var *konsumentupplevelsen och dataflödet*, inte skrapningen.
Återanvänd och förfina det nu; låt Cuptide ärva det.

---

## 12. Bilaga — nyckeltal

- ~65 substantiella commits (feat/fix/docs) + 471 auto-datauppdateringar (~9–18 juli).
- 10 byggda appar (U8–U18 + U15 externt), 43 lag, ~10 åldersgrupper.
- 110 gröna enhetstester; noll driftstörningar under matchdagarna.
- Kända kvarvarande: `MatchFeed.events` exakt form, CORS-koll för feed/stats, 6 UX-backlog-punkter.
