# Generaliseringstest — Potatiscupen 2026 (dry-run)

**Datum:** 2026-07-18 · **Metod:** isolerad git-worktree, byggt lokalt, rörde aldrig de
befintliga apparna/main. Se även [`post-mortem-2026-ahus-beach.md`](post-mortem-2026-ahus-beach.md)
avsnitt 10–11.

## TL;DR

Konsumentlagret generaliserar **mycket bra**. Med en **3-konstants config-ändring**
(`TOURNAMENT_ID`, `CLUB_ID`, `API_HOST`) + neutraliserad Åhus-specifik U15-logik byggde
pipelinen en komplett Alingsås-app-svit för Potatiscupen: **8 åldersgrupper, 43 lag,
177 matcher**, med tabeller, slutspel och korrekta datum ("Lördag 18 april"). En byggd
app (U12) renderade fullt (24 matcher, F12/P12). Inga kodändringar behövdes — bara config.

## Vad som transfererade rakt av

Schema, könsfilter, multi-hero, tabeller, slutspelsträd, ICS-kalendrar, hubb, färgregler,
livescore-plumbing (match-id + `MatchResult`), bakgrundsuppdatering. Samma cupmanager-
`results_api`, samma entitetstyper (Match/Team/MatchResult/Category/Arena/Playoff).
Endpointen svarar på både `potatiscupen.cupmanager.net` och egna domänen `potatiscupen.nu`.

## Anpassningspunkter som testet avslöjade (det verkliga utfallet)

1. **Regel-/formatdetektering är Åhus-specifik.** Åhus-kategorier bär "Classic"/"Mini";
   Potatiscupen gör det inte → `rule='?'` → föll till default-profil (funkade, men är ett
   antagande). *Åtgärd:* gör regel/format till **per-cup-config** (eller robustare härledning),
   inte ett suffix i kategorinamnet.
2. **Icke-ålders-kategorier hamnar fel.** "HFA (Handboll för alla)" saknar ålder → landade i
   en skräp-grupp **`u0`**. *Åtgärd:* hantera specialkategorier (exkludera eller egen etikett
   via config).
3. **Venue-modellen är beach-specifik (störst jobb).** Potatiscupen = **11 namngivna hallar**
   spridda över orten (Albert Hall, Alströmerhallen, Estrad, Hjälmareds, Lenahallen, Nolhaga,
   Noltorpshallen 1/2/3, Stadsskogshallen, Östlyckehallen). `_bana_num` drar ut en siffra →
   blandar "hallnamn" och "plan-nummer", och områdeskartan med banpositioner gäller inte alls.
   *Åtgärd:* en **hall-baserad venue-modell** (hallar på en ortskarta, eller bara hallnamn —
   som redan visas i schemat). Detta är den enskilt största per-cup-anpassningen.
4. **U15-cross-repo-publicering är Åhus-specifik.** Neutraliserades i testet. *Åtgärd:* i en mall
   ska "special-slug som publiceras externt" vara **opt-in config**, inte hårdkodat.
5. **Fler-helgs-struktur.** Potatiscupen spelas över två helger (17–19 april + 24–26 april,
   olika per ålder). Dag-etiketter hanterade det utan problem.

## Config-checklista för att rulla ut en ny cup (utkast)

**Obligatoriskt:** `TOURNAMENT_ID`, `API_HOST`, `CLUB_ID`, `CLUB_NAME`, `PAGES_PATH`.
**Branding:** färgpalett, logga, appnamn, analytics-token.
**Regel/format:** profil om ej Classic-default (punkt 1).
**Venue:** kart-/hallmodell + ev. banpositioner — mest jobb (punkt 3).
**Special:** hantering av icke-ålders-kategorier (punkt 2).
**Trupper:** valfritt (`roster_data`).
**Deploy:** mål-URL + ev. extern cross-repo-publicering (punkt 4).

## Verdikt

Generalisering är **mycket genomförbar**. Kärnan (läslagret) är redan mallbar; återstående
arbete är att lyfta punkt 1–4 till config och bygga en hall-baserad venue-modell. Uppskattat:
~1 dags config-ifiering + venue-modellen → en ny cup live. Potatiscupen är ett skarpt,
verkligt testfall (Alingsås spelar där) att göra det på.
