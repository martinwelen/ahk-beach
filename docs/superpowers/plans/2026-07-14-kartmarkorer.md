# Kartmarkörer (live/nästa AHK-match) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Markera på kartan var Alingsås spelar nu (🔴) och var nästa match spelas (🟠), i både flik-karta och zoombar helskärm, med klickbara markörer som visar klass+lag.

**Architecture:** Statisk `bana_coords.py` (uppmätta pixlar → andelar) bäddas in som `BANA_XY`. Klient-JS (`mapMarkers()`) räknar live/nästa bland filtrerade matcher och placerar markörer via %-position i två lager (inline + helskärm). Helskärmens zoom-transform flyttas till en "stage" som omsluter bild + markörer så de följer med.

**Tech Stack:** Python 3.12 (stdlib, pytest), vanilla HTML/CSS/JS i `template.py`.

---

## Filstruktur
- **Skapa:** `bana_coords.py` — pixel-tabell + andelar.
- **Modifiera:** `build_apps.py` — importera + bädda in `__BANA_XY__`.
- **Modifiera:** `template.py` — `const BANA_XY`, markör-lager (DOM+CSS), stage-omslag, `mapMarkers()` + info-panel + hooks.
- **Test:** `tests/test_bana_coords.py` (ny), `tests/test_build_apps.py`, `tests/test_livescore.py`.

---

## Task 1: bana_coords.py

**Files:** Create `bana_coords.py`, Create `tests/test_bana_coords.py`

- [ ] **Step 1: Skapa `bana_coords.py`**
```python
# bana_coords.py
# -*- coding: utf-8 -*-
"""Pixelpositioner (mitten av varje bana) på karta.png, manuellt uppmätta.
Görs upplösningsoberoende (andel av bildmåtten) vid inbäddning i build_apps."""

IMG_W, IMG_H = 842, 1191

BANA_PX = {
    1: (513, 507), 2: (509, 392), 3: (561, 396), 4: (557, 305), 5: (687, 234),
    6: (767, 248), 7: (700, 158), 8: (778, 172), 9: (789, 92), 10: (610, 184),
    11: (335, 560), 12: (335, 475), 13: (383, 381), 14: (276, 655), 15: (265, 555),
    16: (229, 490), 17: (203, 555), 18: (142, 555), 19: (73, 548),
}


def bana_fractions():
    """{bana: [x_frac, y_frac]} i [0,1] för %-positionering i appen."""
    return {n: [round(x / IMG_W, 4), round(y / IMG_H, 4)] for n, (x, y) in BANA_PX.items()}
```

- [ ] **Step 2: Skriv test `tests/test_bana_coords.py`**
```python
# -*- coding: utf-8 -*-
import bana_coords as bc


def test_all_19_courts_present():
    assert set(bc.BANA_PX) == set(range(1, 20))


def test_fractions_in_range_and_correct():
    fr = bc.bana_fractions()
    assert all(0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 for x, y in fr.values())
    assert fr[9] == [round(789 / 842, 4), round(92 / 1191, 4)]
    assert len(fr) == 19
```

- [ ] **Step 3: Kör testet, verifiera PASS**
Run: `python3 -m pytest tests/test_bana_coords.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**
```bash
git add bana_coords.py tests/test_bana_coords.py
git commit -m "feat: bana_coords – uppmätta banpositioner på kartan"
```

---

## Task 2: build_apps bäddar in BANA_XY

**Files:** Modify `build_apps.py`, Modify `template.py`, Test `tests/test_build_apps.py`

- [ ] **Step 1: Skriv failing test — lägg till i `tests/test_build_apps.py`**
```python
def test_render_app_embeds_bana_xy():
    html = build_apps.render_app(_group(), standings=None, base="b", updated="u")
    assert "__BANA_XY__" not in html
    assert "0.9371" in html   # bana 9 x-andel (789/842)
    assert "const BANA_XY" in html
```

- [ ] **Step 2: Kör, verifiera FAIL**
Run: `python3 -m pytest tests/test_build_apps.py::test_render_app_embeds_bana_xy -v`
Expected: FAIL.

- [ ] **Step 3: Lägg till konstant i mallen**
I `template.py`, direkt efter raden `const TOURNAMENT_ID = "__TOURNAMENT_ID__";`, lägg till:
```javascript
const BANA_XY = __BANA_XY__;
```

- [ ] **Step 4: Bädda in i `build_apps.py`**
Lägg till import högst upp (efter `import roster_data`):
```python
import bana_coords
```
I `render_app`, lägg till i `.replace`-kedjan (efter `.replace("__TOURNAMENT_ID__", config.TOURNAMENT_ID)`):
```python
            .replace("__BANA_XY__", json.dumps(bana_coords.bana_fractions()))
```

- [ ] **Step 5: Kör, verifiera PASS**
Run: `python3 -m pytest tests/test_build_apps.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**
```bash
git add build_apps.py template.py tests/test_build_apps.py
git commit -m "feat: bädda in BANA_XY (banpositioner) i mallen"
```

---

## Task 3: DOM + CSS för markör-lager, stage och info-panel

**Files:** Modify `template.py`, Test `tests/test_livescore.py`

- [ ] **Step 1: Skriv failing test — lägg till i `tests/test_livescore.py`**
```python
def test_map_markers_markup():
    t = template.TEMPLATE
    assert 'id="mk-inline"' in t          # inline markör-lager
    assert 'id="mapzoom-stage"' in t      # stage som omsluter bild+markörer
    assert 'id="mk-zoom"' in t            # helskärms markör-lager
    assert 'id="mapinfo"' in t            # info-panel
```

- [ ] **Step 2: Kör, verifiera FAIL**
Run: `python3 -m pytest tests/test_livescore.py::test_map_markers_markup -v`
Expected: FAIL.

- [ ] **Step 3: Lägg markör-lager i inline-kartan**
I `template.py`, i `#map`-sektionen, byt:
```html
    <button class="mapbtn" id="mapopen" aria-label="Öppna kartan i helskärm">
      <img src="karta.png" alt="Områdeskarta – Åhus Beach Handboll" loading="lazy">
      <span class="maphint">Tryck för helskärm</span>
    </button>
```
mot:
```html
    <button class="mapbtn" id="mapopen" aria-label="Öppna kartan i helskärm">
      <img src="karta.png" alt="Områdeskarta – Åhus Beach Handboll" loading="lazy">
      <span class="mapmarkers" id="mk-inline" aria-hidden="true"></span>
      <span class="maphint">Tryck för helskärm</span>
    </button>
```

- [ ] **Step 4: Omslut helskärmsbilden i en stage + lägg markör-lager och info-panel**
I `template.py`, byt:
```html
  <div id="mapzoom" hidden>
    <button id="mapzoom-close" aria-label="Stäng karta">✕</button>
    <img id="mapzoom-img" src="karta.png" alt="Områdeskarta – Åhus Beach Handboll" draggable="false">
  </div>
```
mot:
```html
  <div id="mapzoom" hidden>
    <button id="mapzoom-close" aria-label="Stäng karta">✕</button>
    <div id="mapzoom-stage">
      <img id="mapzoom-img" src="karta.png" alt="Områdeskarta – Åhus Beach Handboll" draggable="false">
      <div class="mapmarkers" id="mk-zoom"></div>
    </div>
    <div id="mapinfo" hidden></div>
  </div>
```

- [ ] **Step 5: CSS — direkt före `</style>`, lägg in**
```css
.mapmarkers{position:absolute;inset:0;pointer-events:none}
.mk{position:absolute;transform:translate(-50%,-50%);width:20px;height:20px;border-radius:50%;
  border:2px solid #fff;box-shadow:0 1px 4px #0006}
.mk.live{background:#d22f27;animation:pulse 1.1s infinite}
.mk.next{background:#e8730c}
#mapzoom-stage{position:relative;touch-action:none}
#mapzoom-stage>#mapzoom-img{display:block}
#mk-zoom{pointer-events:none}
#mk-zoom .mk{pointer-events:auto;cursor:pointer;padding:0;border:2px solid #fff}
#mapinfo{position:fixed;left:12px;right:12px;bottom:calc(env(safe-area-inset-bottom,0px) + 14px);
  z-index:1002;background:#13293dee;color:#fff;border-radius:12px;padding:10px 14px;
  font-weight:600;font-size:.95rem;box-shadow:0 4px 16px #0007}
#mapinfo .k{font-weight:800;color:#e8730c;margin-right:6px}
#mapinfo .ls{color:#ff6a5f;font-weight:800;margin-left:8px}
```

- [ ] **Step 6: Byt helskärmsbildens max-mått så stagen ryms**
I `template.py`, byt CSS-raden:
```css
#mapzoom-img{max-width:100%;max-height:100%;user-select:none;-webkit-user-select:none;
  will-change:transform;touch-action:none}
```
mot:
```css
#mapzoom-img{max-width:100vw;max-height:100vh;user-select:none;-webkit-user-select:none;
  touch-action:none}
```
(`will-change:transform` flyttas till stagen i Task 4.)

- [ ] **Step 7: Kör test + full svit**
Run: `python3 -m pytest tests/test_livescore.py -v` sedan `python3 -m pytest -q`
Expected: alla PASS.

- [ ] **Step 8: Commit**
```bash
git add template.py tests/test_livescore.py
git commit -m "feat: DOM+CSS för kartmarkörer, stage och info-panel"
```

---

## Task 4: Flytta zoom-transformen till stagen

**Files:** Modify `template.py` (Kartzoom-IIFE), Test `tests/test_livescore.py`

- [ ] **Step 1: Skriv failing test — lägg till i `tests/test_livescore.py`**
```python
def test_zoom_transforms_stage_not_img():
    t = template.TEMPLATE
    assert "mapzoom-stage" in t
    assert "stage.style.transform" in t   # transformen på stagen → markörer följer med
```

- [ ] **Step 2: Kör, verifiera FAIL**
Run: `python3 -m pytest tests/test_livescore.py::test_zoom_transforms_stage_not_img -v`
Expected: FAIL.

- [ ] **Step 3: Peka om transformen till stagen**
I `template.py`, i Kartzoom-IIFE, byt raden:
```javascript
  const closeBtn=document.getElementById("mapzoom-close");
  if(!openBtn||!ov||!img||!closeBtn) return;
```
mot:
```javascript
  const closeBtn=document.getElementById("mapzoom-close");
  const stage=document.getElementById("mapzoom-stage");
  if(!openBtn||!ov||!img||!closeBtn||!stage) return;
  stage.style.willChange="transform";
```
Byt sedan `apply`-raden:
```javascript
  const apply=()=>{ clamp(); img.style.transform=`translate(${tx}px,${ty}px) scale(${scale})`; };
```
mot:
```javascript
  const apply=()=>{ clamp(); stage.style.transform=`translate(${tx}px,${ty}px) scale(${scale})`; };
```

- [ ] **Step 4: Kör test + full svit**
Run: `python3 -m pytest -q`
Expected: alla PASS.

- [ ] **Step 5: Commit**
```bash
git add template.py tests/test_livescore.py
git commit -m "feat: zoom-transform på stagen så kartmarkörer följer med"
```

---

## Task 5: mapMarkers()-logik, info-panel och hooks

**Files:** Modify `template.py`, Test `tests/test_livescore.py`

- [ ] **Step 1: Skriv failing test — lägg till i `tests/test_livescore.py`**
```python
def test_map_markers_logic():
    t = template.TEMPLATE
    assert "function mapMarkers(" in t
    assert "function showMapInfo(" in t
    assert 'state(m,now)==="live"' in t
    assert "BANA_XY[" in t
    assert "mapMarkers();" in t   # anropas (hook)
```

- [ ] **Step 2: Kör, verifiera FAIL**
Run: `python3 -m pytest tests/test_livescore.py::test_map_markers_logic -v`
Expected: FAIL.

- [ ] **Step 3: Lägg till mapMarkers() + showMapInfo()**
I `template.py`, hitta raden `setInterval(refreshData, 60000);` och lägg in **direkt före** den:
```javascript
// Kartmarkörer: var Alingsås spelar nu (live) / härnäst (up), på rätt bana.
function mapMarkers(){
  const now = Date.now();
  const rows = MATCHES.filter(matchPass);
  const liveOnes = rows.filter(m=>state(m,now)==="live");
  const fn = rows.find(m=>state(m,now)==="up");
  const next = fn ? rows.filter(m=>state(m,now)==="up" && m.ms===fn.ms) : [];
  const byBana = {};
  for(const m of next) if(BANA_XY[m.bana] && !byBana[m.bana]) byBana[m.bana]={m,kind:"next"};
  for(const m of liveOnes) if(BANA_XY[m.bana]) byBana[m.bana]={m,kind:"live"};
  const inline = document.getElementById("mk-inline");
  const zoom = document.getElementById("mk-zoom");
  if(inline) inline.innerHTML="";
  if(zoom) zoom.innerHTML="";
  for(const bana in byBana){
    const it = byBana[bana], xy = BANA_XY[bana];
    if(inline){
      const d=document.createElement("span");
      d.className="mk "+it.kind; d.style.left=(xy[0]*100)+"%"; d.style.top=(xy[1]*100)+"%";
      inline.appendChild(d);
    }
    if(zoom){
      const b=document.createElement("button");
      b.className="mk "+it.kind; b.style.left=(xy[0]*100)+"%"; b.style.top=(xy[1]*100)+"%";
      b.setAttribute("aria-label", `Bana ${bana}: ${it.m.home} mot ${it.m.away}`);
      b.addEventListener("click", ev=>{ ev.stopPropagation(); showMapInfo(it.m, bana); });
      zoom.appendChild(b);
    }
  }
  if(!Object.keys(byBana).length){ const info=document.getElementById("mapinfo"); if(info) info.hidden=true; }
}
function showMapInfo(m, bana){
  const info=document.getElementById("mapinfo"); if(!info) return;
  const s=liveState[m.id];
  const sc=(s && s.live && !s.finished) ? `<span class="ls">🔴 ${s.hg}–${s.ag}</span>` : "";
  info.innerHTML = `<span class="k">${esc(m.klass||"")}</span>${esc(m.home)} – ${esc(m.away)} · bana ${esc(bana)} · ${esc(m.t)}${sc}`;
  info.hidden=false;
}
```

- [ ] **Step 4: Hooka in mapMarkers() (render, setView, refresh)**
I `template.py`, i `render()`, byt raden:
```javascript
  if(typeof reapplyLive==="function") reapplyLive();
```
mot:
```javascript
  if(typeof reapplyLive==="function") reapplyLive();
  if(typeof mapMarkers==="function") mapMarkers();
```
I `setView(v)`, byt raden:
```javascript
  elMap.hidden = v!=="karta";
```
mot:
```javascript
  elMap.hidden = v!=="karta";
  if(v==="karta" && typeof mapMarkers==="function") mapMarkers();
```

- [ ] **Step 5: Uppdatera markörer när helskärm öppnas + dölj info vid stängning**
I `template.py`, i Kartzoom-IIFE, byt:
```javascript
  const open=()=>{ ov.hidden=false; document.body.style.overflow="hidden"; reset(); };
  const close=()=>{ ov.hidden=true; document.body.style.overflow=""; pts.clear(); lastDist=0; };
```
mot:
```javascript
  const open=()=>{ ov.hidden=false; document.body.style.overflow="hidden"; reset(); if(typeof mapMarkers==="function") mapMarkers(); };
  const close=()=>{ ov.hidden=true; document.body.style.overflow=""; pts.clear(); lastDist=0; const info=document.getElementById("mapinfo"); if(info) info.hidden=true; };
```

- [ ] **Step 6: Kör test + full svit**
Run: `python3 -m pytest -q`
Expected: alla PASS.

- [ ] **Step 7: Commit**
```bash
git add template.py tests/test_livescore.py
git commit -m "feat: kartmarkörer-logik (live/nästa) + klickbar info-panel"
```

---

## Task 6: Bygg, verifiera i webbläsare, deploya

- [ ] **Step 1: Full svit**
Run: `python3 -m pytest -q` → alla PASS.

- [ ] **Step 2: Bygg + kontroller**
```bash
cd ~/dev/ahk-beach
python3 build_apps.py >/dev/null 2>&1 && echo byggt
grep -c "function mapMarkers" u12/index.html
grep -o '"9": *\[0.9371' u12/index.html | head -1
git checkout -- . ; git clean -fq u8 u10 u11 u12 u13 u14 u16 u17 u18 ; rm -rf dist-u15
```
Expected: `byggt`, mapMarkers=1, BANA_XY-andel finns; rent arbetsträd.

- [ ] **Step 3: Manuell webbläsarverifiering**
Servera en byggd app och öppna Karta-fliken:
- När en Alingsås-match är live/nästa: 🔴/🟠-prick sitter **mitt på rätt bana** (jämför mot bannumren på kartan).
- Helskärm: nyp/panorera → markörerna **följer med** och sitter kvar på banorna.
- Tryck på en markör → info-panel visar klass + lag (+ tid, livescore om live).
- Inga live/nästa → inga prickar.
- Inga konsol-fel.

- [ ] **Step 4: Deploya (finishing-a-development-branch → merge till main + force-run)**
Merge grenen till `main`, sedan `gh workflow run "Uppdatera schema" -f force=true`. Verifiera live.

---

## Noteringar
- Inline-markörerna är icke-interaktiva (`pointer-events:none`) så tryck på flik-kartan öppnar helskärm; helskärmsmarkörerna är knappar (info-panel).
- Info-panelen ligger utanför zoom-transformen (skärm-fäst) så texten inte skalas.
- Bana som saknas i `BANA_XY` hoppas över (ingen krasch).
