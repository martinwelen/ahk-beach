# Områdeskarta-flik Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lägg till en alltid-synlig "Karta"-flik i alla appar som visar arenans områdeskarta, med tryck-för-helskärm och nyp-zoom/panorering, offline och beroendefritt.

**Architecture:** `karta.png` bäddas in i repo-roten och kopieras per app av `build_apps.py` (som ikonerna). Mallen (`template.py`) får en Karta-flik + en `#map`-vy (inline-bild) + ett `#mapzoom`-helskärmsöverlägg med en liten vanilla-JS pinch/pan-hanterare (Pointer Events, inga beroenden).

**Tech Stack:** Python 3.12 (stdlib, pytest), vanilla HTML/CSS/JS i `template.py`.

---

## Filstruktur

- **Skapa:** `karta.png` (repo-roten) — statisk kartbild, kopieras per app.
- **Modifiera:** `build_apps.py` — kopiera `karta.png` till varje app-katalog + `dist-u15/`.
- **Modifiera:** `template.py` — Karta-flik, `#map`-vy, `setView`-wiring, `#mapzoom`-overlay, CSS, pinch/pan-JS.
- **Test:** `tests/test_build_apps.py` (kopiering), `tests/test_map.py` (ny — mall-markörer).

---

## Task 1: Bädda in karta.png och kopiera den per app

**Files:**
- Create: `karta.png` (repo-roten)
- Modify: `build_apps.py` (asset-listan + kopieringsloopen, kring rad 99-131)
- Test: `tests/test_build_apps.py`

- [ ] **Step 1: Ladda ner kartan till repo-roten**

Run:
```bash
cd ~/dev/ahk-beach
curl -sL -o karta.png "https://ahusbeach.com/app/uploads/2026/06/Omradeskarta_Handboll-A3-2026_webb.png"
python3 -c "import struct; d=open('karta.png','rb').read(); assert d[:8]==b'\x89PNG\r\n\x1a\n', 'inte PNG'; w,h=struct.unpack('>II',d[16:24]); print(f'OK: PNG {w}x{h}, {len(d)} bytes')"
```
Expected: `OK: PNG 842x1191, 478646 bytes` (storleken kan variera något om arrangören bytt filen — det viktiga är att det är en giltig PNG).

- [ ] **Step 2: Skriv failing test**

Lägg till i `tests/test_build_apps.py`:
```python
def test_build_apps_copies_map_to_every_app(tmp_path, monkeypatch):
    data = {"meta": {"generated": "x"},
            "groups": {"u14": _group("u14", "U14"), "u15": _group("u15", "U15")}}
    (tmp_path / "data.json").write_text(json.dumps(data), encoding="utf-8")
    for ic in ("icon-192.png", "icon-512.png", "icon-512-maskable.png",
               "icon-180.png", "favicon-32.png", "karta.png"):
        (tmp_path / ic).write_bytes(b"x")
    monkeypatch.setattr(build_apps, "ROOT", str(tmp_path))
    monkeypatch.setattr(build_apps, "DATA_JSON", str(tmp_path / "data.json"))
    monkeypatch.setattr(build_apps, "STANDINGS_JSON", str(tmp_path / "nope.json"))
    build_apps.main()
    assert (tmp_path / "u14" / "karta.png").exists()
    assert (tmp_path / "dist-u15" / "karta.png").exists()
```

- [ ] **Step 3: Kör testet, verifiera FAIL**

Run: `python3 -m pytest tests/test_build_apps.py::test_build_apps_copies_map_to_every_app -v`
Expected: FAIL (`karta.png` kopieras inte — filen saknas i app-katalogen).

- [ ] **Step 4: Lägg karta.png i asset-listan**

I `build_apps.py`, hitta:
```python
_ICONS = ("icon-192.png", "icon-512.png", "icon-512-maskable.png",
          "icon-180.png", "favicon-32.png")
```
Lägg till direkt under den:
```python
# Statiska filer som kopieras oförändrade till varje app-katalog.
_ASSETS = _ICONS + ("karta.png",)
```
I `main()`, byt kopieringsloopen från:
```python
        for ic in _ICONS:
            src = os.path.join(ROOT, ic)
            if os.path.exists(src):
                shutil.copy(src, os.path.join(out_dir, ic))
```
till:
```python
        for asset in _ASSETS:
            src = os.path.join(ROOT, asset)
            if os.path.exists(src):
                shutil.copy(src, os.path.join(out_dir, asset))
```

- [ ] **Step 5: Kör testet, verifiera PASS**

Run: `python3 -m pytest tests/test_build_apps.py -v`
Expected: PASS (både det nya testet och det befintliga dir-testet).

- [ ] **Step 6: Commit**

```bash
git add karta.png build_apps.py tests/test_build_apps.py
git commit -m "feat: bädda in områdeskarta (karta.png) och kopiera den per app"
```

---

## Task 2: Karta-flik + inline-vy + setView-wiring + CSS

**Files:**
- Modify: `template.py` — flikrad (rad 236-241), vy-sektioner (rad 245-250), element-refs (rad 393-398), `setView` (rad 406-417), CSS (före `</style>`)
- Test: `tests/test_map.py` (ny)

- [ ] **Step 1: Skriv failing test**

Skapa `tests/test_map.py`:
```python
# -*- coding: utf-8 -*-
import build_apps
import template


def _group():
    return {"age": 14, "label": "U14", "rule": "Classic",
            "profile": {"duration_min": 11, "has_results": True,
                        "has_tables": True, "has_playoffs": True},
            "teams": [{"id": 1, "slug": "u14-p-bla", "team_name": "Blå",
                       "color": "#1f5fbf", "gender": "P"}],
            "matches": []}


def test_template_has_always_visible_karta_tab():
    # Karta-fliken finns och är INTE hidden (till skillnad från data-flikarna).
    tab = '<button class="tab" id="tab-karta" data-view="karta">Karta</button>'
    assert tab in template.TEMPLATE


def test_template_has_map_section_with_image():
    assert 'id="map"' in template.TEMPLATE
    assert 'karta.png' in template.TEMPLATE
    assert 'id="mapopen"' in template.TEMPLATE


def test_setview_toggles_map_section():
    assert 'elMap.hidden = v!=="karta"' in template.TEMPLATE


def test_rendered_app_contains_karta_tab():
    html = build_apps.render_app(_group(), standings=None, base="b", updated="u")
    assert 'data-view="karta"' in html
    assert 'karta.png' in html
```

- [ ] **Step 2: Kör testet, verifiera FAIL**

Run: `python3 -m pytest tests/test_map.py -v`
Expected: FAIL (Karta-fliken/`#map`/`elMap` finns inte i mallen).

- [ ] **Step 3: Lägg till Karta-flikknappen**

I `template.py`, i flikraden, byt:
```html
    <button class="tab" id="tab-trupp" data-view="trupp" aria-pressed="false" hidden>Trupp</button>
  </nav>
```
till:
```html
    <button class="tab" id="tab-trupp" data-view="trupp" aria-pressed="false" hidden>Trupp</button>
    <button class="tab" id="tab-karta" data-view="karta">Karta</button>
  </nav>
```

- [ ] **Step 4: Lägg till #map-vy-sektionen**

I `template.py`, byt:
```html
  <section id="roster" hidden></section>
```
till:
```html
  <section id="roster" hidden></section>
  <section id="map" hidden>
    <button class="mapbtn" id="mapopen" aria-label="Öppna kartan i helskärm">
      <img src="karta.png" alt="Områdeskarta – Åhus Beach Handboll" loading="lazy">
      <span class="maphint">Tryck för helskärm</span>
    </button>
    <p class="mapsrc">Källa: ahusbeach.com</p>
  </section>
```

- [ ] **Step 5: Lägg till elMap-referens och setView-wiring**

I `template.py`, byt:
```javascript
const elHero = document.getElementById("hero");
```
till:
```javascript
const elHero = document.getElementById("hero");
const elMap = document.getElementById("map");
```
Byt sedan i `setView`:
```javascript
  elRoster.hidden = v!=="trupp";
```
till:
```javascript
  elRoster.hidden = v!=="trupp";
  elMap.hidden = v!=="karta";
```

- [ ] **Step 6: Lägg till CSS för inline-vyn**

I `template.py`, hitta den avslutande `</style>`-taggen och lägg in dessa regler **direkt före** den:
```css
#map{padding:12px}
.mapbtn{display:block;width:100%;padding:0;border:0;background:none;cursor:zoom-in;
  border-radius:12px;overflow:hidden;position:relative}
.mapbtn img{display:block;width:100%;height:auto;border-radius:12px}
.maphint{position:absolute;right:10px;bottom:10px;background:#13293dcc;color:#fff;
  font-size:.8rem;padding:4px 8px;border-radius:999px}
.mapsrc{color:#5a6b75;font-size:.75rem;margin:8px 2px 0}
```

- [ ] **Step 7: Kör testet, verifiera PASS**

Run: `python3 -m pytest tests/test_map.py -v`
Expected: PASS (alla fyra).

- [ ] **Step 8: Kör hela sviten**

Run: `python3 -m pytest -q`
Expected: alla PASS.

- [ ] **Step 9: Commit**

```bash
git add template.py tests/test_map.py
git commit -m "feat: Karta-flik och inline-kartvy i mallen"
```

---

## Task 3: Helskärms-overlay med pinch/pan-zoom

**Files:**
- Modify: `template.py` — overlay-markup (efter `#map`-sektionen), CSS (före `</style>`), JS (före service-worker-registreringen)
- Test: `tests/test_map.py`

- [ ] **Step 1: Skriv failing test**

Lägg till i `tests/test_map.py`:
```python
def test_template_has_fullscreen_zoom_overlay():
    assert 'id="mapzoom"' in template.TEMPLATE
    assert 'id="mapzoom-img"' in template.TEMPLATE
    assert 'id="mapzoom-close"' in template.TEMPLATE


def test_template_has_pointer_based_zoom_handler():
    # Zoom-hanteraren använder Pointer Events (inga beroenden) och begränsar skalan.
    assert 'pointerdown' in template.TEMPLATE
    assert 'setPointerCapture' in template.TEMPLATE
    assert 'MIN=1, MAX=6' in template.TEMPLATE
```

- [ ] **Step 2: Kör testet, verifiera FAIL**

Run: `python3 -m pytest tests/test_map.py -k "overlay or pointer" -v`
Expected: FAIL (overlay + zoom-hanterare saknas).

- [ ] **Step 3: Lägg till overlay-markup**

I `template.py`, byt (den avslutande raden på `#map`-sektionen från Task 2):
```html
    <p class="mapsrc">Källa: ahusbeach.com</p>
  </section>
```
till:
```html
    <p class="mapsrc">Källa: ahusbeach.com</p>
  </section>
  <div id="mapzoom" hidden>
    <button id="mapzoom-close" aria-label="Stäng karta">✕</button>
    <img id="mapzoom-img" src="karta.png" alt="Områdeskarta – Åhus Beach Handboll" draggable="false">
  </div>
```

- [ ] **Step 4: Lägg till overlay-CSS**

I `template.py`, direkt före `</style>` (efter inline-reglerna från Task 2), lägg in:
```css
#mapzoom{position:fixed;inset:0;z-index:1000;background:#0b1620;touch-action:none;
  overflow:hidden;display:flex;align-items:center;justify-content:center}
#mapzoom-img{max-width:100%;max-height:100%;user-select:none;-webkit-user-select:none;
  will-change:transform;touch-action:none}
#mapzoom-close{position:fixed;top:calc(env(safe-area-inset-top,0px) + 10px);right:12px;
  z-index:1001;width:44px;height:44px;border:0;border-radius:50%;background:#13293dcc;
  color:#fff;font-size:1.2rem;line-height:1;cursor:pointer}
```

- [ ] **Step 5: Lägg till pinch/pan-JS**

I `template.py`, hitta service-worker-raden:
```javascript
if("serviceWorker" in navigator){ navigator.serviceWorker.register("sw.js").catch(()=>{}); }
```
och lägg in detta block **direkt före** den:
```javascript
// Kartzoom: helskärmsöverlägg med nyp-zoom + panorering (Pointer Events, inga libs).
(function(){
  const openBtn=document.getElementById("mapopen");
  const ov=document.getElementById("mapzoom");
  const img=document.getElementById("mapzoom-img");
  const closeBtn=document.getElementById("mapzoom-close");
  if(!openBtn||!ov||!img||!closeBtn) return;
  let scale=1, tx=0, ty=0, lastDist=0, lastMid=null, lastTap=0;
  const pts=new Map(), MIN=1, MAX=6;
  const apply=()=>{ img.style.transform=`translate(${tx}px,${ty}px) scale(${scale})`; };
  const reset=()=>{ scale=1; tx=0; ty=0; apply(); };
  const open=()=>{ reset(); ov.hidden=false; document.body.style.overflow="hidden"; };
  const close=()=>{ ov.hidden=true; document.body.style.overflow=""; pts.clear(); lastDist=0; };
  const arr=()=>[...pts.values()];
  const dist=()=>{ const a=arr(); return Math.hypot(a[0].x-a[1].x, a[0].y-a[1].y); };
  const mid=()=>{ const a=arr(); return {x:(a[0].x+a[1].x)/2, y:(a[0].y+a[1].y)/2}; };
  openBtn.addEventListener("click", open);
  closeBtn.addEventListener("click", close);
  ov.addEventListener("click", e=>{ if(e.target===ov) close(); });
  document.addEventListener("keydown", e=>{ if(e.key==="Escape" && !ov.hidden) close(); });
  img.addEventListener("pointerdown", e=>{
    img.setPointerCapture(e.pointerId);
    pts.set(e.pointerId, {x:e.clientX, y:e.clientY});
    if(pts.size===2){ lastDist=dist(); lastMid=mid(); }
    else if(pts.size===1){
      const n=Date.now();
      if(n-lastTap<300){ scale>1 ? reset() : (scale=2.5, apply()); }
      lastTap=n;
    }
  });
  img.addEventListener("pointermove", e=>{
    if(!pts.has(e.pointerId)) return;
    const prev=pts.get(e.pointerId), cur={x:e.clientX, y:e.clientY};
    pts.set(e.pointerId, cur);
    if(pts.size===1){ tx+=cur.x-prev.x; ty+=cur.y-prev.y; apply(); }
    else if(pts.size===2){
      const d=dist(), m=mid();
      scale=Math.min(MAX, Math.max(MIN, scale*(d/lastDist)));
      tx+=m.x-lastMid.x; ty+=m.y-lastMid.y;
      lastDist=d; lastMid=m; apply();
    }
  });
  const up=e=>{
    pts.delete(e.pointerId);
    if(pts.size<2) lastDist=0;
    if(scale<=1){ tx=0; ty=0; apply(); }
  };
  img.addEventListener("pointerup", up);
  img.addEventListener("pointercancel", up);
})();
```

- [ ] **Step 6: Kör testet, verifiera PASS**

Run: `python3 -m pytest tests/test_map.py -v`
Expected: PASS (alla).

- [ ] **Step 7: Kör hela sviten**

Run: `python3 -m pytest -q`
Expected: alla PASS.

- [ ] **Step 8: Commit**

```bash
git add template.py tests/test_map.py
git commit -m "feat: helskärms-kartzoom (nyp/panorera) i mallen"
```

---

## Task 4: Bygg lokalt och verifiera

- [ ] **Step 1: Bygg U15-appen (staging) och en live-app lokalt**

Run:
```bash
cd ~/dev/ahk-beach
python3 build_apps.py >/dev/null && echo "byggt"
ls dist-u15/karta.png u14/karta.png u10/karta.png 2>&1
grep -c 'data-view="karta"' dist-u15/index.html
```
Expected: `karta.png` finns i `dist-u15/`, `u14/`, `u10/`; grep ger `1`.

- [ ] **Step 2: Städa spårade regenererade filer (byggets biprodukter)**

Run:
```bash
git checkout -- . ; rm -rf dist-u15
git status --short
```
Expected: rent arbetsträd (bara de committade käll-/testfilerna kvar i historiken). `karta.png` i roten är redan committad i Task 1 och ska INTE försvinna — bekräfta att den finns kvar: `ls karta.png`.

- [ ] **Step 3: Manuell webbläsarverifiering**

Öppna en byggd app i webbläsare (t.ex. via `/run` eller `python3 -m http.server` i en byggd app-katalog) och verifiera på både desktop och mobil:
- Karta-fliken syns i alla appar (även de utan tabeller/trupp).
- Fliken visar kartan i full bredd med hinten "Tryck för helskärm".
- Tryck öppnar helskärm; nyp zoomar, ett finger panorerar, dubbeltryck återställer, ✕/Esc/tryck-utanför stänger.
- Ingen konsol-error.

Detta steg är manuellt (zoom-gesten kan inte enhetstestas i det Python-baserade bygget).

---

## Noteringar

- **Offline:** service workern (nätverk-först, cache-vid-hämtning) cachar `karta.png` vid första visning online → tillgänglig offline därefter. Ingen precache behövs (konsekvent med appens övriga cachning).
- **Zoom-modell:** skalning sker kring bildens mitt (transform-origin center) + fri panorering. Enkelt och robust; inte fokuspunkts-exakt nyp, men fullt tillräckligt för en karta och helt beroendefritt.
- **U15 följer med automatiskt:** samma mall/bygge → `dist-u15/` får kartan och publiceras till gamla URL:en av den befintliga deploy-kedjan. Se [[u15-shared-pipeline]].
