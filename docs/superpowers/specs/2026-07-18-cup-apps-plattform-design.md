# cup-apps — generaliserad cup-app-plattform · Design

**Datum:** 2026-07-18 · **Status:** godkänd design (brainstorming) · **Nästa:** implementationsplan

**Mål:** ett nytt plattforms-repo där man **anger `tournamentId` + `clubId`** och resten
byggs så långt som möjligt automatiskt → en körbar PWA-svit för den klubben i den cupen,
levererad som en **PR att granska**. Generaliserar konsumentlagret från `ahk-beach`
(Åhus). Är samtidigt språngbrädan in i **Cuptide** (cups-registryn = multi-turnering i
miniatyr). `ahk-beach` lämnas **fruset som Åhus-historik** (levande URL:er intakta).

## Ramar (beslutade i brainstorming)
- **Struktur:** plattforms-repo med `cups/<slug>/`-registry (inte template-per-repo).
- **Auto-flöde:** GitHub Actions `workflow_dispatch(tournamentId, clubId[, apiHost])`.
- **Auto-nivå:** körbar app + **PR att granska** (auto-deploya inte direkt).
- **Single-tenant (Alingsås egna cuper), många cuper.** Äkta multi-*organisation* är
  Cuptides jobb — bygg inte SaaS för tidigt här.

## Arkitektur
Tre delar:
- **`engine/`** — generell byggmotor (refaktorerad från ahk-beach): tar ett *cup-config-
  objekt* (laddat ur `cup.toml`) i stället för globala `config.py`-konstanter.
- **`cups/<slug>/cup.toml`** — registryn: en fil per cup med allt om cupen.
- **`discover.py` + `new-cup.yml`** — auto-flödet: 2 ID → härled config → bygg → PR.

### Repo-layout
```
engine/  api.py derive.py rules.py fetch_data.py fetch_standings.py
         build_apps.py build_ics.py build_hub.py template.py
         cupconfig.py (ladda/validera cup.toml)  discover.py
cups/<slug>/  cup.toml   assets/(logo, karta – valfria)   rosters.py (valfri)
dist/<slug>/  byggd output → GitHub Pages
.github/workflows/  new-cup.yml (dispatch→PR)   update.yml (schemalagd data-refresh)
```
Pages-URL: `…/cup-apps/<slug>/<mål>/`. **Två-nivåers hubb:** cup-lista → per-cup-hubb.

## Byggmål per cup
För varje cup + klubb byggs:
1. **En app per åldersgrupp** (som idag) — schema, tabeller, slutspel, trupp, ev. karta.
2. **En klubb-app "alla lag oavsett ålder"** (NYTT krav) — samtliga klubbens lag och
   matcher i alla åldrar i EN app, med filter på **ålder/klass** + lag. Kräver att
   **klass visas i filter/kort** (löser även post-mortem-UX-punkt #3 — "AHK Blå" finns i
   flera klasser). Byggs som en syntetisk aggregat-grupp över alla åldersgrupper.
3. **Per-cup-hubben** som länkar åldersgrupps-apparna + klubb-appen.

## Per-cup-config (`cup.toml`) — schema
- **Obligatoriskt (från dispatch):** `tournament_id`, `club_id`, `api_host`.
- **Auto-härlett (fylls av discover):** `cup_name`, `club_name`, `slug`, `utc_offset`
  (DST-medveten från datumintervall), `age_groups` (härledda), `colors` (från färgsuffix),
  `venues` (distinkta hallar/banor), `venue_mode` ("beach_court" | "halls").
- **Auto-default + manuell finish:** `branding` (palett/logga/appnamn — default klubbblå +
  palett), `rule_profile` (default + override), `venue_map` (default: ingen karta, bara
  namn; lägg bild + koordinater för "var spelar vi nu"), `external_publish` (opt-in
  cross-repo-publicering, generaliserat U15-mönster), `rosters` (valfritt).

## discover.py — ansvar
Givet `tournament_id` + `club_id` + `api_host`:
1. `fetch_store` (MatchWindow-paging).
2. Härled: cupnamn (Tournament-entitet), klubbnamn (ur clubId:s lag), åldersgrupper
   (parse_category på lagens categoryName), klasser, färger (färgsuffix-regel), venues
   (distinkta Arena-`completeName`), datumintervall → säsong → `utc_offset`, regel-gissning.
3. **Edge-cases (från Potatiscupen-testet):** icke-ålders-kategorier (t.ex. "HFA") →
   **flagga**, skapa inte tyst en `u0`-grupp; saknad regel-suffix → default-profil + notis;
   hallar utan gemensam bankarta → `venue_mode="halls"`, karta valfri.
4. Skriv `cups/<slug>/cup.toml` med auto-härlett + defaults/placeholders för finish-bitarna,
   samt en **rapport** (vad härleddes, vad behöver finishas) för PR-texten.
5. `api_host` gissas `<slug>.cupmanager.net` och **verifieras** mot API:t; annars valfri
   3:e dispatch-input.

## Auto-härlett vs manuellt (ärlig gräns)
- ✅ **Auto → körbar app direkt:** cupnamn, klubbnamn, åldersgrupper, klasser, lag, färger,
  datum/säsong/tidszon, schema, resultat, tabeller, slutspel, hall-/bannamn, ICS,
  klubb-appen, hubben.
- ⚙️ **Auto-default, manuell finish i PR:** branding-polish, regel/format, venue-karta.
- **Ingen tyst gissning** på det som inte går att härleda — flaggas i PR:en.

## Motor-refaktor (från ahk-beach)
- **Config-objekt** ersätter globala `config.py` (största jobbet; trådas genom
  fetch/build/template).
- **Regel/format config-drivet** (slut på `rule='?'`-fallback som enda väg).
- **Robust `parse_category`** + hantering av icke-ålders-kategorier.
- **Venue-abstraktion:** `venue_mode` beach_court/halls; karta valfri.
- **Extern cross-repo-publicering** (U15) → generisk `external_publish`-config.
- **Klubb-app-target** (aggregat över åldersgrupper) + klass-i-filter.

## Felhantering
0 lag för `club_id` → tydligt fel. Ohärledd `api_host` → be om input. `age=0`-grupper →
PR-varning (skapa dem inte). Okänd regel → default + notis. Bevara hash-vaktad idempotens.

## Test
Motorns befintliga tester porteras. Nya enhetstester för `discover.py` mot **inspelade
fixturer** (Potatiscupen + Åhus, sparade JSON-store). Acceptanstest: "dispatch Potatiscupen-
ID → PR med körbar U14-app **och** klubb-app".

## Faser
- **Fas 1** — motor som config-objekt (porta ahk-beach, bygg via cup.toml, ingen beteendeändring).
- **Fas 2** — `discover.py`: 2 ID → cup.toml + edge-cases.
- **Fas 3** — multi-cup-bygge + klubb-app + två-nivåers hubb + Pages-layout.
- **Fas 4** — `new-cup.yml` dispatch→PR.
- **Fas 5** — venue-abstraktion + branding/regel-config (finish-punkterna).
- **Fas 6** — post-mortem-hygien: staleness-monitor, syntetisk E2E, koppla in CF Worker-cron.

**Implementationsplanen täcker MVP = Fas 1–4 (inkl. klubb-appen).** Fas 5–6 = roadmap,
egna spec→plan-varv.

## Öppna beslut
- Repo-namn (arbetsnamn `cup-apps`).
- Ska Åhus-config läggas in som testfixtur i nya repot (levande Åhus står kvar i ahk-beach oavsett)?
- Exakt PR-automation (GitHub-token/behörighet för att öppna PR från Action).
