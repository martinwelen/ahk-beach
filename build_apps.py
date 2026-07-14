# build_apps.py
# -*- coding: utf-8 -*-
"""Bygger en installerbar PWA per åldersgrupp ur data.json/standings.json."""

import os
import json
import shutil

import config
import template
import roster_data
import bana_coords

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(ROOT, "data.json")
STANDINGS_JSON = os.path.join(ROOT, "standings.json")
# (U15 byggs nu också – till config.U15_DIST, publiceras till det externa repot.)


def app_manifest(group):
    m = dict(template.MANIFEST_BASE)
    m["name"] = f"AHK {group['label']}"
    m["short_name"] = f"AHK {group['label']}"
    m["description"] = f"Matchschema för Alingsås HK {group['label']} på Åhus Beach Handboll"
    m["start_url"] = "."
    m["scope"] = "./"
    return m


def service_worker_js(age_slug):
    legacy = ["ahus-schema-v1"] if age_slug == config.U15_SLUG else []
    return (template.SERVICE_WORKER_TPL
            .replace("__CACHE__", f"ahk-{age_slug}-v1")
            .replace("__LEGACY__", json.dumps(legacy)))


_GENDER_LABEL = {"P": "Pojkar", "F": "Flickor"}


def _classes(group):
    """Könsklasser som finns i gruppen → [{cls, label}], P före F."""
    age = group["age"]
    seen = []
    for t in group["teams"]:
        if t["gender"] not in seen:
            seen.append(t["gender"])
    seen.sort(key=lambda g: {"P": 0, "F": 1}.get(g, 9))
    return [{"cls": f"{g}{age}", "label": f"{_GENDER_LABEL.get(g, g)} {age}"} for g in seen]


def _js_matches(group):
    age = group["age"]
    has_res = group["profile"]["has_results"]
    name_by_slug = {t["slug"]: t["team_name"] for t in group["teams"]}
    out = []
    for m in group["matches"]:
        out.append({
            "ms": m["start_ms"], "t": m["tid"], "bana": m["bana"],
            "lag": name_by_slug.get(m["slug"], m["slug"]), "slug": m["slug"],
            "klass": f"{m['gender']}{age}",
            "grp": m["grupp"], "home": m["hemma"], "away": m["borta"],
            "hb": m["hb"], "day": m["day_label"], "color": m["color"].lstrip("#"),
            "res": m.get("result") if has_res else None,
            "id": m.get("id"),
            "video": m.get("video"),
            "runda": m.get("runda"),
        })
    out.sort(key=lambda x: x["ms"])
    return out


def _teams_js(group):
    age = group["age"]
    # `id` = cupmanagers numeriska lag-id (standings joinar på det); `slug` = filtervärde.
    return [{"lag": t["team_name"], "slug": t["slug"], "klass": f"{t['gender']}{age}",
             "id": t["id"], "color": t["color"].lstrip("#")} for t in group["teams"]]


def _rosters_js(group):
    """Trupper för gruppens lag → {slug: [spelare]}. Tomt om ingen trupp finns."""
    slugs = {t["slug"] for t in group["teams"]}
    return {s: p for s, p in roster_data.rosters.items() if s in slugs}


def _dates(group):
    """Distinkta speldagar i tidsordning, t.ex. 'Måndag 13 juli &amp; Tisdag 14 juli'."""
    seen = []
    for m in group["matches"]:
        d = m["day_label"]
        if d not in seen:
            seen.append(d)
    return " &amp; ".join(seen) if seen else "&nbsp;"


def render_app(group, standings, base, updated):
    """Renderar en åldersgrupps index.html. `standings` = by_age[age_slug] eller None."""
    st = standings if (standings and group["profile"]["has_tables"]) else None
    return (template.TEMPLATE
            .replace("__DATA__", json.dumps(_js_matches(group), ensure_ascii=False))
            .replace("__TEAMS__", json.dumps(_teams_js(group), ensure_ascii=False))
            .replace("__CLASSES__", json.dumps(_classes(group), ensure_ascii=False))
            .replace("__DUR_MIN__", str(group["profile"]["duration_min"]))
            .replace("__API_HOST__", config.API_HOST)
            .replace("__TOURNAMENT_ID__", config.TOURNAMENT_ID)
            .replace("__BANA_XY__", json.dumps(bana_coords.bana_fractions()))
            .replace("__KLUBBTALT__", json.dumps(bana_coords.klubbtalt_fraction()))
            .replace("__STANDINGS__", json.dumps(st, ensure_ascii=False))
            .replace("__ROSTERS__", json.dumps(_rosters_js(group), ensure_ascii=False))
            .replace("__CAL_ITEMS__", "")
            .replace("__APPLABEL__", group["label"])
            .replace("__DATES__", _dates(group))
            .replace("__TEAMCOUNT__", str(len(group["teams"])))
            .replace("__BASE__", base)
            .replace("__UPDATED__", updated))


_ICONS = ("icon-192.png", "icon-512.png", "icon-512-maskable.png",
          "icon-180.png", "favicon-32.png")
# Statiska filer som kopieras oförändrade till varje app-katalog.
_ASSETS = _ICONS + ("karta.png", "Alingsas_HK_logo.svg")


def _load(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def main():
    data = _load(DATA_JSON, {"groups": {}, "meta": {}})
    standings = _load(STANDINGS_JSON, {"by_age": {}}).get("by_age", {})
    updated = data.get("meta", {}).get("generated", "")
    built = 0
    for age_slug, group in data.get("groups", {}).items():
        if age_slug == config.U15_SLUG:
            out_dir = os.path.join(ROOT, config.U15_DIST)
            base = config.U15_PAGES_BASE
        else:
            out_dir = os.path.join(ROOT, age_slug)
            base = f"{config.PAGES_BASE}/{age_slug}"
        os.makedirs(out_dir, exist_ok=True)
        html = render_app(group, standings.get(age_slug), base, updated)
        with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)
        with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(app_manifest(group), f, ensure_ascii=False, indent=2)
        with open(os.path.join(out_dir, "sw.js"), "w", encoding="utf-8") as f:
            f.write(service_worker_js(age_slug))
        for asset in _ASSETS:
            src = os.path.join(ROOT, asset)
            if os.path.exists(src):
                shutil.copy(src, os.path.join(out_dir, asset))
        sg = standings.get(age_slug)
        st_group = sg if (sg and group["profile"]["has_tables"]) else None
        sched = {"matches": _js_matches(group), "standings": st_group, "updated": updated}
        with open(os.path.join(out_dir, "sched.json"), "w", encoding="utf-8") as f:
            json.dump(sched, f, ensure_ascii=False)
        built += 1
    print(f"Byggde {built} appar")
    return built


if __name__ == "__main__":
    main()
