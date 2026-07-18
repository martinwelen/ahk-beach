# cup-apps MVP (Fas 1–4) Implementation Plan — v2

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **v2** incorporates an independent review (Fable) that verified the plan against the real `ahk-beach` source and the live cupmanager API. Corrections baked in: engine is not verbatim-portable (needs a cup-agnostic pass), `club_name` comes from `NameClub` (not string-chopping), `cup_name`/slug is a dispatch input (no `Tournament` name exists in the store), tz via `zoneinfo`, `dist/` stays out of git (PR ships a report + artifact; Pages builds on merge), and fixture tests monkeypatch `api.call` too.

**Goal:** A new platform repo where `workflow_dispatch(tournament_id, club_id, api_host[, cup_name])` auto-derives a cup config and builds a runnable PWA suite (one app per age group + one club-wide "all teams" app + hubs), delivered as a PR whose body has build stats + a preview-artifact link; Pages deploys on merge.

**Architecture:** A config-object-driven `engine/` (ported from `ahk-beach`, then made cup-agnostic; `config.py` globals replaced by a `CupConfig` loaded from `cups/<slug>/cup.toml`). `discover.py` turns the IDs into a `cup.toml` + report. `new-cup.yml` runs discover → build → open PR. `dist/` is generated, never committed.

**Tech Stack:** Python 3.12 (stdlib only — `tomllib` read, hand-written TOML write, `zoneinfo`), vanilla JS/CSS template, GitHub Actions, GitHub Pages.

**Verified API facts (used below):**
- `NameClub({id:<club_id>})` → entity with `name` = clean club name (e.g. `"Alingsås HK"`). Authoritative.
- The `MatchWindow` store contains **no `Tournament` entity**; `Tournament({id})` exists but exposes no name. → cup name is a dispatch input.
- `team_name` (from `nm.clubName`) is the **full team display name** (e.g. `"Alingsås HK Lag Blå"`), NOT the club name.
- Arenas are `completeName` strings; Åhus = `"Bana N"`, Potatiscupen = named halls.

**"Port" = copy that file from `~/dev/ahk-beach/` unless a change is given.** `ahk-beach` stays frozen as Åhus history.

---

## File Structure

```
engine/
  __init__.py       # makes engine a package  [NEW]
  cupconfig.py      # CupConfig + load_cup(); branding/venue/tz/rules defaults  [NEW]
  api.py            # cupmanager client — takes CupConfig  [PORT + refactor]
  derive.py         # slugify, parse_category, colors(cfg)  [PORT + refactor]
  rules.py          # rule_profile(name, cfg) — override only when unknown  [PORT + refactor]
  fetch_data.py     # build_cup_data(cfg) -> dict; tz via zoneinfo; drop non-age  [PORT + refactor]
  fetch_standings.py# build_standings(cfg) -> dict  [PORT + refactor]
  template.py       # template; Karta tab gated; branding placeholders; class filter row  [PORT + refactor]
  build_apps.py     # per-age apps + club_group() + build_all_apps(cfg,...)  [PORT + refactor]
  build_ics.py      # build_all_ics(cfg, groups, out_dir)  [PORT + refactor]
  build_hub.py      # build_cup_hub(cfg, groups, out_dir)  [PORT + refactor]
  build_cup.py      # build_cup(cfg, dist_root) orchestrator  [NEW]
  discover.py       # discover(tid, cid, host, cup_name) -> {config, report}  [NEW]
  scaffold.py       # scaffold_cup(...) writes cup.toml + report; prints slug  [NEW]
  tomlwrite.py      # deterministic TOML writer  [NEW]
  assets/           # generic default icons + logo (no Åhus map)  [NEW]
build_hub_root.py   # top-level cup-list hub  [NEW]
scripts/record_fixture.py  # dump {store, responses} fixtures  [NEW]
cups/<slug>/cup.toml   (+ optional assets/, rosters.py)
tests/  (+ tests/fixtures/{potatis,ahus}.json)
dist/<slug>/        # GENERATED, gitignored
.github/workflows/  new-cup.yml, pages.yml
pytest.ini
```

`CupConfig` (Task 3) is the interface every engine module depends on.

---

## Task 1: Scaffold repo + package skeleton

**Files:** new repo `~/dev/cup-apps/`, `.gitignore`, `.nojekyll`, `README.md`, `engine/__init__.py`, `pytest.ini`

- [ ] **Step 1: Create repo + dirs**
```bash
mkdir -p ~/dev/cup-apps/{engine/assets,cups,tests/fixtures,scripts,.github/workflows}
cd ~/dev/cup-apps && git init -q
printf 'dist/\n__pycache__/\n*.pyc\n' > .gitignore
touch .nojekyll engine/__init__.py
printf '[pytest]\ntestpaths = tests\n' > pytest.ini
printf '# cup-apps\n\nAnge tournamentId + clubId → PR med körbar app-svit. Se docs/superpowers/.\n' > README.md
```

- [ ] **Step 2: Port engine source (pre-refactor baseline)**
```bash
cp ~/dev/ahk-beach/{api,derive,rules,fetch_data,fetch_standings,template,build_apps,build_ics,build_hub}.py ~/dev/cup-apps/engine/
```
Do NOT copy `config.py`, `bana_coords.py`, or `roster_data.py` (Åhus-specific; replaced by config/optional).

- [ ] **Step 3: Commit**
```bash
cd ~/dev/cup-apps && git add -A && git commit -q -m "chore: scaffold cup-apps package + port engine source"
```

---

## Task 2: Package hygiene — imports, drop Åhus-only tests

**Files:** all `engine/*.py` (import rewrite), `tests/` (prune), `tests/conftest.py`

- [ ] **Step 1: Rewrite intra-engine imports**
In every `engine/*.py`, change flat imports to package imports: `import api` → `from engine import api`; same for `derive`, `rules`, `template`, `fetch_data`, `fetch_standings`, `build_apps`, `build_ics`, `build_hub`. Delete every `import config`, `import bana_coords`, `import roster_data` (later tasks replace their uses).

- [ ] **Step 2: Delete Åhus-specific tests**
```bash
cd ~/dev/cup-apps && git rm -q tests/test_config_u15.py tests/test_bana_coords.py tests/test_roster.py tests/test_map.py 2>/dev/null; true
```
(These reference removed modules. Roster/map functionality returns generically in Tasks 12–13 with new tests.)

- [ ] **Step 3: Add conftest so `engine` imports resolve**
```python
# tests/conftest.py
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

- [ ] **Step 4: Run collection to confirm no import errors**
Run: `cd ~/dev/cup-apps && python3 -m pytest --collect-only -q`
Expected: collects without `ModuleNotFoundError` (some tests may still fail assertions — that's fine; **collection** must be clean). Fix any remaining flat imports until collection is clean.

- [ ] **Step 5: Commit**
```bash
git add -A && git commit -q -m "chore: package imports + drop Åhus-only tests"
```

---

## Task 3: `CupConfig` + `cup.toml` loader

**Files:** Create `engine/cupconfig.py`, `tests/test_cupconfig.py`

- [ ] **Step 1: Write failing test**
```python
# tests/test_cupconfig.py
import textwrap
from engine.cupconfig import load_cup, CupConfig

def _w(tmp, body):
    p = tmp / "cup.toml"; p.write_text(textwrap.dedent(body), encoding="utf-8"); return str(p)

def test_defaults_and_required(tmp_path):
    c = load_cup(_w(tmp_path, '''
        slug = "potatiscupen"
        tournament_id = "67026461"
        club_id = 72525561
        api_host = "potatiscupen.cupmanager.net"
        cup_name = "Potatiscupen 2026"
        club_name = "Alingsås HK"
    '''))
    assert isinstance(c, CupConfig)
    assert c.tz == "Europe/Stockholm"          # default, not an int offset
    assert c.venue_map is False                 # Karta tab off by default
    assert c.rosters == {}                      # rosters optional
    assert c.venue_mode == "halls"
    assert c.pages_base.endswith("/potatiscupen")
    assert c.palette and c.color_map and c.branding["app_name"]

def test_missing_required_raises(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        load_cup(_w(tmp_path, 'slug = "x"\n'))
```

- [ ] **Step 2: Run to verify fail** — `python3 -m pytest tests/test_cupconfig.py -v` → FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement `engine/cupconfig.py`**
```python
# engine/cupconfig.py
# -*- coding: utf-8 -*-
"""CupConfig: per-cup config laddad ur cups/<slug>/cup.toml."""
import tomllib
from dataclasses import dataclass, field

DEFAULT_PALETTE = ["#1f5fbf", "#e8730c", "#2f9e44", "#d22f27", "#9c36b5", "#f2bd0c"]
DEFAULT_COLOR_MAP = {"bla": "#1f5fbf", "vit": "#c9c2b4", "svart": "#23303a", "orange": "#e8730c",
                     "gul": "#f2bd0c", "rod": "#d22f27", "gron": "#2f9e44", "rosa": "#e864a4"}
PAGES_HOST = "martinwelen.github.io"
PAGES_REPO = "cup-apps"

def _default_branding():
    return {"app_name": "Cup", "logo": "logo.svg", "theme": "#13293d", "og_title": "Cup"}

@dataclass
class CupConfig:
    slug: str
    tournament_id: str
    club_id: int
    api_host: str
    cup_name: str = ""
    club_name: str = ""
    tz: str = "Europe/Stockholm"
    venue_mode: str = "halls"                    # "halls" | "beach_court"
    venue_map: bool = False                       # True → visa Karta-flik (kräver assets + coords)
    rule_override: str = ""                       # appliceras bara när härledd regel är okänd
    rules_by_age: dict = field(default_factory=dict)   # {"u14": "Classic"}
    club_blue: str = "#1f5fbf"
    palette: list = field(default_factory=lambda: list(DEFAULT_PALETTE))
    color_map: dict = field(default_factory=lambda: dict(DEFAULT_COLOR_MAP))
    branding: dict = field(default_factory=_default_branding)
    rosters: dict = field(default_factory=dict)   # {team_slug: [players]}
    external_publish: dict = field(default_factory=dict)

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
    cfg = CupConfig(**{k: v for k, v in d.items() if k in known})
    cfg.branding = {**_default_branding(), **cfg.branding}
    return cfg
```

- [ ] **Step 4: Run to verify pass** — `python3 -m pytest tests/test_cupconfig.py -v` → PASS.

- [ ] **Step 5: Commit** — `git add engine/cupconfig.py tests/test_cupconfig.py && git commit -q -m "feat: CupConfig + loader (tz, venue_map off, optional rosters)"`

---

## Task 4: Fixture recorder + record Potatiscupen & Åhus fixtures

**Files:** Create `scripts/record_fixture.py`, `tests/fixtures/potatis.json`, `tests/fixtures/ahus.json`

- [ ] **Step 1: Implement the recorder**
```python
# scripts/record_fixture.py
# Usage: python3 scripts/record_fixture.py <tid> <cid> <api_host> <out.json>
import json, sys, urllib.parse, urllib.request
def call(host, tid, q):
    u = f"https://{host}/rest/results_api/call?call={urllib.parse.quote(q)}&lang=sv&tournamentId={tid}"
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"user-agent": "rec/1.0"}), timeout=60).read())
def mq(tid, l, o):
    return ("MatchWindow({{limit:{l},offset:{o},tournamentId:{t}}})"
            "{{matches:[{{... on Match:{{start:{{}},arena:{{}},away:{{team:{{}}}},"
            "division:{{category:{{}},name:{{}}}},home:{{team:{{}}}},result:{{}}}}}}]}}").format(l=l, o=o, t=tid)
def main(tid, cid, host, out):
    store, off = {}, 0
    for _ in range(100):
        resp = call(host, tid, mq(tid, 300, off)).get("responses", {}); pg = 0
        for k, v in resp.items():
            if isinstance(v, dict) and isinstance(v.get("entity"), dict):
                store[k] = v["entity"]
                if v["entity"].get("__typename") == "Match": pg += 1
        if pg < 300: break
        off += 300
    cid = int(cid)
    keep_clubs = {api_ref(t.get("club")) for t in store.values() if t.get("__typename") == "Team"}
    # Behåll allt (matcher små), men spela även in extra-anrop pipelinen gör:
    responses = {}
    responses[f"NameClub({{id:{cid}}})"] = call(host, tid, f"NameClub({{id:{cid}}})")
    # division-tabeller + rundnamn + video som fetch_standings/_round_name/_video_url gör:
    divs = {ref_id(m.get("division")) for m in store.values() if m.get("__typename") == "Match"}
    for d in filter(None, divs):
        responses[f"Division({{id:{d}}})$table"] = call(host, tid, f"Division({{id:{d}}})$table")
    json.dump({"store": store, "responses": responses}, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    print("skrev", out, "| store", len(store), "| responses", len(responses))
def ref_id(node):
    import re
    if isinstance(node, dict):
        m = re.search(r"id:(\d+)", node.get("href", "")); return int(m.group(1)) if m else None
    return None
api_ref = ref_id
if __name__ == "__main__":
    main(*sys.argv[1:5])
```

- [ ] **Step 2: Record both fixtures**
```bash
cd ~/dev/cup-apps
python3 scripts/record_fixture.py 67026461 72525561 potatiscupen.cupmanager.net tests/fixtures/potatis.json
python3 scripts/record_fixture.py 70944382 73383031 ahusbeachhandboll.cupmanager.net tests/fixtures/ahus.json
```
Expected: both print `skrev … | store N | responses M`. (Åhus is the beach-court ground-truth fixture.)

- [ ] **Step 3: Commit**
```bash
git add scripts/record_fixture.py tests/fixtures/potatis.json tests/fixtures/ahus.json
git commit -q -m "test: fixture recorder + Potatiscupen & Åhus fixtures (store + responses)"
```

**Note for all later fixture tests:** load `f = json.load(open("tests/fixtures/potatis.json"))`; `monkeypatch.setattr("engine.api.fetch_store", lambda cfg: f["store"])` **and** `monkeypatch.setattr("engine.api.call", lambda cfg, q, **k: f["responses"].get(q, {"responses": {}}))`.

---

## Task 5: Refactor `api.py` to take `CupConfig`

**Files:** Modify `engine/api.py`, `tests/test_api.py`

- [ ] **Step 1: Update test**
```python
from engine.cupconfig import CupConfig
from engine import api
CFG = CupConfig(slug="t", tournament_id="70944382", club_id=73383031, api_host="ahusbeachhandboll.cupmanager.net")
def test_match_query_has_tid():
    assert "tournamentId:70944382" in api.match_query(CFG, 300, 0)
```

- [ ] **Step 2: Run to verify fail** — `python3 -m pytest tests/test_api.py -v` → FAIL.

- [ ] **Step 3: Refactor** — remove `import config` and `_API`. New signatures: `match_query(cfg, limit, offset)` (uses `cfg.tournament_id`), `call(cfg, query, retries=4)` (builds url from `cfg.api_host`/`cfg.tournament_id`), `fetch_store(cfg)` (pages via `call(cfg, match_query(cfg, ...))`). Keep `ref_id`, `name_of`, `store_get` as-is. (Full bodies are the same as `ahk-beach` `api.py` with `config.X` replaced by `cfg.X` and `cfg` added as first param.)

- [ ] **Step 4: Run to verify pass** — `python3 -m pytest tests/test_api.py -v` → PASS.

- [ ] **Step 5: Commit** — `git add engine/api.py tests/test_api.py && git commit -q -m "refactor: api.py takes CupConfig"`

---

## Task 6: `rules.py` + `derive.py` colors take `CupConfig`

**Files:** Modify `engine/rules.py`, `engine/derive.py`, `tests/test_rules.py`, `tests/test_derive.py`

- [ ] **Step 1: Write failing tests**
```python
# tests/test_rules.py (add)
from engine.cupconfig import CupConfig
from engine import rules
def test_override_only_when_unknown():
    cfg = CupConfig(slug="t", tournament_id="1", club_id=1, api_host="h", rule_override="Mini")
    assert rules.rule_profile("Classic", cfg)["has_tables"] is True   # known rule NOT clobbered
    assert rules.rule_profile("?", cfg)["has_tables"] is False        # unknown → override applies
def test_per_age_rule():
    cfg = CupConfig(slug="t", tournament_id="1", club_id=1, api_host="h", rules_by_age={"u8": "Mini"})
    assert rules.rule_profile("?", cfg, age_slug="u8")["has_tables"] is False
```

- [ ] **Step 2: Run to verify fail** — `python3 -m pytest tests/test_rules.py -v` → FAIL.

- [ ] **Step 3: Implement** — `rule_profile(name, cfg, age_slug=None)`. Resolution order: if `age_slug in cfg.rules_by_age` → that; elif `name` unknown (`"?"`/not in table) and `cfg.rule_override` → override; else `name`. Then existing profile table (unknown → `_DEFAULT`). In `derive.py`, `derive_group_colors(group, cfg)` using `cfg.club_blue/color_map/palette`; remove `import config`.

- [ ] **Step 4: Run to verify pass** — `python3 -m pytest tests/test_rules.py tests/test_derive.py -v` → PASS.

- [ ] **Step 5: Commit** — `git add engine/rules.py engine/derive.py tests/test_rules.py tests/test_derive.py && git commit -q -m "refactor: rules override-only-when-unknown + per-age; colors via cfg"`

---

## Task 7: `fetch_data.build_cup_data(cfg)` (tz via zoneinfo, drop non-age)

**Files:** Modify `engine/fetch_data.py`, `tests/test_fetch_data.py`

- [ ] **Step 1: Write failing test**
```python
import json
from engine.cupconfig import CupConfig
from engine import fetch_data
CFG = CupConfig(slug="potatiscupen", tournament_id="67026461", club_id=72525561, api_host="h")
def test_build_cup_data(monkeypatch):
    f = json.load(open("tests/fixtures/potatis.json", encoding="utf-8"))
    monkeypatch.setattr("engine.api.fetch_store", lambda cfg: f["store"])
    monkeypatch.setattr("engine.api.call", lambda cfg, q, **k: f["responses"].get(q, {"responses": {}}))
    data = fetch_data.build_cup_data(CFG)
    assert data["groups"] and all(g["teams"] for g in data["groups"].values())
    assert "u0" not in data["groups"]                        # non-age (HFA) dropped
    m = next(iter(data["groups"].values()))["matches"][0]
    assert ":" in m["tid"]                                    # tz formatting worked
```

- [ ] **Step 2: Run to verify fail** — `python3 -m pytest tests/test_fetch_data.py -v` → FAIL.

- [ ] **Step 3: Refactor** — remove `import config`, `DATA_JSON`, `write_if_changed`, `main`, file I/O. Changes:
  - tz: `from zoneinfo import ZoneInfo`; `TZ = ZoneInfo(cfg.tz)`; `datetime.fromtimestamp(start_ms/1000, TZ)`. Delete `_CEST`/`UTC_OFFSET_HOURS`.
  - Thread `cfg` into `normalize_match(e, store, reg_by_id, cfg)`, `bucket_by_age_group(registry, match_entities, store, cfg)`, `build_team_registry(store, cfg)`, `_round_name(mid, cfg)`, `_video_url(mid, cfg)` (they call `api.call(cfg, ...)`).
  - Video probe only when `cfg.venue_mode == "beach_court"` (guards indoor halls whose name has a digit).
  - Add `build_cup_data(cfg)`:
```python
def build_cup_data(cfg):
    store = api.fetch_store(cfg)
    registry = build_team_registry(store, cfg)
    if not registry:
        raise ValueError(f"0 lag för club_id {cfg.club_id}")
    matches = [e for e in store.values() if e.get("__typename") == "Match"]
    groups = bucket_by_age_group(registry, matches, store, cfg)
    groups = {a: g for a, g in groups.items() if a != "u0"}     # icke-ålders → bort
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    return {"groups": groups, "meta": {"cup": cfg.cup_name, "club_id": cfg.club_id,
            "generated": now.isoformat(timespec="seconds"), "data_hash": _hash_groups(groups)}}
```
  Keep `_hash_groups` unchanged.

- [ ] **Step 4: Run to verify pass** — `python3 -m pytest tests/test_fetch_data.py -v` → PASS.

- [ ] **Step 5: Commit** — `git add engine/fetch_data.py tests/test_fetch_data.py && git commit -q -m "refactor: fetch_data.build_cup_data(cfg) — zoneinfo tz, drop non-age, cfg-threaded helpers"`

---

## Task 8: `fetch_standings.build_standings(cfg)`

**Files:** Modify `engine/fetch_standings.py`, `tests/test_standings.py`

- [ ] **Step 1: Write failing test**
```python
import json
from engine.cupconfig import CupConfig
from engine import fetch_standings
def test_build_standings(monkeypatch):
    f = json.load(open("tests/fixtures/potatis.json", encoding="utf-8"))
    monkeypatch.setattr("engine.api.fetch_store", lambda cfg: f["store"])
    monkeypatch.setattr("engine.api.call", lambda cfg, q, **k: f["responses"].get(q, {"responses": {}}))
    st = fetch_standings.build_standings(CupConfig(slug="p", tournament_id="67026461", club_id=72525561, api_host="h"))
    assert "by_age" in st
```

- [ ] **Step 2: Run to verify fail** — → FAIL.

- [ ] **Step 3: Refactor** — remove globals/file I/O; `build_standings(cfg) -> {"by_age": {...}}`; every `api.call(q)` → `api.call(cfg, q)`; every `config.X` → `cfg.X`.

- [ ] **Step 4: Run to verify pass** — → PASS.

- [ ] **Step 5: Commit** — `git add engine/fetch_standings.py tests/test_standings.py && git commit -q -m "refactor: fetch_standings.build_standings(cfg)"`

---

## Task 9: Make `template.py` + `build_apps.py` cup-agnostic (rosters/map/branding)

**Files:** Modify `engine/template.py`, `engine/build_apps.py`, `engine/assets/`, `tests/test_template_agnostic.py`

- [ ] **Step 1: Write failing test**
```python
# tests/test_template_agnostic.py
from engine import build_apps
from engine.cupconfig import CupConfig
def _grp():
    return {"age": 12, "label": "U12", "rule": "Classic",
            "profile": {"duration_min": 11, "has_results": True, "has_tables": True, "has_playoffs": True},
            "teams": [{"id": 1, "slug": "u12-p-bla", "team_name": "Blå", "gender": "P", "color": "#1f5fbf"}],
            "matches": []}
def test_no_map_tab_when_venue_map_off():
    cfg = CupConfig(slug="p", tournament_id="1", club_id=1, api_host="h", venue_map=False,
                    branding={"app_name": "Potatiscupen", "logo": "logo.svg", "theme": "#13293d", "og_title": "Potatiscupen"})
    html = build_apps.render_app(cfg, _grp(), None, "u")
    assert 'data-view="karta"' not in html          # Karta-fliken renderas inte
    assert "karta.png" not in html
    assert "Potatiscupen" in html                     # branding app-namn används
```

- [ ] **Step 2: Run to verify fail** — `python3 -m pytest tests/test_template_agnostic.py -v` → FAIL.

- [ ] **Step 3: Implement**
  - `template.py`: wrap the Karta tab button, the `#map`/`#mapzoom` markup, and the map JS in `__MAP_BLOCK__` placeholders so they are emitted only when the map is on. Replace hardcoded `Alingsas_HK_logo.svg`→`__LOGO__`, `karta.png`→`__MAP_IMG__`, `AHK __APPLABEL__` / "Åhus Beach Handboll" alt/OG → `__APP_NAME__`/`__OG_TITLE__`, theme color → `__THEME__`. Replace `__ROSTERS__` default handling so an empty dict hides the Trupp tab (already the case).
  - `build_apps.py`: `render_app(cfg, group, standings, updated)`:
    - `__ROSTERS__` = `json.dumps(cfg.rosters filtered to group teams)`.
    - Map: if `cfg.venue_map` → inject the map block + `__BANA_XY__`/`__KLUBBTALT__` from a cup-provided `cups/<slug>/coords.json` (loaded by caller); else replace the map placeholders with empty string and omit `BANA_XY`.
    - `__LOGO__`=`cfg.branding["logo"]`, `__APP_NAME__`=`cfg.branding["app_name"]`, `__THEME__`=`cfg.branding["theme"]`, `__OG_TITLE__`=`cfg.branding["og_title"]`, `__BASE__`=`cfg.pages_base`.
    - `_ASSETS` = generic `_ICONS` + `(cfg.branding["logo"],)` (+ map image only when `venue_map`), copied from `engine/assets/` or `cups/<slug>/assets/`.
  - Add default files under `engine/assets/`: `icon-192.png`, `icon-512.png`, `icon-512-maskable.png`, `icon-180.png`, `favicon-32.png`, `logo.svg` (neutral placeholder marks — a cup overrides via `cups/<slug>/assets/`).

- [ ] **Step 4: Run to verify pass** — `python3 -m pytest tests/test_template_agnostic.py tests/test_livescore.py -v` → PASS. (Update any `test_livescore.py`/`test_map.py`-derived substring tests that assumed an always-on map; keep the livescore/TDZ regression tests.)

- [ ] **Step 5: Commit** — `git add engine/template.py engine/build_apps.py engine/assets tests/test_template_agnostic.py tests/test_livescore.py && git commit -q -m "feat: cup-agnostic template — gated map tab, optional rosters, branding placeholders"`

---

## Task 10: Club-wide "all teams" app + class filter row

**Files:** Modify `engine/build_apps.py`, `engine/template.py`, `tests/test_club_app.py`

- [ ] **Step 1: Write failing test (assert on `_teams_js` output, not the input)**
```python
# tests/test_club_app.py
from engine import build_apps
def _data():
    def g(age, gender, slug):
        return {"age": age, "label": f"U{age}", "rule": "Classic",
                "profile": {"duration_min": 11, "has_results": True, "has_tables": True, "has_playoffs": True},
                "teams": [{"id": age, "slug": slug, "team_name": "Blå", "gender": gender, "color": "#1f5fbf"}],
                "matches": [{"start_ms": age, "tid": "09:00", "bana": 1, "slug": slug, "gender": gender,
                             "hemma": "Blå", "borta": "X", "grupp": "A", "hb": "Hemma", "day_label": "Lör",
                             "color": "#1f5fbf", "result": None}]}
    return {"groups": {"u12": g(12, "P", "u12-p-bla"), "u14": g(14, "F", "u14-f-bla")}}
def test_club_group_and_classes():
    club = build_apps.club_group(_data())
    assert len(club["teams"]) == 2 and len(club["matches"]) == 2
    teams_js = build_apps._teams_js(club)                       # the real embed
    assert {t["klass"] for t in teams_js} == {"P12", "F14"}     # per-item age → correct class
```

- [ ] **Step 2: Run to verify fail** — `python3 -m pytest tests/test_club_app.py -v` → FAIL.

- [ ] **Step 3: Implement**
```python
# engine/build_apps.py
def club_group(data):
    teams, matches = [], []
    for g in data["groups"].values():
        for t in g["teams"]:  teams.append({**t, "age": g["age"]})
        for m in g["matches"]: matches.append({**m, "age": g["age"]})
    matches.sort(key=lambda m: m["start_ms"])
    return {"age": 0, "slug": "klubb", "label": "Alla lag", "rule": "Club",
            "profile": {"duration_min": 11, "has_results": True, "has_tables": False, "has_playoffs": False},
            "teams": teams, "matches": matches}
```
Update `_classes(group)`, `_teams_js(group)`, `_js_matches(group)` to read each item's own `age` when present (`t.get("age", group["age"])`), so class = `f"{gender}{age}"` is correct in the club app. In `template.py`, when `MULTI_CLASS` (`new Set(TEAMS.map(t=>t.klass)).size > 1`) add a **class filter row** (P12/F14 chips) above the team chips that filters teams by class; each team chip also shows `<span class="chip-klass">${t.klass}</span>`.

- [ ] **Step 4: Run to verify pass** — `python3 -m pytest tests/test_club_app.py -v` → PASS.

- [ ] **Step 5: Commit** — `git add engine/build_apps.py engine/template.py tests/test_club_app.py && git commit -q -m "feat: club-wide app (per-item age → class) + class filter row"`

---

## Task 11: `tomlwrite.py`

**Files:** Create `engine/tomlwrite.py`, `tests/test_tomlwrite.py`

- [ ] **Step 1: Write failing test**
```python
def test_roundtrip(tmp_path):
    import tomllib
    from engine.tomlwrite import dump_toml
    d = {"slug": "p", "club_id": 72525561, "venue_mode": "halls", "venue_map": False,
         "palette": ["#1f5fbf", "#e8730c"], "branding": {"app_name": "Potatiscupen"}}
    p = tmp_path / "c.toml"; p.write_text(dump_toml(d), encoding="utf-8")
    back = tomllib.load(open(p, "rb"))
    assert back["club_id"] == 72525561 and back["palette"][0] == "#1f5fbf"
    assert back["venue_map"] is False and back["branding"]["app_name"] == "Potatiscupen"
```

- [ ] **Step 2: Run to verify fail** — → FAIL.

- [ ] **Step 3: Implement**
```python
# engine/tomlwrite.py — minimal deterministic TOML writer.
def _v(x):
    if isinstance(x, bool): return "true" if x else "false"
    if isinstance(x, int):  return str(x)
    if isinstance(x, str):  return '"' + x.replace('\\', '\\\\').replace('"', '\\"') + '"'
    if isinstance(x, list): return "[" + ", ".join(_v(i) for i in x) + "]"
    raise TypeError(type(x))
def dump_toml(d):
    scal = {k: v for k, v in d.items() if not isinstance(v, dict)}
    tbls = {k: v for k, v in d.items() if isinstance(v, dict)}
    lines = [f"{k} = {_v(v)}" for k, v in scal.items()]
    for name, t in tbls.items():
        lines.append(f"\n[{name}]"); lines += [f"{k} = {_v(v)}" for k, v in t.items()]
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run to verify pass** — → PASS.

- [ ] **Step 5: Commit** — `git add engine/tomlwrite.py tests/test_tomlwrite.py && git commit -q -m "feat: deterministic TOML writer"`

---

## Task 12: `discover.py` — derive config from IDs (corrected)

**Files:** Create `engine/discover.py`, `tests/test_discover.py`

- [ ] **Step 1: Write failing tests (both fixtures)**
```python
import json
from engine import api, discover
def _patch(mp, path):
    f = json.load(open(path, encoding="utf-8"))
    mp.setattr(api, "fetch_store", lambda cfg: f["store"])
    mp.setattr(api, "call", lambda cfg, q, **k: f["responses"].get(q, {"responses": {}}))
def test_discover_potatis(monkeypatch):
    _patch(monkeypatch, "tests/fixtures/potatis.json")
    d = discover.discover("67026461", 72525561, "potatiscupen.cupmanager.net", cup_name="Potatiscupen 2026")
    assert d["config"]["club_name"] == "Alingsås HK"        # from NameClub, exact
    assert d["config"]["slug"] == "potatiscupen-2026"
    assert d["config"]["venue_mode"] == "halls"
    assert d["report"]["non_age_categories"]                 # HFA flagged, not silently dropped
def test_discover_ahus_is_beach(monkeypatch):
    _patch(monkeypatch, "tests/fixtures/ahus.json")
    d = discover.discover("70944382", 73383031, "ahusbeachhandboll.cupmanager.net", cup_name="Åhus 2026")
    assert d["config"]["venue_mode"] == "beach_court"        # ground truth
```

- [ ] **Step 2: Run to verify fail** — → FAIL.

- [ ] **Step 3: Implement**
```python
# engine/discover.py
import re
from engine import api, derive
from engine.cupconfig import CupConfig

def _club_name(store, club_id, host, tid):
    r = api.call(CupConfig(slug="p", tournament_id=tid, club_id=club_id, api_host=host),
                 f"NameClub({{id:{club_id}}})")
    for v in (r.get("responses") or {}).values():
        e = (v or {}).get("entity") or {}
        if e.get("__typename") == "NameClub":
            return e.get("name") or ""
    return ""

def discover(tournament_id, club_id, api_host, cup_name=""):
    club_id = int(club_id)
    probe = CupConfig(slug="probe", tournament_id=tournament_id, club_id=club_id, api_host=api_host)
    store = api.fetch_store(probe)
    club_teams = [t for t in store.values()
                  if t.get("__typename") == "Team" and api.ref_id(t.get("club")) == club_id]
    if not club_teams:
        raise ValueError(f"0 lag för club_id {club_id}")
    club_name = _club_name(store, club_id, api_host, tournament_id) or "Klubb"
    ages, non_age = set(), []
    for t in club_teams:
        nm = t.get("name") or {}
        p = derive.parse_category(nm.get("categoryName", "")) if isinstance(nm, dict) else {"age": 0}
        ages.add(p["age"]) if p["age"] else non_age.append(nm.get("categoryName", ""))
    arenas = sorted({e.get("completeName") for e in store.values()
                     if e.get("__typename") == "Arena" and e.get("completeName")})
    beach = bool(arenas) and all(re.fullmatch(r"(bana|court)\s*\d+", a.strip(), re.I) for a in arenas)
    venue_mode = "beach_court" if beach else "halls"
    if not cup_name:
        cup_name = f"{club_name} {tournament_id}"
    slug = derive.slugify(cup_name)
    config = {"slug": slug, "tournament_id": tournament_id, "club_id": club_id, "api_host": api_host,
              "cup_name": cup_name, "club_name": club_name, "venue_mode": venue_mode}
    flags = []
    if non_age:
        flags.append(f"Icke-ålders-kategorier ignoreras (ingen app byggs): {sorted(set(non_age))}")
    if venue_mode == "halls":
        flags.append("venue_mode=halls: ingen Karta-flik. Sätt venue_map=true + coords.json för karta.")
    if not cup_name.strip() or cup_name.endswith(tournament_id):
        flags.append("cup_name auto-provisoriskt → sätt ett snyggt namn/slug INNAN merge (permanent URL).")
    report = {"age_groups": sorted(a for a in ages), "venues": arenas,
              "non_age_categories": sorted(set(non_age)), "flags": flags}
    return {"config": config, "report": report}
```

- [ ] **Step 4: Run to verify pass** — `python3 -m pytest tests/test_discover.py -v` → PASS.

- [ ] **Step 5: Commit** — `git add engine/discover.py tests/test_discover.py && git commit -q -m "feat: discover — NameClub club name, beach-iff-all-BanaN, cup_name input, edge flags"`

---

## Task 13: `scaffold.py` — write cup.toml + report, print slug

**Files:** Create `engine/scaffold.py`, `tests/test_scaffold.py`

- [ ] **Step 1: Write failing test**
```python
import json, tomllib
from engine import api, scaffold
def test_scaffold(tmp_path, monkeypatch):
    f = json.load(open("tests/fixtures/potatis.json", encoding="utf-8"))
    monkeypatch.setattr(api, "fetch_store", lambda cfg: f["store"])
    monkeypatch.setattr(api, "call", lambda cfg, q, **k: f["responses"].get(q, {"responses": {}}))
    path, slug = scaffold.scaffold_cup("67026461", 72525561, "potatiscupen.cupmanager.net",
                                       cup_name="Potatiscupen 2026", cups_root=str(tmp_path))
    d = tomllib.load(open(path, "rb"))
    assert d["club_name"] == "Alingsås HK" and slug == "potatiscupen-2026"
    assert path.endswith("cup.toml")
```

- [ ] **Step 2: Run to verify fail** — → FAIL.

- [ ] **Step 3: Implement**
```python
# engine/scaffold.py
import os, sys
from engine import discover
from engine.tomlwrite import dump_toml

def scaffold_cup(tournament_id, club_id, api_host, cup_name="", cups_root="cups"):
    d = discover.discover(tournament_id, club_id, api_host, cup_name=cup_name)
    cfg, report = d["config"], d["report"]
    out = os.path.join(cups_root, cfg["slug"]); os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "cup.toml")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Auto-genererad. Finish manuellt före merge: branding, ev. venue_map + coords.\n")
        f.write(dump_toml(cfg))
    with open(os.path.join(out, "discover-report.md"), "w", encoding="utf-8") as f:
        f.write(f"## Ny cup: {cfg['cup_name']} ({cfg['slug']})\n\n"
                f"- Klubb: {cfg['club_name']}\n- Åldersgrupper: {report['age_groups']}\n"
                f"- Venues ({cfg['venue_mode']}): {report['venues']}\n\n### Att finisha\n"
                + ("\n".join(f"- {x}" for x in report["flags"]) or "- inget") + "\n")
    return path, cfg["slug"]

if __name__ == "__main__":                       # CLI: <tid> <cid> <host> [cup_name]
    _, slug = scaffold_cup(*sys.argv[1:5]) if len(sys.argv) > 4 else scaffold_cup(*sys.argv[1:4])
    print(slug)                                   # workflow läser stdout för slug
```

- [ ] **Step 4: Run to verify pass** — → PASS.

- [ ] **Step 5: Commit** — `git add engine/scaffold.py tests/test_scaffold.py && git commit -q -m "feat: scaffold_cup writes cup.toml + report, returns/prints slug"`

---

## Task 14: `build_cup.py` orchestrator → `dist/<slug>/`

**Files:** Create `engine/build_cup.py`; extend `build_apps`/`build_ics`/`build_hub` with `cfg`-taking entry points; `tests/test_build_cup.py`

- [ ] **Step 1: Write failing test**
```python
import json, os
from engine.cupconfig import CupConfig
from engine import api, build_cup
def test_build_cup(tmp_path, monkeypatch):
    f = json.load(open("tests/fixtures/potatis.json", encoding="utf-8"))
    monkeypatch.setattr(api, "fetch_store", lambda cfg: f["store"])
    monkeypatch.setattr(api, "call", lambda cfg, q, **k: f["responses"].get(q, {"responses": {}}))
    cfg = CupConfig(slug="potatiscupen-2026", tournament_id="67026461", club_id=72525561,
                    api_host="h", cup_name="Potatiscupen 2026", club_name="Alingsås HK",
                    branding={"app_name": "Potatiscupen", "logo": "logo.svg", "theme": "#13293d", "og_title": "Potatiscupen"})
    out = build_cup.build_cup(cfg, dist_root=str(tmp_path))
    base = tmp_path / "potatiscupen-2026"
    assert (base / "index.html").exists() and (base / "klubb" / "index.html").exists()
    assert any((base / d / "index.html").exists() for d in os.listdir(base) if d.startswith("u"))
    assert out["apps"] >= 2 and out["teams"] > 0 and out["matches"] > 0
```

- [ ] **Step 2: Run to verify fail** — → FAIL.

- [ ] **Step 3: Implement**
```python
# engine/build_cup.py
import os
from engine import fetch_data, fetch_standings, build_apps, build_ics, build_hub

def build_cup(cfg, dist_root="dist"):
    data = fetch_data.build_cup_data(cfg)
    standings = fetch_standings.build_standings(cfg).get("by_age", {})
    out = os.path.join(dist_root, cfg.slug); os.makedirs(out, exist_ok=True)
    groups = dict(data["groups"]); groups["klubb"] = build_apps.club_group(data)
    n = build_apps.build_all_apps(cfg, groups, standings, out, data["meta"]["generated"])
    build_ics.build_all_ics(cfg, data["groups"], out)
    build_hub.build_cup_hub(cfg, groups, out)
    return {"slug": cfg.slug, "apps": n,
            "teams": sum(len(g["teams"]) for g in data["groups"].values()),
            "matches": sum(len(g["matches"]) for g in data["groups"].values())}
```
Add `build_all_apps(cfg, groups, standings, out_dir, updated)` (loop from old `main()`, render each group via `render_app(cfg, ...)` to `out_dir/<slug>/`, write `sched.json`, copy assets; no `U15_SLUG` special-case). Add `build_all_ics(cfg, groups, out_dir)` and `build_cup_hub(cfg, groups, out_dir)` (old mains parameterized by `cfg`/paths; hub links every age app + the `klubb` app).

- [ ] **Step 4: Run to verify pass** — → PASS.

- [ ] **Step 5: Commit** — `git add engine/build_cup.py engine/build_apps.py engine/build_ics.py engine/build_hub.py tests/test_build_cup.py && git commit -q -m "feat: build_cup orchestrator → dist/<slug>/ (age + club apps + hub + stats)"`

---

## Task 15: Root hub (`build_hub_root.py`)

**Files:** Create `build_hub_root.py`, `tests/test_hub_root.py`

- [ ] **Step 1: Write failing test**
```python
def test_root_hub(tmp_path):
    import os
    from build_hub_root import build_root_hub
    for c in ("potatiscupen-2026", "ahus-2026"):
        os.makedirs(tmp_path / c); (tmp_path / c / "index.html").write_text("x")
    html = build_root_hub(str(tmp_path))
    assert "potatiscupen-2026" in html and "ahus-2026" in html
```

- [ ] **Step 2: Run to verify fail** — → FAIL.

- [ ] **Step 3: Implement**
```python
# build_hub_root.py
import os
def build_root_hub(dist_root="dist"):
    cups = sorted(d for d in os.listdir(dist_root)
                  if os.path.isdir(os.path.join(dist_root, d))
                  and os.path.exists(os.path.join(dist_root, d, "index.html")))
    items = "\n".join(f'<li><a href="{c}/">{c}</a></li>' for c in cups)
    html = f"<!doctype html><html lang=sv><meta charset=utf-8><title>Cup-appar</title><ul>{items}</ul>"
    with open(os.path.join(dist_root, "index.html"), "w", encoding="utf-8") as f: f.write(html)
    return html
```

- [ ] **Step 4: Run to verify pass** — → PASS.

- [ ] **Step 5: Commit** — `git add build_hub_root.py tests/test_hub_root.py && git commit -q -m "feat: root hub listing all cups"`

---

## Task 16: `new-cup.yml` — dispatch → discover → build → PR (dist as artifact)

**Files:** Create `.github/workflows/new-cup.yml`

- [ ] **Step 1: Create the workflow**
```yaml
name: Ny cup
on:
  workflow_dispatch:
    inputs:
      tournament_id: { description: "cupmanager tournamentId", required: true }
      club_id:       { description: "cupmanager clubId", required: true }
      api_host:      { description: "<slug>.cupmanager.net", required: true }
      cup_name:      { description: "(valfritt) cup-namn → slug/URL", required: false }
permissions: { contents: write, pull-requests: write }
jobs:
  new-cup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - name: Scaffold cup.toml (discover)
        id: sc
        run: |
          slug=$(python -m engine.scaffold "${{ inputs.tournament_id }}" "${{ inputs.club_id }}" "${{ inputs.api_host }}" "${{ inputs.cup_name }}")
          echo "slug=$slug" >> "$GITHUB_OUTPUT"
      - name: Build cup (dist/ – ej committad)
        run: |
          python -c "from engine.cupconfig import load_cup; from engine.build_cup import build_cup; import json; print(json.dumps(build_cup(load_cup('cups/${{ steps.sc.outputs.slug }}/cup.toml'))))" | tee build.json
      - name: Upload preview artifact
        uses: actions/upload-artifact@v4
        with: { name: "preview-${{ steps.sc.outputs.slug }}", path: "dist/${{ steps.sc.outputs.slug }}" }
      - name: Open PR (bara cup-config + rapport)
        uses: peter-evans/create-pull-request@v6
        with:
          branch: cup/${{ steps.sc.outputs.slug }}
          title: "Ny cup: ${{ steps.sc.outputs.slug }}"
          body-path: cups/${{ steps.sc.outputs.slug }}/discover-report.md
          add-paths: cups/${{ steps.sc.outputs.slug }}/**
```
Notes baked in: `dist/` is gitignored so the PR carries only `cups/<slug>/**` + the report; the built app is downloadable as the **preview artifact**; Pages builds on merge (Task 17). Build stats (`build.json`) can be appended to the PR body in a follow-up step. **Caveat:** PRs opened with the default `GITHUB_TOKEN` do not trigger other workflows — fine for MVP (Pages deploy runs on the merge push, not the PR).

- [ ] **Step 2: Validate YAML** — `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/new-cup.yml'))"` (skip if pyyaml absent; GitHub validates on push).

- [ ] **Step 3: Commit** — `git add .github/workflows/new-cup.yml && git commit -q -m "ci: new-cup dispatch → discover → build → PR (dist as artifact, Pages on merge)"`

---

## Task 17: `pages.yml` — build all cups + deploy, hash-gated

**Files:** Create `.github/workflows/pages.yml`

- [ ] **Step 1: Create the workflow** — on push to `main` (+ optional schedule): for each `cups/*/cup.toml`, run `build_cup(load_cup(...))` into `dist/`; run `build_root_hub("dist")`; upload `dist/` via `actions/upload-pages-artifact`; deploy via `actions/deploy-pages`. To avoid needless redeploys on scheduled runs, first fetch each cup's data and compare `_hash_groups` to a committed `cups/<slug>/.last_hash`; skip build for unchanged cups and skip deploy if nothing changed (reuse the `_hash_groups` machinery; the data-refresh cadence is driven by the serverless CF Worker cron `ops/gh-dispatch-worker`, `ACTIVE_FROM/UNTIL` per active cup).

- [ ] **Step 2: Commit** — `git add .github/workflows/pages.yml && git commit -q -m "ci: build all cups + deploy Pages (hash-gated)"`

---

## Task 18: Acceptance — Potatiscupen + Åhus end-to-end

**Files:** Create `tests/test_acceptance.py`

- [ ] **Step 1: Write the acceptance test**
```python
import json, os
from engine import api, scaffold, build_cup
from engine.cupconfig import load_cup
def _run(tmp_path, monkeypatch, fixture, tid, cid, host, name):
    f = json.load(open(fixture, encoding="utf-8"))
    monkeypatch.setattr(api, "fetch_store", lambda cfg: f["store"])
    monkeypatch.setattr(api, "call", lambda cfg, q, **k: f["responses"].get(q, {"responses": {}}))
    path, slug = scaffold.scaffold_cup(tid, cid, host, cup_name=name, cups_root=str(tmp_path / "cups"))
    out = build_cup.build_cup(load_cup(path), dist_root=str(tmp_path / "dist"))
    base = tmp_path / "dist" / slug
    assert (base / "klubb" / "index.html").exists()
    assert any((base / d / "index.html").exists() for d in os.listdir(base) if d.startswith("u"))
    return out, base
def test_potatis(tmp_path, monkeypatch):
    out, base = _run(tmp_path, monkeypatch, "tests/fixtures/potatis.json",
                     "67026461", 72525561, "potatiscupen.cupmanager.net", "Potatiscupen 2026")
    html = next((base / d / "index.html") for d in os.listdir(base) if d.startswith("u")).read_text(encoding="utf-8")
    assert "Alingsås" in html and 'data-view="karta"' not in html   # indoor → no map tab
def test_ahus(tmp_path, monkeypatch):
    out, base = _run(tmp_path, monkeypatch, "tests/fixtures/ahus.json",
                     "70944382", 73383031, "ahusbeachhandboll.cupmanager.net", "Åhus 2026")
    assert out["apps"] >= 2
```

- [ ] **Step 2: Run** — `python3 -m pytest tests/test_acceptance.py -v` → PASS.

- [ ] **Step 3: Full suite** — `python3 -m pytest -q` → all green.

- [ ] **Step 4: Commit** — `git add tests/test_acceptance.py && git commit -q -m "test: acceptance — Potatiscupen (halls) + Åhus (beach) build age + club apps"`

---

## Self-Review

**Spec coverage:** platform repo + registry (T1, T13); engine config-object (T3–T10, T14); discover 2 IDs→cup.toml+report (T12–T13); club-wide app + class dimension (T10); two-level hub (T14 per-cup, T15 root); dispatch→PR (T16); Pages deploy + hash-gate + CF cron (T17); edge cases non-age/rule/venue (T6, T7, T12); cup-agnostic engine/map/branding (T9); acceptance both venue modes (T18). ✓

**Review fixes folded in:** verbatim-port broken → T1–T2 + T9 cup-agnostic pass; `club_name` via `NameClub` → T12; no `Tournament` name → `cup_name` dispatch input → T12/T16; `dist/` stays gitignored, PR = config+report, app = artifact, Pages on merge → T16/T17; fixtures monkeypatch `api.call` too + record division `$table`/NameClub → T4 + all fixture tests; `api_host` required input (no dead resolver) → T16; venue heuristic = all-`Bana N` → beach, Åhus fixture proves it → T12/T18; `rule_override` only-when-unknown + per-age → T6; `zoneinfo` tz, no month heuristic → T3/T7; fixture recording is its own task → T4; club-app test asserts `_teams_js` output → T10; `update`/deploy hash-gate → T17; scaffold prints slug (no `ls -t`) → T13/T16.

**Placeholder scan:** each code step has real code; refactor tasks give exact signatures + change lists. No "handle edge cases" left.

**Type consistency:** `CupConfig` fields consistent (`api_host, tournament_id, club_id, tz, venue_mode, venue_map, rule_override, rules_by_age, club_blue, palette, color_map, branding, rosters, pages_base`). Function names consistent across tasks: `build_cup_data(cfg)`, `build_standings(cfg)`, `rule_profile(name,cfg,age_slug=None)`, `render_app(cfg,group,standings,updated)`, `club_group(data)`, `build_all_apps(cfg,groups,standings,out_dir,updated)`, `discover(tid,cid,host,cup_name="")→{config,report}`, `scaffold_cup(tid,cid,host,cup_name="",cups_root)→(path,slug)`, `build_cup(cfg,dist_root)→{slug,apps,teams,matches}`, `build_root_hub(dist_root)`.

**Open (Fas 5+, not this plan):** venue-map rendering for `halls`, branding-finish UX, real default asset art in `engine/assets/`, repo name (`cup-apps` placeholder → also affects `pages_base`), whether to seed Åhus as a permanent cup here (fixture exists either way).
