# Livescore + videolänk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Visa löpande livescore (klient-poll av `MatchResult`) och en solidsport-videolänk (bana 1–2) på matchkorten, och gör hero-toppen till en multi-lista som visar alla live / alla samtidigt-nästa matcher.

**Architecture:** Roboten berikar `data.json` med match-`id` (för poll) och `video`-URL (bana 1–2). Mallens klient-JS pollar `MatchResult({id})` var ~10:e s för matcher i tidsfönster (CORS öppet) och uppdaterar kort/hero in-place. Hero blir en lista av featured-kort.

**Tech Stack:** Python 3.12 (stdlib, pytest), vanilla HTML/CSS/JS i `template.py`. Ingen ny körtidsdependens.

---

## Filstruktur

- **Modifiera:** `fetch_data.py` — `normalize_match` lägger `id` + `video`; ny helper `_video_url`.
- **Modifiera:** `build_apps.py` — `_js_matches` skickar `id`/`video`; `render_app` bäddar in `__API_HOST__`/`__TOURNAMENT_ID__`.
- **Modifiera:** `template.py` — placeholders, poll-modul, kort-badge + videolänk, multi-hero, CSS.
- **Test:** `tests/test_fetch_data.py`, `tests/test_build_apps.py`, `tests/test_livescore.py` (ny).

---

## Task 1: `data.json` – match-id per match

**Files:**
- Modify: `fetch_data.py` (`normalize_match` return-dict, ~rad 100-114)
- Test: `tests/test_fetch_data.py`

- [ ] **Step 1: Skriv failing test**

Lägg till i `tests/test_fetch_data.py`:
```python
def test_normalize_match_includes_cupmanager_id():
    import fetch_data
    e = {"id": 81848529, "home": {}, "away": {}, "start": 1784034000000,
         "division": {}, "arena": {}, "result": {}}
    store = {}
    reg = {7: {"id": 7, "age_slug": "u15", "slug": "u15-p-bla", "gender": "P",
               "rule": "Classic", "color": "#1f5fbf", "age": 15}}
    # tvinga hemmalaget att vara vårt via monkey-fri väg: patcha ref_id/name_of
    import api
    orig = (api.ref_id, api.name_of, api.store_get)
    api.ref_id = lambda n: 7
    api.name_of = lambda x: "Lag"
    api.store_get = lambda s, r: {}
    try:
        m = fetch_data.normalize_match(e, store, reg)
    finally:
        api.ref_id, api.name_of, api.store_get = orig
    assert m is not None
    assert m["id"] == 81848529
```

- [ ] **Step 2: Kör testet, verifiera FAIL**

Run: `python3 -m pytest tests/test_fetch_data.py::test_normalize_match_includes_cupmanager_id -v`
Expected: FAIL (`KeyError: 'id'`).

- [ ] **Step 3: Lägg till `id` i return-dicten**

I `fetch_data.py`, i `normalize_match`, lägg till raden i den returnerade dicten (direkt efter `"age_slug": team["age_slug"], "slug": team["slug"],`):
```python
        "id": e.get("id"),
```

- [ ] **Step 4: Kör testet, verifiera PASS**

Run: `python3 -m pytest tests/test_fetch_data.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fetch_data.py tests/test_fetch_data.py
git commit -m "feat: inkludera cupmanager match-id i data.json"
```

---

## Task 2: `data.json` – video-URL för bana 1 & 2

**Files:**
- Modify: `fetch_data.py` (ny helper `_video_url`; `normalize_match` sätter `video`)
- Test: `tests/test_fetch_data.py`

- [ ] **Step 1: Skriv failing test**

Lägg till i `tests/test_fetch_data.py`:
```python
def test_video_url_extracts_external_link():
    import fetch_data, api
    orig = api.call
    api.call = lambda q: {"responses": {"Video({id:1})": {"entity": {
        "__typename": "Video", "externalLink": "https://solidsport.com/x"}}}}
    try:
        assert fetch_data._video_url(123) == "https://solidsport.com/x"
        api.call = lambda q: {"responses": {}}
        assert fetch_data._video_url(123) is None
        assert fetch_data._video_url(None) is None
    finally:
        api.call = orig


def test_normalize_match_sets_video_only_for_courts_1_2():
    import fetch_data, api
    reg = {7: {"id": 7, "age_slug": "u15", "slug": "u15-p-bla", "gender": "P",
               "rule": "Classic", "color": "#1f5fbf", "age": 15}}
    orig = (api.ref_id, api.name_of, api.store_get, api.call)
    api.ref_id = lambda n: 7
    api.name_of = lambda x: "Lag"
    api.call = lambda q: {"responses": {"v": {"entity": {
        "__typename": "Video", "externalLink": "https://solidsport.com/x"}}}}
    def mk(bana):
        api.store_get = lambda s, r: {"completeName": f"Bana {bana}"}
        return fetch_data.normalize_match(
            {"id": 1, "home": {}, "away": {}, "start": 1784034000000,
             "division": {}, "arena": {}, "result": {}}, {}, reg)
    try:
        assert mk(2)["video"] == "https://solidsport.com/x"   # bana 2 → video
        assert mk(15)["video"] is None                        # annan bana → ingen
    finally:
        api.ref_id, api.name_of, api.store_get, api.call = orig
```

- [ ] **Step 2: Kör testet, verifiera FAIL**

Run: `python3 -m pytest tests/test_fetch_data.py -k "video" -v`
Expected: FAIL (`_video_url` saknas; `video` saknas i dicten).

- [ ] **Step 3: Lägg till helper + fältet**

I `fetch_data.py`, lägg till helpern (t.ex. direkt före `normalize_match`):
```python
def _video_url(mid):
    """Resolvar Match($video) → solidsport externalLink, annars None."""
    if not mid:
        return None
    try:
        resp = api.call(f"Match({{id:{mid}}})$video").get("responses", {})
    except Exception:
        return None
    for v in resp.values():
        ent = v.get("entity", {}) if isinstance(v, dict) else {}
        if isinstance(ent, dict) and ent.get("__typename") == "Video":
            return ent.get("externalLink")
    return None
```
I `normalize_match`, direkt efter raden `bana = _bana_num(...)`, lägg till:
```python
    video = _video_url(e.get("id")) if bana in (1, 2) else None
```
och lägg till i return-dicten (t.ex. efter `"bana": bana,`):
```python
        "video": video,
```

- [ ] **Step 4: Kör testet, verifiera PASS**

Run: `python3 -m pytest tests/test_fetch_data.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fetch_data.py tests/test_fetch_data.py
git commit -m "feat: hämta solidsport-videolänk för bana 1-2 till data.json"
```

---

## Task 3: `_js_matches` skickar med id + video

**Files:**
- Modify: `build_apps.py` (`_js_matches`, ~rad 46-61)
- Test: `tests/test_build_apps.py`

- [ ] **Step 1: Skriv failing test**

Lägg till i `tests/test_build_apps.py`:
```python
def test_js_matches_includes_id_and_video():
    g = _group()
    g["teams"] = [{"id": 1, "slug": "u14-p-bla", "team_name": "A", "color": "#1f5fbf", "gender": "P"}]
    g["matches"] = [{"start_ms": 1, "tid": "10:00", "bana": 2, "slug": "u14-p-bla",
                     "grupp": "G1", "hemma": "A", "borta": "B", "hb": "Hemma",
                     "day_label": "x", "color": "#1f5fbf", "gender": "P", "result": None,
                     "id": 999, "video": "https://solidsport.com/x"}]
    out = build_apps._js_matches(g)[0]
    assert out["id"] == 999
    assert out["video"] == "https://solidsport.com/x"
```

- [ ] **Step 2: Kör testet, verifiera FAIL**

Run: `python3 -m pytest tests/test_build_apps.py::test_js_matches_includes_id_and_video -v`
Expected: FAIL (`KeyError: 'id'`).

- [ ] **Step 3: Lägg till fälten i `_js_matches`**

I `build_apps.py`, i `_js_matches`, i dicten som appendas, lägg till (efter raden `"res": m.get("result") if has_res else None,`):
```python
            "id": m.get("id"),
            "video": m.get("video"),
```

- [ ] **Step 4: Kör testet, verifiera PASS**

Run: `python3 -m pytest tests/test_build_apps.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add build_apps.py tests/test_build_apps.py
git commit -m "feat: _js_matches skickar match-id och videolänk till mallen"
```

---

## Task 4: Bädda in API_HOST + TOURNAMENT_ID i mallen

**Files:**
- Modify: `template.py` (JS-konstantblock, ~rad 306-311)
- Modify: `build_apps.py` (`render_app`, substitutionskedjan)
- Test: `tests/test_build_apps.py`

- [ ] **Step 1: Skriv failing test**

Lägg till i `tests/test_build_apps.py`:
```python
def test_render_app_embeds_api_host_and_tournament():
    html = build_apps.render_app(_group(), standings=None, base="b", updated="u")
    import config
    assert config.API_HOST in html
    assert config.TOURNAMENT_ID in html
    assert "__API_HOST__" not in html and "__TOURNAMENT_ID__" not in html
```

- [ ] **Step 2: Kör testet, verifiera FAIL**

Run: `python3 -m pytest tests/test_build_apps.py::test_render_app_embeds_api_host_and_tournament -v`
Expected: FAIL (host/tournament finns inte i mallen).

- [ ] **Step 3: Lägg till placeholders i mallen**

I `template.py`, direkt efter raden `const DUR = __DUR_MIN__ * 60000;`, lägg till:
```javascript
const API_HOST = "__API_HOST__";
const TOURNAMENT_ID = "__TOURNAMENT_ID__";
```

- [ ] **Step 4: Substituera i `render_app`**

I `build_apps.py`, i `render_app`, lägg till två `.replace` i kedjan (t.ex. efter `.replace("__DUR_MIN__", str(group["profile"]["duration_min"]))`):
```python
            .replace("__API_HOST__", config.API_HOST)
            .replace("__TOURNAMENT_ID__", config.TOURNAMENT_ID)
```

- [ ] **Step 5: Kör testet, verifiera PASS**

Run: `python3 -m pytest tests/test_build_apps.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add template.py build_apps.py tests/test_build_apps.py
git commit -m "feat: bädda in API_HOST och TOURNAMENT_ID i mallen för klient-poll"
```

---

## Task 5: Matchkort – data-mid, livescore-plats och videolänk

**Files:**
- Modify: `template.py` (matchkortets HTML i `render`, ~rad 394-404; CSS före `</style>`)
- Test: `tests/test_livescore.py` (ny)

- [ ] **Step 1: Skriv failing test**

Skapa `tests/test_livescore.py`:
```python
# -*- coding: utf-8 -*-
import template


def test_match_card_has_mid_and_live_slot_and_video():
    t = template.TEMPLATE
    assert 'data-mid="${m.id||' in t            # kortet bär match-id
    assert 'class="lscore"' in t                 # plats för livescore-badge
    assert 'class="vidlink"' in t                # videolänk (bana 1-2)
    assert 'm.video' in t                        # renderas villkorat på video
```

- [ ] **Step 2: Kör testet, verifiera FAIL**

Run: `python3 -m pytest tests/test_livescore.py::test_match_card_has_mid_and_live_slot_and_video -v`
Expected: FAIL.

- [ ] **Step 3: Uppdatera matchkortet**

I `template.py`, i `render()`, byt ut hela `<article ...>...</article>`-mallen (raderna som börjar med `` `<article class="match ${st}" ...`` och slutar med `</article>`) mot:
```javascript
      `<article class="match ${st}" data-mid="${m.id||''}" style="--c:#${m.color}">
        <div class="t">${m.t}${st==="live"?'<small class="nowtag">NU</small>':""}</div>
        <div>
          <div class="chips"><span class="lagchip" style="background:#${m.color}">${esc(m.lag)}</span>
            ${m.klass?`<span class="klasschip">${esc(m.klass)}</span>`:""}<span class="grp">${esc(m.grp)}</span></div>
          <div class="vs"><span class="${homeAli?"ali":""}">${esc(m.home)}</span> – <span class="${homeAli?"":"ali"}">${esc(m.away)}</span></div>
          <div class="lscore" hidden></div>
          ${m.res ? `<div class="score"><b class="${m.res.hg>m.res.ag?'w':m.res.hg<m.res.ag?'l':''}">${m.res.hg}</b><span class="x">–</span><b class="${m.res.ag>m.res.hg?'w':m.res.ag<m.res.hg?'l':''}">${m.res.ag}</b></div>` : ""}
          ${m.video?`<a class="vidlink" href="${m.video}" target="_blank" rel="noopener" aria-label="Se video på solidsport">▶ Video</a>`:""}
        </div>
        <div class="bana"><small>BANA</small><b>${esc(m.bana)}</b></div>
      </article>`;
```

- [ ] **Step 4: Lägg till CSS**

I `template.py`, direkt före `</style>`, lägg in:
```css
.lscore{display:inline-flex;align-items:center;gap:6px;margin-top:6px;font-weight:800;
  color:#d22f27;font-size:.95rem}
.lscore .pulse{width:8px;height:8px;border-radius:50%;background:#d22f27;animation:pulse 1.1s infinite}
.vidlink{display:inline-block;margin-top:6px;font-weight:800;font-size:.82rem;color:#fff;
  background:#d22f27;padding:3px 9px;border-radius:999px;text-decoration:none}
```

- [ ] **Step 5: Kör testet, verifiera PASS**

Run: `python3 -m pytest tests/test_livescore.py -v`
Expected: PASS.

- [ ] **Step 6: Kör hela sviten**

Run: `python3 -m pytest -q`
Expected: alla PASS.

- [ ] **Step 7: Commit**

```bash
git add template.py tests/test_livescore.py
git commit -m "feat: matchkort med data-mid, livescore-plats och videolänk"
```

---

## Task 6: Livescore-pollmodul (klient)

**Files:**
- Modify: `template.py` (JS före service-worker-registreringen; hook i `render`)
- Test: `tests/test_livescore.py`

- [ ] **Step 1: Skriv failing test**

Lägg till i `tests/test_livescore.py`:
```python
def test_template_has_livescore_poll_module():
    t = template.TEMPLATE
    assert "MatchResult(" in t                       # rätt endpoint
    assert "encodeURIComponent" in t                 # bygger call-param säkert
    assert "visibilitychange" in t                   # pausar när fliken döljs
    assert "homeGoals" in t and "awayGoals" in t     # läser ställningen
    assert "setInterval(pollWindow" in t             # pollar på intervall


def test_render_reapplies_livescore_after_rerender():
    # render() måste återapplicera känt live-state på nyritade noder
    assert "reapplyLive()" in template.TEMPLATE
```

- [ ] **Step 2: Kör testet, verifiera FAIL**

Run: `python3 -m pytest tests/test_livescore.py -k "poll or reapplies" -v`
Expected: FAIL.

- [ ] **Step 3: Lägg till pollmodulen**

I `template.py`, hitta raden:
```javascript
if("serviceWorker" in navigator){ navigator.serviceWorker.register("sw.js").catch(()=>{}); }
```
och lägg in **direkt före** den:
```javascript
// Livescore: polla MatchResult för matcher i tidsfönster; uppdatera kort/hero in-place.
const liveState = {};   // id -> {hg, ag, live, finished}
function applyLive(id){
  const s = liveState[id];
  for(const el of document.querySelectorAll(`[data-mid="${id}"] .lscore`)){
    if(s && s.live && !s.finished){
      el.innerHTML = `<span class="pulse"></span>LIVE ${s.hg}–${s.ag}`; el.hidden = false;
    } else { el.hidden = true; el.innerHTML = ""; }
  }
}
function reapplyLive(){ for(const id in liveState) applyLive(id); }
function pollOne(id){
  const call = encodeURIComponent(`MatchResult({id:${id}})`);
  const url = `https://${API_HOST}/rest/results_api/call?call=${call}&lang=sv&tournamentId=${TOURNAMENT_ID}`;
  fetch(url).then(r=>r.json()).then(j=>{
    for(const v of Object.values(j.responses||{})){
      const e = (v&&v.entity)||{};
      if(e.__typename==="MatchResult"){
        liveState[id] = {hg:e.homeGoals, ag:e.awayGoals, live:e.live, finished:e.finished};
        applyLive(id);
      }
    }
  }).catch(()=>{});
}
function pollWindow(){
  if(document.visibilityState!=="visible") return;
  const now = Date.now();
  for(const m of MATCHES){
    if(!m.id) continue;
    const inWindow = now >= m.ms && now < m.ms + DUR + 600000;
    if(inWindow && !(liveState[m.id]||{}).finished) pollOne(m.id);
  }
}
setInterval(pollWindow, 10000);
document.addEventListener("visibilitychange", ()=>{ if(document.visibilityState==="visible") pollWindow(); });
pollWindow();
```

- [ ] **Step 4: Anropa `reapplyLive()` efter omritning**

I `template.py`, i `render()`, byt raden:
```javascript
  list.innerHTML = html;
```
mot:
```javascript
  list.innerHTML = html;
  if(typeof reapplyLive==="function") reapplyLive();
```

- [ ] **Step 5: Kör testet, verifiera PASS**

Run: `python3 -m pytest tests/test_livescore.py -v`
Expected: PASS.

- [ ] **Step 6: Kör hela sviten**

Run: `python3 -m pytest -q`
Expected: alla PASS.

- [ ] **Step 7: Commit**

```bash
git add template.py tests/test_livescore.py
git commit -m "feat: klient pollar MatchResult och visar livescore på korten"
```

---

## Task 7: Multi-hero (alla live / alla samtidigt-nästa)

**Files:**
- Modify: `template.py` (hero-delen av `render`, ~rad 367-385; countdown-intervall rad 415-416; scroll-villkor rad 408; CSS före `</style>`)
- Test: `tests/test_livescore.py`

- [ ] **Step 1: Skriv failing test**

Lägg till i `tests/test_livescore.py`:
```python
def test_template_has_multihero_logic():
    t = template.TEMPLATE
    assert 'filter(m=>state(m,now)==="live")' in t   # alla live
    assert "featured" in t                           # lista av featured
    assert "herolist" in t                           # multi-container
    assert "m.ms===" in t or "m.ms ===" in t         # samma starttid = samma "nästa"
```

- [ ] **Step 2: Kör testet, verifiera FAIL**

Run: `python3 -m pytest tests/test_livescore.py::test_template_has_multihero_logic -v`
Expected: FAIL.

- [ ] **Step 3: Byt ut hero-blocket**

I `template.py`, i `render()`, byt ut hela blocket från `// hero: pågående annars nästa` t.o.m. den avslutande `}` för else-grenen (raderna 367–385) mot:
```javascript
  // hero: alla pågående; annars alla kommande som delar tidigaste starttid
  const liveOnes = rows.filter(m=>state(m,now)==="live");
  let featured;
  if(liveOnes.length){ featured = liveOnes; }
  else { const fn = rows.find(m=>state(m,now)==="up");
         featured = fn ? rows.filter(m=>state(m,now)==="up" && m.ms===fn.ms) : []; }
  const hero = $("#hero");
  if(featured.length){
    hero.innerHTML = `<div class="herolist${featured.length>1?' many':''}">` + featured.map(hm=>{
      const isLive = state(hm,now)==="live";
      return `<div class="hero ${isLive?'live':''}" data-mid="${hm.id||''}">
        <div class="tag">Bana ${esc(hm.bana)}</div>
        <div class="lbl">${isLive?'<span class="pulse"></span>Pågår nu':'Härnäst'}</div>
        <div class="mt">${esc(hm.home)} <span style="opacity:.7">vs</span> ${esc(hm.away)}</div>
        <div class="sub">${esc(hm.lag)}${hm.klass?' · '+esc(hm.klass):''} · ${esc(hm.grp)} · ${hm.t} · ${esc(hm.day)}</div>
        <div class="lscore" hidden></div>
        <div class="cd" data-ms="${hm.ms}">${isLive?'Spelas nu':fmtCountdown(hm.ms-now)}</div>
        ${hm.video?`<a class="vidlink" href="${hm.video}" target="_blank" rel="noopener" aria-label="Se video på solidsport">▶ Video</a>`:''}
      </div>`;
    }).join('') + `</div>`;
  } else {
    hero.innerHTML = rows.length
      ? `<div class="hero"><div class="lbl">Klart</div><div class="mt">Alla matcher spelade</div></div>` : "";
  }
```

- [ ] **Step 4: Uppdatera scroll-villkoret (hm finns inte längre)**

I `template.py`, i `render()`, byt raden:
```javascript
  if(!render._scrolled && rows.some(m=>state(m,now)==="past") && hm){
```
mot:
```javascript
  if(!render._scrolled && rows.some(m=>state(m,now)==="past") && featured.length){
```

- [ ] **Step 5: Uppdatera nedräkningen till att gälla alla hero-kort**

I `template.py`, byt intervallet:
```javascript
setInterval(()=>{ const cd=document.querySelector(".hero .cd"); if(cd&&cd.dataset.ms){
  const left=+cd.dataset.ms-Date.now(); cd.textContent = left>0?fmtCountdown(left):"Spelas nu"; }}, 1000);
```
mot:
```javascript
setInterval(()=>{ for(const cd of document.querySelectorAll(".hero .cd")){ if(cd.dataset.ms){
  const left=+cd.dataset.ms-Date.now(); cd.textContent = left>0?fmtCountdown(left):"Spelas nu"; }}}, 1000);
```

- [ ] **Step 6: Anropa `reapplyLive()` även efter hero ritats**

I `template.py`, i `render()`, direkt efter `list.innerHTML = html;`-raden byttes i Task 6 finns redan `reapplyLive()`. Säkerställ att den ligger **efter** att både hero och list ritats (den gör det redan eftersom hero sätts före listan i `render`). Ingen ny ändring behövs – verifiera bara att `reapplyLive()` anropas en gång i slutet av `render()`.

- [ ] **Step 7: Lägg till multi-hero-CSS**

I `template.py`, direkt före `</style>`, lägg in:
```css
.herolist{display:flex;flex-direction:column;gap:10px}
.herolist.many .hero{padding:12px 14px}
.herolist.many .hero .mt{font-size:clamp(1.05rem,4vw,1.4rem)}
.herolist.many .hero .cd{font-size:1.1rem;margin-top:8px}
.hero{position:relative}
```

- [ ] **Step 8: Kör testet + hela sviten**

Run: `python3 -m pytest -q`
Expected: alla PASS.

- [ ] **Step 9: Commit**

```bash
git add template.py tests/test_livescore.py
git commit -m "feat: multi-hero visar alla live / alla samtidigt-nästa matcher"
```

---

## Task 8: Bygg lokalt och verifiera

- [ ] **Step 1: Kör hela testsviten**

Run: `python3 -m pytest -q`
Expected: alla PASS.

- [ ] **Step 2: Bygg apparna lokalt**

Run:
```bash
cd ~/dev/ahk-beach
python3 build_apps.py >/dev/null && echo byggt
grep -c "MatchResult(" u17/index.html          # poll-modulen finns
grep -o "const API_HOST = \"[^\"]*\"" u17/index.html
```
Expected: `byggt`, grep ≥1, API_HOST = `ahusbeachhandboll.cupmanager.net`.

- [ ] **Step 3: Städa byggartefakter (behåll källändringar)**

Run:
```bash
git checkout -- . 2>/dev/null; git clean -fq u8 u10 u11 u12 u13 u14 u16 u17 u18 2>/dev/null; rm -rf dist-u15
git status --porcelain
```
Expected: rent arbetsträd.

- [ ] **Step 4: Manuell webbläsarverifiering (mot en live-matchsession)**

Servera en byggd app (`python3 -m http.server` i en byggd app-katalog eller repo-roten) och verifiera:
- Under en pågående live-scoutad Alingsås-match: kortet visar **🔴 LIVE h–a** som uppdateras var ~10:e s.
- Bana 1/2-matcher visar **▶ Video**-länk som öppnar solidsport.
- Multi-hero: när flera matcher är live/nästa-samtidigt visas alla som staplade kort; en ensam = stor ruta.
- Dölj fliken → polling pausar (inga nya `MatchResult`-anrop i nätverksfliken); visa igen → återupptas.
- Inga konsol-fel.

Detta steg är manuellt (klient-livebeteendet kan inte enhetstestas i Python-bygget).

---

## Noteringar

- **Roboten** plockar upp `id`/`video`/slutresultat var 10:e min; **klienten** ger löpande siffra däremellan. Oberoende.
- **CORS** är verifierat öppet för `martinwelen.github.io`, så direkt-poll funkar; ingen server/proxy.
- **Video** gated till bana 1–2 i datalagret (där solidsport-videon faktiskt finns).
- `MatchResult`-pollen stängs per match när `finished:true`, och pausar globalt när fliken är dold → sparsamt även med ~6+ samtidiga live-matcher.
- Ingen `MatchFeed`/statistik/ljud (utanför scope).
