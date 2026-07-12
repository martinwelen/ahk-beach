# U15 in i delad pipeline (samma URL) – Implementationsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Låt `ahk-beach` bygga U15-appen med exakt samma kod som alla andra åldersgrupper och publicera den till den oförändrade URL:en `https://martinwelen.github.io/alingsas-ahus-beach-2026/`, med bevarad Trupp-flik.

**Architecture:** `ahk-beach` är enda källan. `build_apps.py`/`build_ics.py` bygger U15 till en staging-katalog `dist-u15/` (med U15:s externa og-bas och de gamla ICS-filnamnen). CI pushar `dist-u15/` till roten av `alingsas-ahus-beach-2026` via en deploy-nyckel. PWA-identiteten är relativ (`start_url:"."`, `scope:"./"`), så installerade appar uppdateras sömlöst på samma URL. Den gamla robotten avaktiveras.

**Tech Stack:** Python 3.12 (standardbibliotek, inga beroenden), pytest, GitHub Actions, SSH deploy key.

---

## Filstruktur

- **Skapa:** `roster_data.py` — statiska U15-trupper, keyade på ahk-beach team-slugs.
- **Skapa:** `scripts/deploy_u15.sh` — publicerar `dist-u15/` till det externa repot.
- **Modifiera:** `config.py` — U15-konstanter (slug, extern bas, staging-katalog).
- **Modifiera:** `template.py` — service worker städar gamla cachar på `activate`.
- **Modifiera:** `build_apps.py` — bygg U15 till `dist-u15/`; bädda in trupper via `__ROSTERS__`.
- **Modifiera:** `build_ics.py` — bygg U15-kalendrar till `dist-u15/ics/` med gamla filnamn.
- **Modifiera:** `.gitignore` — ignorera `dist-u15/` i ahk-beach.
- **Modifiera:** `.github/workflows/update.yml` — deploy-steg för U15.
- **Modifiera (separat repo):** `~/dev/ahusbeach/.github/workflows/update.yml` — avaktivera gamla roboten.
- **Test:** `tests/test_build_apps.py`, `tests/test_ics.py`, `tests/test_roster.py` (ny).

---

## Task 0: Deploy-nyckel (manuellt förkrav – utförs av Martin)

Detta steg kan inte automatiseras (kräver åtkomst till båda repona på GitHub).

- [ ] **Step 1: Generera ett nyckelpar**

Run:
```bash
ssh-keygen -t ed25519 -C "ahk-beach->alingsas-ahus-beach-2026" -f /tmp/u15_deploy -N ""
```
Skapar `/tmp/u15_deploy` (privat) och `/tmp/u15_deploy.pub` (publik).

- [ ] **Step 2: Lägg publika nyckeln som Deploy key i mål-repot**

I `martinwelen/alingsas-ahus-beach-2026` → Settings → Deploy keys → Add deploy key:
- Title: `ahk-beach publish`
- Key: innehållet i `/tmp/u15_deploy.pub`
- **Bocka i "Allow write access"** (obligatoriskt – annars kan inte push ske).

- [ ] **Step 3: Lägg privata nyckeln som secret i käll-repot**

I `martinwelen/ahk-beach` → Settings → Secrets and variables → Actions → New repository secret:
- Name: `U15_DEPLOY_KEY`
- Secret: hela innehållet i `/tmp/u15_deploy` (inkl. BEGIN/END-raderna).

- [ ] **Step 4: Ta bort de lokala nyckelfilerna**

Run:
```bash
rm -f /tmp/u15_deploy /tmp/u15_deploy.pub
```

---

## Task 1: U15-konstanter i config.py

**Files:**
- Modify: `config.py:13-15`

- [ ] **Step 1: Skriv failing test**

Skapa `tests/test_config_u15.py`:
```python
# -*- coding: utf-8 -*-
import config


def test_u15_constants_point_at_external_repo():
    assert config.U15_SLUG == "u15"
    assert config.U15_PAGES_BASE == "https://martinwelen.github.io/alingsas-ahus-beach-2026"
    assert config.U15_DIST == "dist-u15"
```

- [ ] **Step 2: Kör testet, verifiera FAIL**

Run: `python3 -m pytest tests/test_config_u15.py -v`
Expected: FAIL med `AttributeError: module 'config' has no attribute 'U15_SLUG'`.

- [ ] **Step 3: Lägg till konstanterna**

I `config.py`, direkt efter raden `PAGES_BASE = f"https://{PAGES_HOST}{PAGES_PATH}"` (rad 15), lägg till:
```python

# U15 bor på en egen, redan distribuerad URL (installerade appar får inte flytta).
# ahk-beach bygger U15 till en staging-katalog och publicerar den dit via CI.
U15_SLUG = "u15"
U15_PAGES_BASE = "https://martinwelen.github.io/alingsas-ahus-beach-2026"
U15_DIST = "dist-u15"
```

- [ ] **Step 4: Kör testet, verifiera PASS**

Run: `python3 -m pytest tests/test_config_u15.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config_u15.py
git commit -m "feat: U15-konstanter (extern bas + staging-katalog)"
```

---

## Task 2: Service worker städar gamla cachar (delad, no-op för live-appar)

Byter U15:s cache från `ahus-schema-v1` → `ahk-u15-v1`. Städlogiken raderar cachar
≠ aktuell på `activate`. Live-appar har bara sin egen `ahk-uXX-v1` → inget raderas → oförändrat beteende.

**Files:**
- Modify: `template.py:637-639`
- Test: `tests/test_build_apps.py`

- [ ] **Step 1: Skriv failing test**

Lägg till i `tests/test_build_apps.py`:
```python
def test_service_worker_purges_stale_caches():
    sw = build_apps.service_worker_js("u15")
    assert 'const C = "ahk-u15-v1";' in sw
    # activate raderar alla cachar utom den aktuella (C)
    assert "caches.keys()" in sw
    assert "caches.delete" in sw
    assert "k !== C" in sw
```

- [ ] **Step 2: Kör testet, verifiera FAIL**

Run: `python3 -m pytest tests/test_build_apps.py::test_service_worker_purges_stale_caches -v`
Expected: FAIL (`caches.keys()` saknas i mallen).

- [ ] **Step 3: Uppdatera SW-mallen**

I `template.py`, byt ut raden (rad 639):
```python
self.addEventListener("activate", e => self.clients.claim());
```
mot:
```python
self.addEventListener("activate", e => e.waitUntil(
  caches.keys().then(ks => Promise.all(ks.filter(k => k !== C).map(k => caches.delete(k))))
    .then(() => self.clients.claim())
));
```

- [ ] **Step 4: Kör hela SW-testgruppen, verifiera PASS**

Run: `python3 -m pytest tests/test_build_apps.py -k "service_worker" -v`
Expected: PASS (både `test_service_worker_has_unique_cache_name` och den nya).

- [ ] **Step 5: Commit**

```bash
git add template.py tests/test_build_apps.py
git commit -m "feat: service worker rensar gamla cachar på activate"
```

---

## Task 3: Porta trupp-data (remappade slugs) + bädda in via __ROSTERS__

**Files:**
- Create: `roster_data.py`
- Create: `tests/test_roster.py`
- Modify: `build_apps.py:81-96` (render_app) + ny helper

- [ ] **Step 1: Skapa roster_data.py (remappad till ahk-beach-slugs)**

Skapa `roster_data.py`:
```python
# roster_data.py
# -*- coding: utf-8 -*-
"""Spelartrupper per Alingsås-lag (statisk källa; cupmanager saknar spelardata).

Nycklar = ahk-beach team-slugs: u{ålder}-{kön}-{färg}. Per spelare: namn (krav),
valfritt nr (tröjnummer), pos ("MV"/"UT"), smek (smeknamn). Lag utan publicerad
trupp: tom lista. Trupp-fliken göms automatiskt tills minst ett lag har spelare.
"""

rosters = {
    "u15-p-bla": [
        {"namn": "Oskar Viklund", "pos": "UT"},
        {"namn": "Alfred Lindblad", "pos": "MV", "smek": "Affe"},
        {"namn": "Theodor Kangas", "pos": "UT"},
        {"namn": "Maurits Fridberg", "pos": "UT", "smek": "Marre"},
        {"namn": "Filip Holmgren", "pos": "UT"},
        {"namn": "Terje Hegge", "pos": "UT"},
    ],
    "u15-p-orange": [
        {"namn": "Olle Laas", "pos": "MV"},
        {"namn": "Hjalmar Oscarsson", "pos": "UT", "smek": "Hjalle"},
        {"namn": "Alexander Westberg", "pos": "UT"},
        {"namn": "Theodor Herou", "pos": "UT"},
        {"namn": "Fabian Mattsson", "pos": "UT", "smek": "Fabbe"},
        {"namn": "Frank Jannerland", "pos": "UT"},
    ],
    "u15-p-vit": [
        {"namn": "Samuel Welén", "pos": "MV"},
        {"namn": "Filip Landström", "pos": "UT"},
        {"namn": "Sixten Herbertsson", "pos": "UT"},
        {"namn": "Filip Larsson", "pos": "UT"},
        {"namn": "Liam Bergaoui", "pos": "UT"},
        {"namn": "Love Jönsson", "pos": "UT"},
    ],
    "u15-f-bla": [],
    "u15-f-gul": [],
    "u15-f-vit": [],
}
```

- [ ] **Step 2: Skriv failing test**

Skapa `tests/test_roster.py`:
```python
# -*- coding: utf-8 -*-
import build_apps


def _group(age_slug="u15", age=15):
    return {"age": age, "label": f"U{age}", "rule": "Classic",
            "profile": {"duration_min": 11, "has_results": True,
                        "has_tables": True, "has_playoffs": True},
            "teams": [{"id": 1, "slug": f"{age_slug}-p-bla", "team_name": "Blå",
                       "color": "#1f5fbf", "gender": "P"}],
            "matches": []}


def test_rosters_js_returns_players_for_group_teams():
    r = build_apps._rosters_js(_group())
    assert "u15-p-bla" in r
    assert {"namn": "Oskar Viklund", "pos": "UT"} in r["u15-p-bla"]


def test_rosters_js_empty_for_group_without_roster_data():
    r = build_apps._rosters_js(_group("u14", 14))
    assert r == {}


def test_render_app_embeds_rosters_not_empty_object_for_u15():
    import json
    html = build_apps.render_app(_group(), standings=None, base="b", updated="u")
    rosters = html.split("const ROSTERS = ", 1)[1].split(";\n", 1)[0]
    assert "Oskar Viklund" in rosters
    assert json.loads(rosters)["u15-p-bla"]


def test_render_app_keeps_empty_rosters_for_live_groups():
    html = build_apps.render_app(_group("u14", 14), standings=None, base="b", updated="u")
    rosters = html.split("const ROSTERS = ", 1)[1].split(";\n", 1)[0]
    assert rosters == "{}"
```

- [ ] **Step 3: Kör testet, verifiera FAIL**

Run: `python3 -m pytest tests/test_roster.py -v`
Expected: FAIL (`build_apps._rosters_js` finns inte; `ROSTERS` = `{}` för u15).

- [ ] **Step 4: Lägg till helper och koppla in __ROSTERS__**

I `build_apps.py`, lägg till import högst upp (efter `import template`):
```python
import roster_data
```
Lägg till helper (t.ex. efter `_teams_js`, före `_dates`):
```python
def _rosters_js(group):
    """Trupper för gruppens lag → {slug: [spelare]}. Tomt om ingen trupp finns."""
    slugs = {t["slug"] for t in group["teams"]}
    return {s: p for s, p in roster_data.rosters.items() if s in slugs}
```
Byt i `render_app` raden:
```python
            .replace("__ROSTERS__", "{}")
```
mot:
```python
            .replace("__ROSTERS__", json.dumps(_rosters_js(group), ensure_ascii=False))
```

- [ ] **Step 5: Kör testet, verifiera PASS**

Run: `python3 -m pytest tests/test_roster.py -v`
Expected: PASS (alla fyra).

- [ ] **Step 6: Commit**

```bash
git add roster_data.py build_apps.py tests/test_roster.py
git commit -m "feat: porta U15-trupper (remappade slugs) och bädda in via __ROSTERS__"
```

---

## Task 4: build_apps bygger U15 till dist-u15/ med extern bas

**Files:**
- Modify: `build_apps.py:15` (ta bort SKIP), `build_apps.py:110-134` (main)
- Modify: `tests/test_build_apps.py:73-90` (uppdatera befintligt test)

- [ ] **Step 1: Uppdatera det befintliga dir-testet till nytt beteende**

I `tests/test_build_apps.py`, byt ut hela `test_build_apps_writes_each_group_dir` (rad 73–90) mot:
```python
def test_build_apps_writes_each_group_dir(tmp_path, monkeypatch):
    data = {"meta": {"generated": "2026-06-26T00:00:00Z"},
            "groups": {"u14": _group("u14", "U14"), "u15": _group("u15", "U15")}}
    (tmp_path / "data.json").write_text(json.dumps(data), encoding="utf-8")
    for ic in ("icon-192.png", "icon-512.png", "icon-512-maskable.png",
               "icon-180.png", "favicon-32.png"):
        (tmp_path / ic).write_bytes(b"x")
    monkeypatch.setattr(build_apps, "ROOT", str(tmp_path))
    monkeypatch.setattr(build_apps, "DATA_JSON", str(tmp_path / "data.json"))
    monkeypatch.setattr(build_apps, "STANDINGS_JSON", str(tmp_path / "nope.json"))
    n = build_apps.main()
    assert (tmp_path / "u14" / "index.html").exists()
    assert (tmp_path / "u14" / "manifest.json").exists()
    assert (tmp_path / "u14" / "sw.js").exists()
    assert not (tmp_path / "u15").exists()                    # ingen lokal u15/
    assert (tmp_path / "dist-u15" / "index.html").exists()    # U15 → staging
    assert (tmp_path / "dist-u15" / "sw.js").exists()
    assert n == 2
```
Obs: `_group()` i denna fil sätter `label` som andra argument. `_group("u15", "U15")` ger `age=14`; det spelar ingen roll för dir-testet (bara slug/label används för utdatavägen).

- [ ] **Step 2: Verifiera att testet nu failar**

Run: `python3 -m pytest tests/test_build_apps.py::test_build_apps_writes_each_group_dir -v`
Expected: FAIL (u15 skippas fortfarande, `dist-u15` saknas, n==1).

- [ ] **Step 3: Ta bort skip och gör U15-grenen i main()**

I `build_apps.py`, byt ut rad 15:
```python
SKIP_AGE_SLUGS = {"u15"}                  # U15 bor kvar i alingsas-ahus-beach-2026
```
mot:
```python
# (U15 byggs nu också – till config.U15_DIST, publiceras till det externa repot.)
```
I `main()`, byt ut raderna:
```python
    for age_slug, group in data.get("groups", {}).items():
        if age_slug in SKIP_AGE_SLUGS:
            continue
        out_dir = os.path.join(ROOT, age_slug)
        os.makedirs(out_dir, exist_ok=True)
        base = f"{config.PAGES_BASE}/{age_slug}"
```
mot:
```python
    for age_slug, group in data.get("groups", {}).items():
        if age_slug == config.U15_SLUG:
            out_dir = os.path.join(ROOT, config.U15_DIST)
            base = config.U15_PAGES_BASE
        else:
            out_dir = os.path.join(ROOT, age_slug)
            base = f"{config.PAGES_BASE}/{age_slug}"
        os.makedirs(out_dir, exist_ok=True)
```

- [ ] **Step 4: Kör hela build_apps-testfilen, verifiera PASS**

Run: `python3 -m pytest tests/test_build_apps.py -v`
Expected: PASS (alla, inkl. det uppdaterade dir-testet).

- [ ] **Step 5: Commit**

```bash
git add build_apps.py tests/test_build_apps.py
git commit -m "feat: build_apps bygger U15 till dist-u15 med extern og-bas"
```

---

## Task 5: build_ics bygger U15-kalendrar med gamla filnamn

**Files:**
- Modify: `build_ics.py:14` (ta bort SKIP), `build_ics.py:81-106` (main) + ny helper
- Test: `tests/test_ics.py`

- [ ] **Step 1: Skriv failing test för filnamns-mappning**

Lägg till i `tests/test_ics.py`:
```python
def test_u15_ics_filename_maps_to_legacy_name():
    assert build_ics.u15_ics_name("u15-p-bla") == "alingsas-p15-bla.ics"
    assert build_ics.u15_ics_name("u15-f-gul") == "alingsas-f15-gul.ics"
    assert build_ics.u15_ics_name("u15-p-orange") == "alingsas-p15-orange.ics"
```

- [ ] **Step 2: Kör testet, verifiera FAIL**

Run: `python3 -m pytest tests/test_ics.py::test_u15_ics_filename_maps_to_legacy_name -v`
Expected: FAIL (`build_ics.u15_ics_name` finns inte).

- [ ] **Step 3: Lägg till mappnings-helper**

I `build_ics.py`, lägg till efter `slug_ascii` (rad 29):
```python
def u15_ics_name(slug):
    """ahk-beach-slug → gammalt U15-filnamn. 'u15-p-bla' → 'alingsas-p15-bla.ics'."""
    parts = slug.split("-")                 # ["u15", "p", "bla"]
    age = parts[0][1:]                      # "15"
    gender = parts[1]                       # "p"
    rest = "-".join(parts[2:])              # "bla"
    return f"alingsas-{gender}{age}-{rest}.ics"
```

- [ ] **Step 4: Kör testet, verifiera PASS**

Run: `python3 -m pytest tests/test_ics.py::test_u15_ics_filename_maps_to_legacy_name -v`
Expected: PASS.

- [ ] **Step 5: Skriv failing test för U15-utdatavägar**

Lägg till i `tests/test_ics.py`:
```python
import json
import build_ics as _bi


def test_main_writes_u15_with_legacy_names(tmp_path, monkeypatch):
    data = {"meta": {"seq": 1}, "groups": {"u15": {
        "label": "U15", "profile": {"duration_min": 11},
        "teams": [{"slug": "u15-p-bla", "team_name": "Alingsås HK P15 Blå"}],
        "matches": [{"slug": "u15-p-bla", "mots": "Lugi", "grupp": "G1",
                     "start_ms": 1783585800000, "bana": 1, "hemma": "Blå",
                     "borta": "Lugi", "hb": "Hemma", "tid": "10:30"}]}}}
    (tmp_path / "data.json").write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(_bi, "ROOT", str(tmp_path))
    monkeypatch.setattr(_bi, "DATA_JSON", str(tmp_path / "data.json"))
    _bi.main()
    ics_dir = tmp_path / "dist-u15" / "ics"
    assert (ics_dir / "alingsas-alla.ics").exists()
    assert (ics_dir / "alingsas-p15-bla.ics").exists()
    assert not (tmp_path / "u15").exists()
```

- [ ] **Step 6: Kör testet, verifiera FAIL**

Run: `python3 -m pytest tests/test_ics.py::test_main_writes_u15_with_legacy_names -v`
Expected: FAIL (u15 skippas; skriver till `u15/ics/` med namn `alla.ics`).

- [ ] **Step 7: Ta bort skip och gör U15-grenen i main()**

`config` importeras redan (rad 10). Ta bort rad 14 helt:
```python
SKIP = {"u15"}
```
Slutresultat: ingen `SKIP`-konstant kvar i filen.

I `main()`, byt ut blocket (rad 86–105):
```python
    for age_slug, g in data.get("groups", {}).items():
        if age_slug in SKIP:
            continue
        out_dir = os.path.join(ROOT, age_slug, "ics")
        os.makedirs(out_dir, exist_ok=True)
        dur = g["profile"]["duration_min"]
        by_team = {}
        for m in g["matches"]:
            by_team.setdefault(m["slug"], []).append(m)
        with open(os.path.join(out_dir, "alla.ics"), "w", encoding="utf-8", newline="") as f:
            f.write(build_calendar(g["matches"], f"Alingsås HK {g['label']} (alla) – Åhus Beach",
                                   f"Alla lag i {g['label']}. {SOURCE_NOTE}",
                                   g["label"], dur, seq, dtstamp))
        for t in g["teams"]:
            with open(os.path.join(out_dir, f"{t['slug']}.ics"), "w",
                      encoding="utf-8", newline="") as f:
                f.write(build_calendar(by_team.get(t["slug"], []),
                                       f"{t['team_name']} – Åhus Beach",
                                       f"{g['label']}. {SOURCE_NOTE}",
                                       g["label"], dur, seq, dtstamp))
```
mot:
```python
    for age_slug, g in data.get("groups", {}).items():
        if age_slug == config.U15_SLUG:
            out_dir = os.path.join(ROOT, config.U15_DIST, "ics")
            alla_name = "alingsas-alla.ics"
            name_for = u15_ics_name
        else:
            out_dir = os.path.join(ROOT, age_slug, "ics")
            alla_name = "alla.ics"
            name_for = lambda slug: f"{slug}.ics"
        os.makedirs(out_dir, exist_ok=True)
        dur = g["profile"]["duration_min"]
        by_team = {}
        for m in g["matches"]:
            by_team.setdefault(m["slug"], []).append(m)
        with open(os.path.join(out_dir, alla_name), "w", encoding="utf-8", newline="") as f:
            f.write(build_calendar(g["matches"], f"Alingsås HK {g['label']} (alla) – Åhus Beach",
                                   f"Alla lag i {g['label']}. {SOURCE_NOTE}",
                                   g["label"], dur, seq, dtstamp))
        for t in g["teams"]:
            with open(os.path.join(out_dir, name_for(t["slug"])), "w",
                      encoding="utf-8", newline="") as f:
                f.write(build_calendar(by_team.get(t["slug"], []),
                                       f"{t['team_name']} – Åhus Beach",
                                       f"{g['label']}. {SOURCE_NOTE}",
                                       g["label"], dur, seq, dtstamp))
```

- [ ] **Step 8: Kör hela ICS-testfilen, verifiera PASS**

Run: `python3 -m pytest tests/test_ics.py -v`
Expected: PASS (alla).

- [ ] **Step 9: Commit**

```bash
git add build_ics.py tests/test_ics.py
git commit -m "feat: build_ics bygger U15-kalendrar till dist-u15 med gamla filnamn"
```

---

## Task 6: Ignorera dist-u15/ i ahk-beach

Så att workflowens `git add -A` (ahk-beach-committen) inte råkar committa staging-katalogen och exponera den på ahk-beach:s egen URL.

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Lägg till ignore-rad**

Run:
```bash
cd ~/dev/ahk-beach
printf '\n# U15 byggs till en staging-katalog och publiceras till det externa repot.\ndist-u15/\n' >> .gitignore
```

- [ ] **Step 2: Verifiera att den ignoreras**

Run:
```bash
mkdir -p dist-u15 && touch dist-u15/probe && git status --porcelain dist-u15 ; rm -rf dist-u15
```
Expected: ingen utdata (katalogen är ignorerad).

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: ignorera dist-u15 staging-katalog"
```

---

## Task 7: Deploy-skript + CI-steg som publicerar U15

**Files:**
- Create: `scripts/deploy_u15.sh`
- Modify: `.github/workflows/update.yml`

- [ ] **Step 1: Skapa deploy-skriptet**

Skapa `scripts/deploy_u15.sh`:
```bash
#!/usr/bin/env bash
# Publicerar dist-u15/ till roten av alingsas-ahus-beach-2026 (behåller repots
# övriga filer/historik). Kräver env DEPLOY_KEY (privat SSH deploy key med skriv).
set -euo pipefail

REPO="git@github.com:martinwelen/alingsas-ahus-beach-2026.git"
WORK="$(mktemp -d)"

if [ ! -d dist-u15 ]; then
  echo "dist-u15/ saknas – inget att publicera."; exit 0
fi

mkdir -p ~/.ssh
printf '%s\n' "$DEPLOY_KEY" > ~/.ssh/u15_deploy
chmod 600 ~/.ssh/u15_deploy
export GIT_SSH_COMMAND="ssh -i $HOME/.ssh/u15_deploy -o StrictHostKeyChecking=no"

git clone --depth 1 "$REPO" "$WORK"
# Kopiera app-filerna över; behåller allt annat (källkod/docs) i mål-repot.
cp -R dist-u15/. "$WORK"/

cd "$WORK"
git config user.name "ahk-beach-bot"
git config user.email "github-actions[bot]@users.noreply.github.com"
git add -A
if git diff --cached --quiet; then
  echo "U15 oförändrad – inget att publicera."
else
  git commit -m "U15-uppdatering från ahk-beach ($(date -u '+%Y-%m-%d %H:%M UTC'))"
  git push origin HEAD:main
  echo "U15 publicerad."
fi
```

- [ ] **Step 2: Gör skriptet körbart**

Run:
```bash
chmod +x scripts/deploy_u15.sh
```

- [ ] **Step 3: Lägg till deploy-steget i workflowen**

I `.github/workflows/update.yml`, efter steget **"Committa och publicera"**, lägg till (samma indentering som övriga steg, dvs. 6 mellanslag före `- name`):
```yaml
      - name: Publicera U15 till alingsas-ahus-beach-2026
        if: steps.changed.outputs.changed == 'true'
        env:
          DEPLOY_KEY: ${{ secrets.U15_DEPLOY_KEY }}
        run: bash scripts/deploy_u15.sh
```

- [ ] **Step 4: Validera YAML-syntaxen**

Run:
```bash
python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/update.yml')); print('YAML OK')"
```
Expected: `YAML OK`. (Om `yaml` saknas: `python3 -m pip install pyyaml` eller hoppa – GitHub validerar vid push.)

- [ ] **Step 5: Commit**

```bash
git add scripts/deploy_u15.sh .github/workflows/update.yml
git commit -m "feat: CI publicerar U15 till det externa repot via deploy key"
```

---

## Task 8: Avaktivera den gamla roboten (separat repo)

Annars skriver två robotar över `alingsas-ahus-beach-2026` och kämpar mot varandra.

**Files:**
- Modify (separat repo): `~/dev/ahusbeach/.github/workflows/update.yml`

- [ ] **Step 1: Ta bort schema-triggrarna, behåll bara manuell**

I `~/dev/ahusbeach/.github/workflows/update.yml`, byt ut `on:`-blocket (rad 4–8):
```yaml
on:
  schedule:
    - cron: "*/30 * * * *"        # normalt: var 30:e minut (no-op om inget ändrats)
    - cron: "*/10 * 17,18 7 *"    # turneringshelgen 17-18 juli: var 10:e minut
  workflow_dispatch:               # + manuell "Run workflow"-knapp
```
mot:
```yaml
# PENSIONERAD: U15 byggs och publiceras numera av ahk-beach (single source of
# truth). Denna robot är avstängd så den inte skriver över den publiceringen.
# Endast manuell körning kvar (nödfall), aldrig automatisk.
on:
  workflow_dispatch:
```

- [ ] **Step 2: Verifiera YAML**

Run:
```bash
python3 -c "import yaml; yaml.safe_load(open('$HOME/dev/ahusbeach/.github/workflows/update.yml')); print('YAML OK')"
```
Expected: `YAML OK`.

- [ ] **Step 3: Commit och pusha i det separata repot**

```bash
cd ~/dev/ahusbeach
git add .github/workflows/update.yml
git commit -m "chore: pensionera U15-roboten (ahk-beach publicerar nu U15)"
git push
cd ~/dev/ahk-beach
```

---

## Task 9: Verifiering och cutover

U15 spelar inte just nu → säkert att bygga om/cutover:a. Live-klasserna får inte påverkas.

- [ ] **Step 1: Kör hela testsviten**

Run: `python3 -m pytest`
Expected: alla test PASS.

- [ ] **Step 2: Bygg allt lokalt från färsk data**

Run:
```bash
cd ~/dev/ahk-beach
python3 build_apps.py && python3 build_ics.py && python3 build_hub.py
```
Expected: `dist-u15/index.html`, `dist-u15/manifest.json`, `dist-u15/sw.js`,
`dist-u15/ics/alingsas-alla.ics` + `dist-u15/ics/alingsas-p15-bla.ics` m.fl. finns.

- [ ] **Step 3: Verifiera att live-appar är oförändrade (utom avsedd SW-städning)**

Run:
```bash
git status --porcelain u8 u10 u11 u12 u13 u14 u16 u17 u18 2>/dev/null | grep -E 'index\.html|manifest' || echo "Inga index/manifest-ändringar i live-appar"
git diff -- u14/sw.js | head -20
```
Expected: **inga** `index.html`/`manifest.json`-ändringar för live-grupperna
(trupp = tomt → oförändrat). `sw.js` visar **endast** den nya activate-städningen.
Om en live-apps `index.html` ändrats av annat än data → STOPP, undersök.

- [ ] **Step 4: Jämför U15-appen mot den nuvarande live-U15:an**

Run:
```bash
ls dist-u15 dist-u15/ics
grep -c "Oskar Viklund" dist-u15/index.html   # trupp-data med (>=1)
grep -o 'ahk-u15-v1' dist-u15/sw.js            # nytt cache-namn
grep -o 'alingsas-ahus-beach-2026' dist-u15/index.html | head -1  # og:url-bas
```
Expected: trupp finns (>=1), SW-cache = `ahk-u15-v1`, og-bas pekar på gamla URL:en.
Öppna ev. `dist-u15/index.html` i webbläsare och kontrollera flikarna
Schema / Tabeller / Slutspel / Trupp + könsfilter mot nuvarande live-U15.

- [ ] **Step 5: Städa lokala staging-artefakter (ignoreras, men håll rent)**

Run: `rm -rf dist-u15`

- [ ] **Step 6: Merga grenen till main och pusha (utlöser CI-cutover)**

Följ `superpowers:finishing-a-development-branch` för slutförandet. Vid merge till
`main` bygger CI om och `scripts/deploy_u15.sh` publicerar U15 till det gamla
repot – första cutover:n sker då. (Manuell trigger vid behov:
`gh workflow run "Uppdatera schema"`.)

- [ ] **Step 7: Verifiera cutover live på oförändrad URL**

Efter att CI kört: öppna `https://martinwelen.github.io/alingsas-ahus-beach-2026/`
i en webbläsare, hård-ladda (SW uppdateras), och bekräfta:
- Appen visar samma innehåll som ahk-beach:s U15-bygge (inkl. Trupp-fliken).
- På en enhet där appen är installerad på hemskärmen: öppna den, verifiera att den
  uppdateras och **fortfarande startar standalone** (ingen scope-brytning).
- Prenumerera/uppdatera en kalender (`…/ics/alingsas-alla.ics`) och bekräfta att den svarar.

---

## Noteringar / accepterade avvägningar

- **ICS-UID:er ändras engångsvis.** Gamla UID:er var `…@ahusbeach2026.cupmanager.net`
  med slug `p15-bla`; nya är `…@ahusbeach.cupmanager.net` med `u15-p-bla`. Redan
  prenumererade kalendrar läser om U15-eventen en gång. Ofarligt eftersom U15 inte
  spelar just nu (inga liveresultat störs).
- **Manifest-namn.** U15 får `name: "AHK U15"` (som syskonapparna) i stället för
  gamla `"AHK Åhus Beach 2026"`. Installerade appar byter inte hemskärmsnamn; endast
  nya installationer påverkas. Acceptabelt.
- **Ikoner.** U15 får ahk-beach:s ikon-assets. `cp -R dist-u15/.` skriver bara över
  filer som finns i bygget; övriga assets i mål-repot (t.ex. `Alingsas_HK_logo.svg`)
  bevaras, så inget som index.html refererar försvinner.
- **Mall-/kodändringar plockas inte upp av data-roboten** (endast data.json/standings.json
  triggar bygge). Första cutover:n sker vid merge/manuell trigger; därefter publiceras
  U15 automatiskt när matchdata ändras.
