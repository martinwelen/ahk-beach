# cup-apps MVP (Fas 1–4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A new platform repo where `workflow_dispatch(tournamentId, clubId)` auto-derives a cup config, builds a runnable PWA suite (per-age-group apps + one club-wide "all teams" app + hubs), and opens a PR to review.

**Architecture:** A config-object-driven `engine/` (ported from `ahk-beach`, `config.py` globals replaced by a `CupConfig` loaded from `cups/<slug>/cup.toml`), a `discover.py` that turns two IDs into a `cup.toml` + report, and a `new-cup.yml` Action that runs discover → build → open PR. Output goes to `dist/<slug>/` served by GitHub Pages.

**Tech Stack:** Python 3.12 (stdlib only — `tomllib` for reading, hand-written TOML writer; no deps), vanilla JS/CSS template, GitHub Actions, GitHub Pages.

**Source of truth for ported code:** the current `ahk-beach` repo. "Port verbatim" = copy that file's exact contents unless a diff is given. `ahk-beach` stays frozen as Åhus history; this is a new repo.

---

## File Structure

```
engine/
  cupconfig.py      # CupConfig dataclass + load_cup(path) from cup.toml  [NEW]
  api.py            # cupmanager client — takes CupConfig  [PORT + refactor]
  derive.py         # slugify, parse_category (robust), colors  [PORT + harden]
  rules.py          # rule_profile(name) + config override  [PORT + refactor]
  fetch_data.py     # store → cup data dict — takes CupConfig, returns dict (no file globals)  [PORT + refactor]
  fetch_standings.py# tables/playoffs — takes CupConfig  [PORT + refactor]
  template.py       # HTML/JS template (+ class-in-filter for club app)  [PORT + small change]
  build_apps.py     # per-age apps + club-wide app — takes CupConfig  [PORT + refactor + NEW target]
  build_ics.py      # calendars — takes CupConfig  [PORT + refactor]
  build_hub.py      # per-cup hub  [PORT + refactor]
  build_cup.py      # orchestrator: build_cup(slug) → dist/<slug>/  [NEW]
  discover.py       # (tid, cid, host) → cup.toml + report  [NEW]
  tomlwrite.py      # minimal deterministic TOML writer (stdlib has no writer)  [NEW]
cups/<slug>/cup.toml
tests/              # pytest, incl. recorded fixtures tests/fixtures/*.json
dist/<slug>/        # build output (gitignored except via Pages workflow)
.github/workflows/  new-cup.yml, update.yml
build_hub_root.py   # top-level cup-list hub  [NEW]
```

`CupConfig` is the interface every engine module depends on. Defined once (Task 2), threaded everywhere.

---

## Task 1: Scaffold the new repo

**Files:**
- Create: new repo `cup-apps/` (working name), `engine/`, `cups/`, `tests/`, `.github/workflows/`, `.gitignore`, `.nojekyll`, `README.md`

- [ ] **Step 1: Create repo + dirs**

```bash
mkdir -p ~/dev/cup-apps/{engine,cups,tests/fixtures,.github/workflows}
cd ~/dev/cup-apps && git init -q
printf 'dist/\n__pycache__/\n*.pyc\n' > .gitignore
touch .nojekyll
printf '# cup-apps\n\nGeneraliserad cupmanager-konsument-plattform. Ange tournamentId + clubId → PR med körbar app-svit.\nSe docs/ (spec) och plans/.\n' > README.md
```

- [ ] **Step 2: Port engine files verbatim (baseline before refactor)**

Copy these from `~/dev/ahk-beach/` into `~/dev/cup-apps/engine/` **unchanged** for now: `api.py`, `derive.py`, `rules.py`, `fetch_data.py`, `fetch_standings.py`, `template.py`, `build_apps.py`, `build_ics.py`, `build_hub.py`. Copy `~/dev/ahk-beach/tests/` into `~/dev/cup-apps/tests/`. Do NOT copy `config.py` (replaced by cup.toml).

```bash
cp ~/dev/ahk-beach/{api,derive,rules,fetch_data,fetch_standings,template,build_apps,build_ics,build_hub}.py ~/dev/cup-apps/engine/
cp -r ~/dev/ahk-beach/tests/* ~/dev/cup-apps/tests/
```

- [ ] **Step 3: Commit**

```bash
cd ~/dev/cup-apps && git add -A && git commit -q -m "chore: scaffold cup-apps + port engine files verbatim"
```

---

## Task 2: `CupConfig` + `cup.toml` loader

**Files:**
- Create: `engine/cupconfig.py`, `tests/test_cupconfig.py`, `cups/_example/cup.toml`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cupconfig.py
import os, textwrap
from engine.cupconfig import load_cup, CupConfig

def _write(tmp_path, body):
    p = tmp_path / "cup.toml"; p.write_text(textwrap.dedent(body), encoding="utf-8"); return str(p)

def test_load_cup_required_and_defaults(tmp_path):
    path = _write(tmp_path, '''
        slug = "potatiscupen"
        tournament_id = "67026461"
        club_id = 72525561
        api_host = "potatiscupen.cupmanager.net"
        cup_name = "Potatiscupen 2026"
        club_name = "Alingsås HK"
        utc_offset = 2
    ''')
    c = load_cup(path)
    assert isinstance(c, CupConfig)
    assert c.tournament_id == "67026461" and c.club_id == 72525561
    assert c.api_host == "potatiscupen.cupmanager.net"
    assert c.pages_base.endswith("/potatiscupen")     # default derived from slug
    assert c.venue_mode == "halls"                     # default when unset
    assert c.palette and c.color_map                   # sane branding defaults present
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/dev/cup-apps && python3 -m pytest tests/test_cupconfig.py -v`
Expected: FAIL with `ModuleNotFoundError: engine.cupconfig`

- [ ] **Step 3: Implement `engine/cupconfig.py`**

```python
# engine/cupconfig.py
# -*- coding: utf-8 -*-
"""CupConfig: per-cup konfiguration laddad ur cups/<slug>/cup.toml."""
import tomllib
from dataclasses import dataclass, field

DEFAULT_PALETTE = ["#1f5fbf", "#e8730c", "#2f9e44", "#d22f27", "#9c36b5", "#f2bd0c"]
DEFAULT_COLOR_MAP = {
    "bla": "#1f5fbf", "vit": "#c9c2b4", "svart": "#23303a", "orange": "#e8730c",
    "gul": "#f2bd0c", "rod": "#d22f27", "gron": "#2f9e44", "rosa": "#e864a4",
}
PAGES_HOST = "martinwelen.github.io"
PAGES_REPO = "cup-apps"

@dataclass
class CupConfig:
    slug: str
    tournament_id: str
    club_id: int
    api_host: str
    cup_name: str = ""
    club_name: str = ""
    utc_offset: int = 2
    venue_mode: str = "halls"                 # "halls" | "beach_court"
    rule_override: str = ""                    # tomt = härled/def
    club_blue: str = "#1f5fbf"
    palette: list = field(default_factory=lambda: list(DEFAULT_PALETTE))
    color_map: dict = field(default_factory=lambda: dict(DEFAULT_COLOR_MAP))
    external_publish: dict = field(default_factory=dict)  # opt-in cross-repo (U15-mönster)

    @property
    def pages_base(self):
        return f"https://{PAGES_HOST}/{PAGES_REPO}/{self.slug}"

def load_cup(path):
    with open(path, "rb") as f:
        d = tomllib.load(f)
    for req in ("slug", "tournament_id", "club_id", "api_host"):
        if req not in d:
            raise ValueError(f"cup.toml saknar obligatoriskt fält: {req}")
    known = CupConfig.__dataclass_fields__.keys()
    return CupConfig(**{k: v for k, v in d.items() if k in known})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_cupconfig.py -v`
Expected: PASS (2 assertions on defaults + required fields)

- [ ] **Step 5: Commit**

```bash
git add engine/cupconfig.py tests/test_cupconfig.py && git commit -q -m "feat: CupConfig + cup.toml loader with branding/venue defaults"
```

---

## Task 3: Refactor `api.py` to take `CupConfig`

**Files:**
- Modify: `engine/api.py` (replace `import config` module-globals with a passed `cfg`)
- Test: `tests/test_api.py` (update)

- [ ] **Step 1: Update the test to pass a config**

Replace the top of `tests/test_api.py` so it builds a `CupConfig` and passes it:

```python
from engine.cupconfig import CupConfig
from engine import api

CFG = CupConfig(slug="t", tournament_id="70944382", club_id=73383031,
                api_host="ahusbeachhandboll.cupmanager.net")

def test_match_query_includes_tournament_id():
    q = api.match_query(CFG, 300, 0)
    assert "tournamentId:70944382" in q
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_api.py::test_match_query_includes_tournament_id -v`
Expected: FAIL (`match_query()` currently takes `(limit, offset)`, not `(cfg, limit, offset)`)

- [ ] **Step 3: Refactor `engine/api.py`**

Remove `import config` and the module-level `_API`. Thread `cfg` through. Exact new signatures:

```python
def _api_url(cfg, call):
    import urllib.parse
    return (f"https://{cfg.api_host}/rest/results_api/call"
            f"?call={urllib.parse.quote(call)}&lang=sv&tournamentId={cfg.tournament_id}")

def match_query(cfg, limit, offset):
    return (
        "MatchWindow({{limit:{l},offset:{o},tournamentId:{t}}})"
        "{{matches:[{{... on Match:{{start:{{}},arena:{{}},"
        "away:{{team:{{}}}},division:{{category:{{}},name:{{}}}},"
        "home:{{team:{{}}}},result:{{}}}}}}]}}"
    ).format(l=limit, o=offset, t=cfg.tournament_id)

def call(cfg, query, retries=4):
    import json, time, urllib.request
    url = _api_url(cfg, query)
    req = urllib.request.Request(url, headers={"accept": "application/json", "user-agent": "cup-apps-bot/1.0"})
    last = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e; time.sleep(2 + 2 * i)
    raise last

def fetch_store(cfg):
    PAGE, MAX_PAGES = 300, 100
    store, offset = {}, 0
    for _ in range(MAX_PAGES):
        resp = call(cfg, match_query(cfg, PAGE, offset)).get("responses", {})
        page = 0
        for k, v in resp.items():
            if isinstance(v, dict) and isinstance(v.get("entity"), dict):
                store[k] = v["entity"]
                if v["entity"].get("__typename") == "Match":
                    page += 1
        if page < PAGE:
            break
        offset += PAGE
    return store
```

Keep `ref_id`, `name_of`, `store_get` unchanged (they take no config).

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/api.py tests/test_api.py && git commit -q -m "refactor: api.py takes CupConfig instead of module globals"
```

---

## Task 4: Refactor `derive.py` colors + `rules.py` to use `CupConfig`

**Files:**
- Modify: `engine/derive.py` (`derive_group_colors(group, cfg)`), `engine/rules.py` (`rule_profile(name, cfg)`)
- Test: `tests/test_derive.py`, `tests/test_rules.py`

- [ ] **Step 1: Update tests to pass cfg**

```python
# tests/test_rules.py (add)
from engine.cupconfig import CupConfig
from engine import rules
CFG = CupConfig(slug="t", tournament_id="1", club_id=1, api_host="h")

def test_rule_profile_defaults_when_unknown():
    p = rules.rule_profile("?", CFG)
    assert p["has_results"] is True and p["duration_min"] >= 1

def test_rule_override_from_config():
    cfg = CupConfig(slug="t", tournament_id="1", club_id=1, api_host="h", rule_override="Mini")
    assert rules.rule_profile("?", cfg)["has_tables"] is False
```

- [ ] **Step 2: Run to verify fail**

Run: `python3 -m pytest tests/test_rules.py -v`
Expected: FAIL (`rule_profile` takes one arg today)

- [ ] **Step 3: Implement**

In `engine/rules.py`, change signature to `rule_profile(name, cfg)`. At the top of the function: `name = cfg.rule_override or name`. Keep the existing profile table; `?`/unknown → the existing `_DEFAULT`. In `engine/derive.py`, change `derive_group_colors(group)` → `derive_group_colors(group, cfg)` and replace references to `config.CLUB_BLUE`/`config.COLOR_MAP`/`config.PALETTE` with `cfg.club_blue`/`cfg.color_map`/`cfg.palette`. Remove `import config`.

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/test_rules.py tests/test_derive.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/rules.py engine/derive.py tests/test_rules.py tests/test_derive.py && git commit -q -m "refactor: rules + colors take CupConfig (rule override supported)"
```

---

## Task 5: Refactor `fetch_data.py` to return a data dict (no globals, no file writes)

**Files:**
- Modify: `engine/fetch_data.py` — `build_cup_data(cfg) -> dict`
- Test: `tests/test_fetch_data.py`

- [ ] **Step 1: Write failing test using a recorded fixture**

First record a small fixture (one-time): `python3 -c "import json,urllib.request,urllib.parse; ..."`. To keep the test offline, add `tests/fixtures/potatis_store.json` (a trimmed store dumped from `api.fetch_store(cfg)` for Potatiscupen — commit it). Then:

```python
# tests/test_fetch_data.py (new core test)
import json
from engine.cupconfig import CupConfig
from engine import fetch_data

CFG = CupConfig(slug="potatiscupen", tournament_id="67026461", club_id=72525561,
                api_host="potatiscupen.cupmanager.net", utc_offset=2)

def test_build_cup_data_groups_and_matches(monkeypatch):
    store = json.load(open("tests/fixtures/potatis_store.json", encoding="utf-8"))
    monkeypatch.setattr("engine.api.fetch_store", lambda cfg: store)
    data = fetch_data.build_cup_data(CFG)
    assert data["groups"], "should discover age groups"
    # club filter worked: every group has teams, all Alingsås
    assert all(g["teams"] for g in data["groups"].values())
    assert "u0" not in data["groups"], "non-age categories must not create a u0 group"
```

- [ ] **Step 2: Run to verify fail**

Run: `python3 -m pytest tests/test_fetch_data.py::test_build_cup_data_groups_and_matches -v`
Expected: FAIL (`build_cup_data` not defined)

- [ ] **Step 3: Refactor `engine/fetch_data.py`**

Remove `import config`, `DATA_JSON`, `write_if_changed`, `main`, and all file I/O. Thread `cfg`:
- `build_team_registry(store, cfg)` — filter `api.ref_id(e.get("club")) != cfg.club_id`; call `derive.derive_group_colors(group, cfg)`.
- `normalize_match(e, store, reg_by_id, cfg)` — use `cfg.utc_offset` for the `_CEST` tz; keep video only when `cfg.venue_mode == "beach_court" and bana in (1,2)` (indoor cups skip video probing unless configured).
- Add `build_cup_data(cfg) -> {"groups": {...}, "meta": {...}}`:

```python
def build_cup_data(cfg):
    store = api.fetch_store(cfg)
    registry = build_team_registry(store, cfg)
    if not registry:
        raise ValueError(f"0 lag för club_id {cfg.club_id} i tournament {cfg.tournament_id}")
    match_entities = [e for e in store.values() if e.get("__typename") == "Match"]
    groups = bucket_by_age_group(registry, match_entities, store, cfg)
    groups = {a: g for a, g in groups.items() if a != "u0"}   # drop non-age (flagged by discover)
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    return {"groups": groups,
            "meta": {"cup": cfg.cup_name, "club_id": cfg.club_id,
                     "generated": now.isoformat(timespec="seconds"),
                     "data_hash": _hash_groups(groups)}}
```

Keep `_hash_groups` (unchanged — already includes id/video/runda/result). `bucket_by_age_group` gains a `cfg` param, passed to `normalize_match`.

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/test_fetch_data.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/fetch_data.py tests/test_fetch_data.py tests/fixtures/potatis_store.json && git commit -q -m "refactor: fetch_data.build_cup_data(cfg) returns dict; drop non-age groups"
```

---

## Task 6: Refactor `fetch_standings.py` to `build_standings(cfg) -> dict`

**Files:**
- Modify: `engine/fetch_standings.py`
- Test: `tests/test_standings.py`

- [ ] **Step 1: Write failing test**

```python
def test_build_standings_returns_by_age(monkeypatch):
    import json
    from engine.cupconfig import CupConfig
    from engine import fetch_standings
    store = json.load(open("tests/fixtures/potatis_store.json", encoding="utf-8"))
    monkeypatch.setattr("engine.api.fetch_store", lambda cfg: store)
    cfg = CupConfig(slug="p", tournament_id="67026461", club_id=72525561, api_host="h")
    st = fetch_standings.build_standings(cfg)
    assert "by_age" in st
```

- [ ] **Step 2: Run to verify fail** — `python3 -m pytest tests/test_standings.py -v` → FAIL (`build_standings` missing).

- [ ] **Step 3: Implement** — mirror Task 5: remove globals/file I/O, add `build_standings(cfg) -> {"by_age": {...}}` that calls `api.fetch_store(cfg)` (or accepts an injected store) and reuses existing table/playoff logic with `cfg` where it referenced `config`.

- [ ] **Step 4: Run to verify pass** — `python3 -m pytest tests/test_standings.py -v` → PASS.

- [ ] **Step 5: Commit** — `git add engine/fetch_standings.py tests/test_standings.py && git commit -q -m "refactor: fetch_standings.build_standings(cfg) returns dict"`

---

## Task 7: Club-wide "all teams" app target in `build_apps.py`

**Files:**
- Modify: `engine/build_apps.py` (add synthetic all-ages group + accept `cfg`)
- Test: `tests/test_build_apps.py`

- [ ] **Step 1: Write failing test**

```python
def test_club_group_aggregates_all_ages():
    from engine import build_apps
    data = {"groups": {
        "u12": {"age": 12, "label": "U12", "rule": "Classic",
                "profile": {"duration_min": 11, "has_results": True, "has_tables": True, "has_playoffs": True},
                "teams": [{"id": 1, "slug": "u12-p-bla", "team_name": "Blå", "gender": "P", "color": "#1f5fbf"}],
                "matches": [{"start_ms": 1, "tid": "09:00", "bana": 1, "slug": "u12-p-bla", "gender": "P",
                             "hemma": "Blå", "borta": "X", "grupp": "A", "hb": "Hemma", "day_label": "Lör",
                             "color": "#1f5fbf", "result": None}]},
        "u14": {"age": 14, "label": "U14", "rule": "Classic",
                "profile": {"duration_min": 11, "has_results": True, "has_tables": True, "has_playoffs": True},
                "teams": [{"id": 2, "slug": "u14-f-vit", "team_name": "Vit", "gender": "F", "color": "#c9c2b4"}],
                "matches": [{"start_ms": 2, "tid": "10:00", "bana": 2, "slug": "u14-f-vit", "gender": "F",
                             "hemma": "Vit", "borta": "Y", "grupp": "B", "hb": "Hemma", "day_label": "Lör",
                             "color": "#c9c2b4", "result": None}]},
    }}
    club = build_apps.club_group(data)
    assert club["label"].lower().startswith("alla") or "klubb" in club["label"].lower()
    assert len(club["teams"]) == 2 and len(club["matches"]) == 2
    # class dimension present so the club app can filter by age/class
    classes = {f"{t['gender']}{g['age']}" for g in data["groups"].values() for t in g["teams"]}
    assert {"P12", "F14"} <= classes
```

- [ ] **Step 2: Run to verify fail** — `python3 -m pytest tests/test_build_apps.py::test_club_group_aggregates_all_ages -v` → FAIL (`club_group` missing).

- [ ] **Step 3: Implement `club_group(data)` in `engine/build_apps.py`**

```python
def club_group(data):
    """Syntetisk grupp med ALLA klubbens lag/matcher i alla åldrar → klubb-appen."""
    teams, matches = [], []
    profile = {"duration_min": 11, "has_results": True, "has_tables": False, "has_playoffs": False}
    for g in data["groups"].values():
        for t in g["teams"]:
            teams.append({**t, "age": g["age"]})          # bär åldern så klass kan visas
        for m in g["matches"]:
            matches.append({**m, "age": g["age"]})
    matches.sort(key=lambda m: m["start_ms"])
    return {"age": 0, "slug": "klubb", "label": "Alla lag",
            "rule": "Club", "profile": profile, "teams": teams, "matches": matches}
```

Note: club app has `has_tables=False` (tables are per-division, not meaningful aggregated). `_js_matches`/`_teams_js`/`_classes` already derive class as `f"{gender}{age}"`; ensure they read `age` from the team/match when present (the club group carries per-item `age`). Update `_classes(group)` to use each team's own `age` if set, else `group["age"]`.

- [ ] **Step 4: Run to verify pass** — `python3 -m pytest tests/test_build_apps.py -v` → PASS.

- [ ] **Step 5: Commit** — `git add engine/build_apps.py tests/test_build_apps.py && git commit -q -m "feat: club-wide all-teams app group (all ages, class dimension)"`

---

## Task 8: Class chip on cards/filter for multi-age apps (`template.py`)

**Files:**
- Modify: `engine/template.py` (show class label in the filter chips + on cards when a group spans multiple classes)
- Test: `tests/test_livescore.py` (template substring) + a render assertion

- [ ] **Step 1: Write failing test**

```python
def test_template_supports_class_in_filter():
    from engine import template
    t = template.TEMPLATE
    # A per-team class label is rendered in the filter chip markup.
    assert "chip-klass" in t
```

- [ ] **Step 2: Run to verify fail** — `python3 -m pytest tests/test_livescore.py::test_template_supports_class_in_filter -v` → FAIL.

- [ ] **Step 3: Implement** — in the filter-chip builder in `template.py`, when `MULTI_CLASS` (more than one distinct class among TEAMS) is true, append `<span class="chip-klass">${t.klass}</span>` to each team chip, and add `.chip-klass{font-size:.7rem;opacity:.7;margin-left:4px}` to the CSS. Set `const MULTI_CLASS = new Set(TEAMS.map(t=>t.klass)).size > 1;` near the other consts. This makes "AHK Blå" unambiguous across P/F and ages.

- [ ] **Step 4: Run to verify pass** — `python3 -m pytest tests/test_livescore.py -v` → PASS.

- [ ] **Step 5: Commit** — `git add engine/template.py tests/test_livescore.py && git commit -q -m "feat: show class chip in filter when app spans multiple classes"`

---

## Task 9: `build_cup.py` orchestrator → `dist/<slug>/`

**Files:**
- Create: `engine/build_cup.py`, `tests/test_build_cup.py`

- [ ] **Step 1: Write failing test**

```python
def test_build_cup_writes_age_apps_club_app_and_hub(tmp_path, monkeypatch):
    import json, os
    from engine.cupconfig import CupConfig
    from engine import api, build_cup
    store = json.load(open("tests/fixtures/potatis_store.json", encoding="utf-8"))
    monkeypatch.setattr(api, "fetch_store", lambda cfg: store)
    cfg = CupConfig(slug="potatiscupen", tournament_id="67026461", club_id=72525561,
                    api_host="potatiscupen.cupmanager.net", cup_name="Potatiscupen", club_name="Alingsås HK")
    out = build_cup.build_cup(cfg, dist_root=str(tmp_path))
    base = tmp_path / "potatiscupen"
    assert (base / "index.html").exists()            # per-cup hub
    assert (base / "klubb" / "index.html").exists()  # club-wide app
    assert any((base / d / "index.html").exists() for d in os.listdir(base) if d.startswith("u"))
    assert out["apps"] >= 2
```

- [ ] **Step 2: Run to verify fail** — `python3 -m pytest tests/test_build_cup.py -v` → FAIL (`build_cup` missing).

- [ ] **Step 3: Implement `engine/build_cup.py`**

```python
# engine/build_cup.py
import os
from engine import fetch_data, fetch_standings, build_apps, build_ics, build_hub

def build_cup(cfg, dist_root="dist"):
    data = fetch_data.build_cup_data(cfg)
    standings = fetch_standings.build_standings(cfg).get("by_age", {})
    out_dir = os.path.join(dist_root, cfg.slug)
    os.makedirs(out_dir, exist_ok=True)
    groups = dict(data["groups"])
    groups["klubb"] = build_apps.club_group(data)          # klubb-appen
    n = build_apps.build_all_apps(cfg, groups, standings, out_dir, data["meta"]["generated"])
    build_ics.build_all_ics(cfg, data["groups"], out_dir)
    build_hub.build_cup_hub(cfg, groups, out_dir)
    return {"slug": cfg.slug, "apps": n}
```

Add `build_all_apps(cfg, groups, standings, out_dir, updated)` to `build_apps.py` (extract the per-group loop from the old `main()`, render each to `out_dir/<age_slug>/`, using `cfg.pages_base`, writing `sched.json` per app; skip the old `config.U15_SLUG` special-case — external publish is handled later by config, not here). Add `build_all_ics(cfg, groups, out_dir)` and `build_cup_hub(cfg, groups, out_dir)` mirroring the old mains but taking `cfg`/paths as params.

- [ ] **Step 4: Run to verify pass** — `python3 -m pytest tests/test_build_cup.py -v` → PASS.

- [ ] **Step 5: Commit** — `git add engine/build_cup.py engine/build_apps.py engine/build_ics.py engine/build_hub.py tests/test_build_cup.py && git commit -q -m "feat: build_cup orchestrator → dist/<slug>/ (age apps + club app + hub)"`

---

## Task 10: `tomlwrite.py` — deterministic TOML writer

**Files:**
- Create: `engine/tomlwrite.py`, `tests/test_tomlwrite.py`

- [ ] **Step 1: Write failing test**

```python
def test_roundtrip_write_then_read(tmp_path):
    import tomllib
    from engine.tomlwrite import dump_toml
    data = {"slug": "p", "club_id": 72525561, "utc_offset": 2, "venue_mode": "halls",
            "palette": ["#1f5fbf", "#e8730c"], "external_publish": {}}
    p = tmp_path / "cup.toml"; p.write_text(dump_toml(data), encoding="utf-8")
    back = tomllib.load(open(p, "rb"))
    assert back["slug"] == "p" and back["club_id"] == 72525561
    assert back["palette"] == ["#1f5fbf", "#e8730c"]
```

- [ ] **Step 2: Run to verify fail** — `python3 -m pytest tests/test_tomlwrite.py -v` → FAIL.

- [ ] **Step 3: Implement `engine/tomlwrite.py`**

```python
# engine/tomlwrite.py — minimal deterministic TOML writer (stdlib saknar writer).
def _val(v):
    if isinstance(v, bool):   return "true" if v else "false"
    if isinstance(v, int):    return str(v)
    if isinstance(v, str):    return '"' + v.replace('\\', '\\\\').replace('"', '\\"') + '"'
    if isinstance(v, list):   return "[" + ", ".join(_val(x) for x in v) + "]"
    raise TypeError(f"otestad TOML-typ: {type(v)}")

def dump_toml(d):
    scalars = {k: v for k, v in d.items() if not isinstance(v, dict)}
    tables = {k: v for k, v in d.items() if isinstance(v, dict)}
    lines = [f"{k} = {_val(v)}" for k, v in scalars.items()]
    for name, tbl in tables.items():
        lines.append(f"\n[{name}]")
        lines += [f"{k} = {_val(v)}" for k, v in tbl.items()]
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run to verify pass** — `python3 -m pytest tests/test_tomlwrite.py -v` → PASS.

- [ ] **Step 5: Commit** — `git add engine/tomlwrite.py tests/test_tomlwrite.py && git commit -q -m "feat: deterministic TOML writer"`

---

## Task 11: `discover.py` — derive cup fields from a store

**Files:**
- Create: `engine/discover.py`, `tests/test_discover.py`

- [ ] **Step 1: Write failing test (against fixture)**

```python
def test_discover_fields_and_edge_cases(monkeypatch):
    import json
    from engine import api, discover
    store = json.load(open("tests/fixtures/potatis_store.json", encoding="utf-8"))
    monkeypatch.setattr(api, "fetch_store", lambda cfg: store)
    d = discover.discover("67026461", 72525561, "potatiscupen.cupmanager.net")
    cfg, report = d["config"], d["report"]
    assert cfg["club_name"].startswith("Alingsås")
    assert cfg["venue_mode"] == "halls"                       # named halls, not beach courts
    assert cfg["utc_offset"] in (1, 2)
    assert any("HFA" in w or "u0" in w or "ålder" in w.lower() for w in report["flags"]) or report["non_age_categories"]
```

- [ ] **Step 2: Run to verify fail** — `python3 -m pytest tests/test_discover.py -v` → FAIL.

- [ ] **Step 3: Implement `engine/discover.py`**

```python
# engine/discover.py
import re
from engine import api, derive
from engine.cupconfig import CupConfig

def _slug_from(name):
    return derive.slugify(name) if name else "cup"

def discover(tournament_id, club_id, api_host):
    probe = CupConfig(slug="probe", tournament_id=tournament_id, club_id=int(club_id), api_host=api_host)
    store = api.fetch_store(probe)
    teams = [e for e in store.values() if e.get("__typename") == "Team"]
    club_teams = [t for t in teams if api.ref_id(t.get("club")) == int(club_id)]
    if not club_teams:
        raise ValueError(f"0 lag för club_id {club_id}")
    club_name = ""
    for t in club_teams:
        nm = t.get("name") or {}
        club_name = (nm.get("clubName") or "").rsplit(" ", 1)[0] if isinstance(nm, dict) else ""
        if club_name: break
    # åldersgrupper + icke-ålders-kategorier
    ages, non_age = set(), []
    for t in club_teams:
        nm = t.get("name") or {}
        p = derive.parse_category(nm.get("categoryName", "")) if isinstance(nm, dict) else {"age": 0}
        (ages.add(p["age"]) if p["age"] else non_age.append(nm.get("categoryName", "")))
    # venues
    arenas = sorted({e.get("completeName") for e in store.values()
                     if e.get("__typename") == "Arena" and e.get("completeName")})
    venue_mode = "halls" if any(not re.fullmatch(r".*\b\d+\b.*", a) for a in arenas) or len(arenas) > 3 else "beach_court"
    # säsong → utc_offset (DST ~ apr–okt = +2)
    starts = [e["start"] for e in store.values() if e.get("__typename") == "Match" and e.get("start")]
    import datetime
    month = datetime.datetime.utcfromtimestamp(min(starts)/1000).month if starts else 7
    utc_offset = 2 if 4 <= month <= 10 else 1
    tourn = next((e for e in store.values() if e.get("__typename") == "Tournament"), {})
    cup_name = api.name_of(tourn) or f"{club_name} cup"
    slug = _slug_from(cup_name)
    config = {"slug": slug, "tournament_id": tournament_id, "club_id": int(club_id),
              "api_host": api_host, "cup_name": cup_name, "club_name": club_name,
              "utc_offset": utc_offset, "venue_mode": venue_mode}
    report = {"age_groups": sorted(a for a in ages), "venues": arenas,
              "non_age_categories": sorted(set(non_age)),
              "flags": ([f"Icke-ålders-kategorier ignoreras: {sorted(set(non_age))}"] if non_age else [])
                       + ([f"venue_mode={venue_mode}: lägg ev. venue-karta manuellt"] )}
    return {"config": config, "report": report}
```

- [ ] **Step 4: Run to verify pass** — `python3 -m pytest tests/test_discover.py -v` → PASS.

- [ ] **Step 5: Commit** — `git add engine/discover.py tests/test_discover.py && git commit -q -m "feat: discover() derives cup fields + flags non-age/venue edge cases"`

---

## Task 12: `api_host` resolution + `scaffold_cup` CLI

**Files:**
- Create: `engine/scaffold.py`, `tests/test_scaffold.py`

- [ ] **Step 1: Write failing test**

```python
def test_scaffold_writes_cup_toml(tmp_path, monkeypatch):
    import json, tomllib
    from engine import api, scaffold
    store = json.load(open("tests/fixtures/potatis_store.json", encoding="utf-8"))
    monkeypatch.setattr(api, "fetch_store", lambda cfg: store)
    path = scaffold.scaffold_cup("67026461", 72525561, api_host="potatiscupen.cupmanager.net",
                                 cups_root=str(tmp_path))
    d = tomllib.load(open(path, "rb"))
    assert d["tournament_id"] == "67026461" and d["club_id"] == 72525561
    assert path.endswith("cup.toml")
```

- [ ] **Step 2: Run to verify fail** — `python3 -m pytest tests/test_scaffold.py -v` → FAIL.

- [ ] **Step 3: Implement `engine/scaffold.py`**

```python
# engine/scaffold.py
import os, sys
from engine import discover
from engine.tomlwrite import dump_toml

def resolve_host(tournament_id, club_id, slug_hint=""):
    """Prova <hint>.cupmanager.net; verifiera via en billig call. Annars None."""
    from engine.cupconfig import CupConfig
    from engine import api
    cand = f"{slug_hint}.cupmanager.net" if slug_hint else None
    for host in filter(None, [cand]):
        try:
            api.call(CupConfig(slug="p", tournament_id=tournament_id, club_id=int(club_id), api_host=host),
                     f"Tournament({{id:{tournament_id}}})")
            return host
        except Exception:
            pass
    return None

def scaffold_cup(tournament_id, club_id, api_host=None, cups_root="cups"):
    if not api_host:
        api_host = resolve_host(tournament_id, club_id)
        if not api_host:
            raise SystemExit("api_host kunde inte härledas – ange den som 3:e argument.")
    d = discover.discover(tournament_id, club_id, api_host)
    cfg, report = d["config"], d["report"]
    out_dir = os.path.join(cups_root, cfg["slug"]); os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "cup.toml")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Auto-genererad av discover. Finish manuellt: branding, venue-karta.\n")
        f.write(dump_toml(cfg))
    with open(os.path.join(out_dir, "discover-report.txt"), "w", encoding="utf-8") as f:
        f.write("Åldersgrupper: %s\nVenues: %s\nFlaggor:\n- %s\n" % (
            report["age_groups"], report["venues"], "\n- ".join(report["flags"]) or "inga"))
    return path

if __name__ == "__main__":                      # CLI: python -m engine.scaffold <tid> <cid> [host]
    scaffold_cup(*sys.argv[1:4] if len(sys.argv) > 3 else sys.argv[1:3])
```

- [ ] **Step 4: Run to verify pass** — `python3 -m pytest tests/test_scaffold.py -v` → PASS.

- [ ] **Step 5: Commit** — `git add engine/scaffold.py tests/test_scaffold.py && git commit -q -m "feat: scaffold_cup writes cup.toml + report; api_host auto-resolve"`

---

## Task 13: Root hub (`build_hub_root.py`) listing all cups

**Files:**
- Create: `build_hub_root.py`, `tests/test_hub_root.py`

- [ ] **Step 1: Write failing test**

```python
def test_root_hub_lists_cups(tmp_path):
    import os
    from build_hub_root import build_root_hub
    os.makedirs(tmp_path / "potatiscupen"); (tmp_path / "potatiscupen" / "index.html").write_text("x")
    os.makedirs(tmp_path / "ahus-2026"); (tmp_path / "ahus-2026" / "index.html").write_text("x")
    html = build_root_hub(str(tmp_path))
    assert "potatiscupen" in html and "ahus-2026" in html
```

- [ ] **Step 2: Run to verify fail** — `python3 -m pytest tests/test_hub_root.py -v` → FAIL.

- [ ] **Step 3: Implement `build_hub_root.py`**

```python
# build_hub_root.py — topp-hubb som listar alla cups i dist/.
import os
def build_root_hub(dist_root="dist"):
    cups = sorted(d for d in os.listdir(dist_root)
                  if os.path.isdir(os.path.join(dist_root, d))
                  and os.path.exists(os.path.join(dist_root, d, "index.html")))
    items = "\n".join(f'<li><a href="{c}/">{c}</a></li>' for c in cups)
    html = f"<!doctype html><html lang=sv><meta charset=utf-8><title>Cup-appar</title><ul>{items}</ul>"
    with open(os.path.join(dist_root, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    return html
```

- [ ] **Step 4: Run to verify pass** — `python3 -m pytest tests/test_hub_root.py -v` → PASS.

- [ ] **Step 5: Commit** — `git add build_hub_root.py tests/test_hub_root.py && git commit -q -m "feat: root hub listing all cups"`

---

## Task 14: `new-cup.yml` — dispatch → discover → build → PR

**Files:**
- Create: `.github/workflows/new-cup.yml`

- [ ] **Step 1: Create the workflow**

```yaml
name: Ny cup
on:
  workflow_dispatch:
    inputs:
      tournament_id: { description: "cupmanager tournamentId", required: true }
      club_id:       { description: "cupmanager clubId", required: true }
      api_host:      { description: "(valfritt) <slug>.cupmanager.net", required: false }
permissions:
  contents: write
  pull-requests: write
jobs:
  new-cup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - name: Scaffold cup.toml (discover)
        id: scaffold
        run: |
          python -m engine.scaffold "${{ inputs.tournament_id }}" "${{ inputs.club_id }}" ${{ inputs.api_host }}
          slug=$(ls -t cups | head -1); echo "slug=$slug" >> "$GITHUB_OUTPUT"
      - name: Build cup
        run: python -c "from engine.cupconfig import load_cup; from engine.build_cup import build_cup; build_cup(load_cup('cups/${{ steps.scaffold.outputs.slug }}/cup.toml'))"
      - name: Open PR
        uses: peter-evans/create-pull-request@v6
        with:
          branch: cup/${{ steps.scaffold.outputs.slug }}
          title: "Ny cup: ${{ steps.scaffold.outputs.slug }}"
          body-path: cups/${{ steps.scaffold.outputs.slug }}/discover-report.txt
          add-paths: |
            cups/${{ steps.scaffold.outputs.slug }}/**
            dist/${{ steps.scaffold.outputs.slug }}/**
```

- [ ] **Step 2: Validate YAML locally** — `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/new-cup.yml'))"` → no error. (Install pyyaml only if needed; else skip — GitHub validates on push.)

- [ ] **Step 3: Commit** — `git add .github/workflows/new-cup.yml && git commit -q -m "ci: new-cup dispatch → discover → build → PR"`

---

## Task 15: Acceptance test — Potatiscupen end-to-end

**Files:**
- Create: `tests/test_acceptance_potatis.py`

- [ ] **Step 1: Write the acceptance test**

```python
def test_potatiscupen_build_produces_age_and_club_apps(tmp_path, monkeypatch):
    import json, os
    from engine import api, scaffold, build_cup
    from engine.cupconfig import load_cup
    store = json.load(open("tests/fixtures/potatis_store.json", encoding="utf-8"))
    monkeypatch.setattr(api, "fetch_store", lambda cfg: store)
    path = scaffold.scaffold_cup("67026461", 72525561, api_host="potatiscupen.cupmanager.net",
                                 cups_root=str(tmp_path / "cups"))
    out = build_cup.build_cup(load_cup(path), dist_root=str(tmp_path / "dist"))
    base = tmp_path / "dist" / out["slug"]
    assert (base / "klubb" / "index.html").exists()                 # club-wide app
    assert (base / "u14" / "index.html").exists()                   # an age app
    html = (base / "u14" / "index.html").read_text(encoding="utf-8")
    assert "MATCHES" in html and "Alingsås" in html
```

- [ ] **Step 2: Run — verify pass** — `python3 -m pytest tests/test_acceptance_potatis.py -v` → PASS.

- [ ] **Step 3: Run full suite** — `python3 -m pytest -q` → all green.

- [ ] **Step 4: Commit** — `git add tests/test_acceptance_potatis.py && git commit -q -m "test: Potatiscupen acceptance — age + club apps build"`

---

## Task 16: Pages deploy workflow + wire the CF Worker cron target

**Files:**
- Create: `.github/workflows/pages.yml` (build all `cups/*` → `dist/` → deploy Pages), point `ops/gh-dispatch-worker` (from ahk-beach) at this repo's refresh workflow.

- [ ] **Step 1: Create `pages.yml`** — on push to main + schedule: for each `cups/*/cup.toml`, run `build_cup`; run `build_hub_root`; upload `dist/` as the Pages artifact and deploy. (Use `actions/upload-pages-artifact` + `actions/deploy-pages`.)

- [ ] **Step 2: Commit** — `git add .github/workflows/pages.yml && git commit -q -m "ci: build all cups + deploy Pages"`

- [ ] **Step 3: Docs** — add `README` note: refresh cadence driven by the serverless CF Worker cron (`ops/gh-dispatch-worker`), `ACTIVE_FROM/UNTIL` per active cup.

---

## Self-Review

**Spec coverage:**
- Platform repo + registry → Tasks 1, 12 (cups/<slug>/cup.toml). ✓
- Engine as config-object → Tasks 2–9. ✓
- discover (2 IDs → cup.toml + report) → Tasks 11–12. ✓
- api_host resolve → Task 12. ✓
- Per-age apps + **club-wide all-teams app** + class chip → Tasks 7, 8, 9. ✓
- Two-level hub → Tasks 9 (per-cup), 13 (root). ✓
- dispatch→PR → Task 14. ✓
- Edge cases (non-age→flag, rule default, venue_mode) → Tasks 4, 5, 11. ✓
- Pages deploy + CF cron wire → Task 16. ✓
- Acceptance on Potatiscupen → Task 15. ✓
- **Gap acknowledged:** venue-map rendering for `halls` mode and branding-finish UI are Fas 5 (roadmap), not this plan — the app is runnable without them (hall names show in schedule). Consistent with spec's "auto-default + manual finish."

**Placeholder scan:** No "TBD/handle edge cases" left; each code step has real code. Task 6/16 are terse but give exact function names/signatures and mirror an earlier fully-shown task — acceptable since the pattern is concrete.

**Type consistency:** `CupConfig` fields (Task 2) are used consistently: `cfg.api_host`, `cfg.tournament_id`, `cfg.club_id`, `cfg.utc_offset`, `cfg.pages_base`, `cfg.venue_mode`, `cfg.rule_override`, `cfg.palette/color_map/club_blue`. `build_cup_data(cfg)`, `build_standings(cfg)`, `club_group(data)`, `build_all_apps(cfg, groups, standings, out_dir, updated)`, `discover(tid, cid, host)→{config,report}`, `scaffold_cup(...)→path`, `build_cup(cfg, dist_root)→{slug,apps}` — names match across tasks.

**Prerequisite for executor:** record `tests/fixtures/potatis_store.json` once (Task 5, Step 1) by dumping `api.fetch_store(CupConfig(... potatiscupen ...))` and trimming to Alingsås-touching entities; commit it so all fixture tests run offline.
