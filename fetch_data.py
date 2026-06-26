# fetch_data.py
# -*- coding: utf-8 -*-
"""Klubbkodsdriven datahämtning → data.json (lag + matcher per åldersgrupp)."""

import hashlib
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone, timedelta

import api
import config
import derive
import rules


def build_team_registry(store):
    """Alla klubbens lag ur en entitets-store, med härledd metadata + färg.

    Returnerar en lista av dict:
      {id, gender, age, rule, suffix, team_name, age_slug, slug, color}
    """
    teams = []
    for e in store.values():
        if e.get("__typename") != "Team":
            continue
        if api.ref_id(e.get("club")) != config.CLUB_ID:
            continue
        nm = e.get("name") or {}
        p = derive.parse_category(nm.get("categoryName", ""))
        teams.append({
            "id": e["id"],
            "gender": p["gender"], "age": p["age"], "rule": p["rule"],
            "suffix": p["suffix"],
            "team_name": nm.get("clubName", ""),
            "age_slug": f"u{p['age']}",
            "slug": derive.slugify(f"u{p['age']}-{p['gender']}-{p['suffix'] or 'lag'}"),
        })

    # Färg tilldelas per åldersgrupp (regeln behöver hela gruppen).
    by_age = defaultdict(list)
    for t in teams:
        by_age[t["age_slug"]].append(t)
    for group in by_age.values():
        colors = derive.derive_group_colors(group)
        for t in group:
            t["color"] = colors[t["id"]]

    teams.sort(key=lambda t: (t["age"], t["gender"], t["slug"]))
    return teams


_CEST = timezone(timedelta(hours=config.UTC_OFFSET_HOURS))
_SV_DAYS = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
_SV_MONTHS = ["", "januari", "februari", "mars", "april", "maj", "juni",
              "juli", "augusti", "september", "oktober", "november", "december"]


def _bana_num(field):
    m = re.search(r"(\d+)", field or "")
    return int(m.group(1)) if m else (field or "")


def _extract_result(res):
    if not res or not res.get("finished"):
        return None
    hg, ag = res.get("homeGoals"), res.get("awayGoals")
    if hg is None or ag is None:
        return None
    return {"hg": hg, "ag": ag}


def normalize_match(e, store, reg_by_id):
    """En Match-entitet → normaliserad dict, knuten till klubbens lag.

    Returnerar None om matchen inte rör något av klubbens lag.
    """
    home_a = api.store_get(store, e.get("home", {}))
    away_a = api.store_get(store, e.get("away", {}))
    hid = api.ref_id(home_a.get("team")) if home_a else None
    aid = api.ref_id(away_a.get("team")) if away_a else None
    team = reg_by_id.get(hid) or reg_by_id.get(aid)
    if not team:
        return None

    hb = "Hemma" if hid in reg_by_id else "Borta"
    hemma = api.name_of(home_a)
    borta = api.name_of(away_a)
    div = api.store_get(store, e.get("division", {}))
    grupp = api.name_of(div)
    bana = _bana_num(api.store_get(store, e.get("arena", {})).get("completeName", ""))
    start_ms = e["start"]
    dt = datetime.fromtimestamp(start_ms / 1000, _CEST)
    result = _extract_result(api.store_get(store, e.get("result", {})))

    return {
        "age_slug": team["age_slug"], "slug": team["slug"],
        "gender": team["gender"], "rule": team["rule"], "color": team["color"],
        "datum": f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}",
        "dag": _SV_DAYS[dt.weekday()],
        "tid": f"{dt.hour:02d}:{dt.minute:02d}",
        "bana": bana,
        "hemma": hemma, "borta": borta,
        "grupp": grupp,
        "mots": borta if hb == "Hemma" else hemma,
        "hb": hb, "result": result,
        "start_ms": start_ms,
        "start_iso": dt.isoformat(timespec="minutes"),
        "day_label": f"{_SV_DAYS[dt.weekday()]} {dt.day} {_SV_MONTHS[dt.month]}",
    }


def _court_sort_key(m):
    """Banor sorteras numeriskt; ev. textfallback (bana utan siffra) sist.

    _bana_num ger normalt en int, men returnerar råsträngen om arenan saknar
    siffra. Vi blandar därför aldrig int och str i samma sorteringsnyckel.
    """
    b = m["bana"]
    return (0, b) if isinstance(b, int) else (1, str(b))


def bucket_by_age_group(registry, match_entities, store):
    """Bygger {age_slug: {age,label,rule,profile,teams,matches}} ur lag + matcher."""
    reg_by_id = {t["id"]: t for t in registry}
    groups = {}
    for t in registry:
        a = t["age_slug"]
        if a not in groups:
            groups[a] = {"age": t["age"], "label": f"U{t['age']}",
                         "rule": t["rule"], "profile": rules.rule_profile(t["rule"]),
                         "teams": [], "matches": []}
        groups[a]["teams"].append(t)

    for e in match_entities:
        nm = normalize_match(e, store, reg_by_id)
        if nm and nm["age_slug"] in groups:
            groups[nm["age_slug"]]["matches"].append(nm)

    for g in groups.values():
        g["matches"].sort(key=lambda m: (m["start_ms"], _court_sort_key(m)))
    return groups


def _hash_groups(groups):
    key = []
    for a in sorted(groups):
        g = groups[a]
        key.append((a, g["rule"], [t["id"] for t in g["teams"]],
                    [(m["slug"], m["start_ms"], str(m["bana"]),
                      m["hemma"], m["borta"], m["grupp"], m.get("result"))
                     for m in g["matches"]]))
    return hashlib.sha256(json.dumps(key, ensure_ascii=False,
                                     sort_keys=True).encode()).hexdigest()


def assemble(groups, generated, seq):
    return {
        "meta": {
            "source": f"cupmanager API (klubbkod {config.CLUB_ID}, "
                      f"tournamentId {config.TOURNAMENT_ID})",
            "club_id": config.CLUB_ID,
            "generated": generated, "seq": seq,
            "data_hash": _hash_groups(groups),
        },
        "groups": groups,
    }


def write_if_changed(groups, path, generated, seq):
    """Skriver data.json bara om innehållet ändrats. Returnerar True om skrivet."""
    new_hash = _hash_groups(groups)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                old = json.load(f)
            if old.get("meta", {}).get("data_hash") == new_hash:
                return False
        except Exception:
            pass
    doc = assemble(groups, generated, seq)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    return True


import sys
from datetime import datetime as _dt, timezone as _tz

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(ROOT, "data.json")


def main():
    try:
        store = api.fetch_store()
    except Exception as e:
        print("FEL vid hämtning:", e, "- lämnar data.json orörd")
        return 0
    registry = build_team_registry(store)
    if not registry:
        print("0 lag för klubbkoden - lämnar data.json orörd")
        return 0
    match_entities = [e for e in store.values() if e.get("__typename") == "Match"]
    groups = bucket_by_age_group(registry, match_entities, store)
    now = _dt.now(_tz.utc)
    wrote = write_if_changed(groups, DATA_JSON,
                             generated=now.isoformat(timespec="seconds"),
                             seq=int(now.timestamp()))
    n_t = sum(len(g["teams"]) for g in groups.values())
    n_m = sum(len(g["matches"]) for g in groups.values())
    print(f"{'Skrev' if wrote else 'Ingen ändring;'} {len(groups)} "
          f"åldersgrupper, {n_t} lag, {n_m} matcher"
          + ("" if wrote else " (skrev inte om)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
