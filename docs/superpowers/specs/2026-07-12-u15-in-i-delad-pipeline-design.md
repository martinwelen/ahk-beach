# Design: U15 in i den delade pipelinen – samma URL

**Datum:** 2026-07-12
**Status:** Godkänd design, redo för implementationsplan

## Bakgrund

`ahk-beach` byggdes ursprungligen genom att generalisera U15-appen
(`alingsas-ahus-beach-2026`, lokalt `~/dev/ahusbeach`). Sedan dess har all
funktionalitet och felsökning gått in i `ahk-beach`:s modulära kod (`template.py`,
`build_apps.py` m.fl.), medan U15-appen frusit på sin gamla monolitiska
`build_site.py`. De två kodbaserna har divergerat.

U15 hämtas redan in i `ahk-beach`:s `data.json` av samma robot, men
`build_apps.py` och `build_ics.py` **hoppar över** u15
(`SKIP_AGE_SLUGS = {"u15"}`), och hubben länkar u15 → den externa URL:en.

## Krav (SKALL)

1. **All funktionalitet och felsökning från main-appen SKALL finnas i U15.**
   Detta är ett skall-krav för allt framåt – U15 ska spegla main-appen exakt.
2. **U15:s URL SKALL vara oförändrad**
   (`https://martinwelen.github.io/alingsas-ahus-beach-2026/`). Många har sparat
   appen på hemskärmen; länken får inte brytas.
3. **Trupp-fliken (verklig spelardata) SKALL bevaras** – ingen regression.
4. **Nolldrift för live-klasser.** En turnering pågår. U15 spelar inte just nu
   (säkert att röra), men andra åldersgrupper är live och byggs av den *delade*
   koden – de får inte påverkas.
5. **Kontinuerliga liveuppdateringar** ska fortsätta flöda till U15 efter bytet.

## Vald lösning

`ahk-beach` blir **enda källan** (single source of truth). Den bygger U15 med
exakt samma mall/kod som alla andra åldersgrupper, och en **deploy-nyckel**
pushar resultatet till roten av `alingsas-ahus-beach-2026`. Eftersom både den
installerade U15-appen och main-appens genererade appar använder **relativ**
PWA-identitet (`start_url: "."`, `scope: "./"`, `sw.js` relativt, inget absolut
`id`), ser en redan installerad app de nya filerna på samma URL som *samma app*
och uppdaterar sig sömlöst.

### Varför inte redirect

En redirect är **inte** garanterad för en installerad PWA. Appen startas i sitt
`scope`; en redirect ut ur scope (`alingsas-ahus-beach-2026/` → `ahk-beach/u15/`)
gör att iOS/Android kastar ut appen i webbläsaren i stället för standalone.
GitHub Pages kan inte göra äkta 301 för projektsidor (bara meta/JS-refresh), och
den gamla service workern ligger kvar och kan intercepta. Att servera det nya
innehållet på plats är därför det garanterat fungerande alternativet – inte
redirect.

### Varför "ahk-beach pushar" (och inte "gamla repot hämtar koden")

U15-datan ligger redan i `ahk-beach`:s `data.json`. En robot + en kodbas ger noll
drift. Alternativet (gamla repot klonar ahk-beach och bygger själv) sparar en
deploy-token men ger två robotar och timing-glapp – sämre för en app som ska
spegla main-appen exakt.

## Komponenter och ändringar

### 1. Bygg U15 i `ahk-beach`

- `build_apps.py`: sluta hoppa över u15. Bygg U15 till en egen **staging-katalog**
  (t.ex. `dist-u15/`), inte till `ahk-beach/u15/` (den skulle skapa en ny,
  oönskad ahk-beach-URL). Övriga åldersgrupper byggs oförändrat.
- Parametrisera `__BASE__` så U15 får
  `https://martinwelen.github.io/alingsas-ahus-beach-2026`
  (används endast för `og:url`/`og:image`, `template.py:25-26`). Övriga grupper
  behåller `config.PAGES_BASE/<age_slug>`.
- `build_ics.py`: sluta hoppa över u15. Skriv U15-kalendrarna med **exakt** de
  gamla filnamnen så befintliga prenumerationer fortsätter uppdateras:
  `alingsas-alla.ics`, `alingsas-p15-bla.ics`, `alingsas-p15-orange.ics`,
  `alingsas-p15-vit.ics`, `alingsas-f15-bla.ics`, `alingsas-f15-gul.ics`,
  `alingsas-f15-vit.ics`.

### 2. Porta trupp-data (additivt)

- Lägg `roster_data.py` i `ahk-beach`, **remappad** från gamla nycklar till
  ahk-beach:s slug-schema:
  `p15-bla → u15-p-bla`, `p15-orange → u15-p-orange`, `p15-vit → u15-p-vit`,
  `f15-bla → u15-f-bla`, `f15-gul → u15-f-gul`, `f15-vit → u15-f-vit`.
- `build_apps.py`: mata `__ROSTERS__` med gruppens trupper (filtrera roster på
  gruppens lag-slugs) i stället för hårdkodat `"{}"` (`build_apps.py:90`).
- Grupper utan trupp-data → `"{}"` → Trupp-fliken göms (befintlig logik i mallen,
  `HAS_ROSTERS`). **Live-apparna beter sig därmed exakt likadant** – detta är en
  verifieringspunkt, inte en beteendeändring.

### 3. Deploy till gamla repot

- `ahk-beach`:s workflow pushar `dist-u15/` + dess `ics/` till **roten** av
  `alingsas-ahus-beach-2026` via deploy-nyckel
  (t.ex. `peaceiris/actions-gh-pages` med `external_repository`).
- Publicerade filer: `index.html`, `manifest.json`, `sw.js`, ikoner, `ics/`.
- SW-cachenamn byter `ahus-schema-v1` → `ahk-u15-v1`. Installerad app uppdaterar
  vid nästa start. **Lägg till gammal-cache-städning** i SW-mallen (radera cachar
  ≠ aktuell på `activate`) så `ahus-schema-v1` rensas. Detta är en delad
  mall-ändring och måste vara ofarlig för live-apparna (de får bara städlogik som
  rör deras egen `ahk-uXX-v1`).
- Ikoner: U15 fortsätter använda samma ikon-assets så hemskärms-ikonen inte
  ändras (verifiera att ahk-beach:s ikoner är acceptabla/identiska, annars kopiera
  de gamla).

### 4. Pensionera gamla roboten

- Stäng av `update.yml` i `alingsas-ahus-beach-2026` (den har egen cron:
  `*/30` + turneringscron + dispatch). Annars skriver två robotar över varandra.
- Gamla `build_site.py`, `fetch_matches.py`, `fetch_standings.py`,
  `roster_data.py` m.fl. i det repot blir historik (ingen aktiv körning).
- Triggern (homelab CT 130-cron → `workflow_dispatch` mot `ahk-beach`) är
  oförändrad; den kör redan ahk-beach:s workflow.

### 5. Cutover och verifiering

- Bygg U15 lokalt från `ahk-beach`; jämför mot nuvarande live-U15:
  schema (tidsordning, härnäst, könsfilter), tabeller, slutspel (A/B/C),
  Trupp-flik, ics-innehåll.
- Bekräfta att **live-klassernas** genererade output är byte-identisk före/efter
  trupp- och SW-ändringen (`git diff` på deras `index.html`/`sw.js` ska vara tom
  bortsett från avsedda no-ops).
- Ett rent cutover-commit till gamla repot. Verifiera uppdateringsvägen på samma
  URL (SW uppdateras, ingen scope-brytning).

## Risker och hur de hanteras

| Risk | Hantering |
|------|-----------|
| Slug-mismatch gör att trupp inte joinar | Remap i `roster_data.py` (se §2) – verifieras mot `data.json`-slugs. |
| ICS-namn ändras → prenumerationer dör | Bygg U15-ics med exakt gamla filnamn (§1). |
| Två robotar skriver gamla repot | Stäng av gamla `update.yml` (§4). |
| Delad mall-ändring bryter live-appar | Trupp = additiv (tom → oförändrat); SW-städning rör bara egen cache. Byte-diff-verifiering (§5). |
| Installerad app ser ny app-identitet | Relativ identitet bevaras; samma URL → sömlös uppdatering. |
| Ops-container-trigger påverkas | Oförändrad – kör redan ahk-beach:s workflow. |

## Utanför scope

- Att flytta in trupp-*redigering* eller trupp för andra åldersgrupper (mekaniken
  blir generell, men bara U15 har data i denna omgång).
- Att ta bort/arkivera gammal kod i `alingsas-ahus-beach-2026` utöver att
  avaktivera roboten.
- Internationella set-baserade regler (redan en förberedd söm i main-appen).
