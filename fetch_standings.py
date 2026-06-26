# fetch_standings.py
# -*- coding: utf-8 -*-
"""Grupptabeller + A/B/C-slutspelsträd per åldersgrupp (klubbkodsdrivet).

Speglar API:ts tabellordning (ingen egen tie-break). Mini hoppas över
(inga tabeller). Mirror av proven logik i alingsas-ahus-beach-2026."""

import os
import re
import sys
import json
import hashlib
from datetime import datetime, timezone

import api
import config
import rules
import fetch_data


def winner_side(result):
    if not result or not result.get("finished"):
        return None
    hg, ag = result.get("homeGoals"), result.get("awayGoals")
    if hg is None or ag is None or hg == ag:
        return None
    return "home" if hg > ag else "away"


def _stage_id(href):
    m = re.search(r"stageId:(\d+)", href or "")
    return int(m.group(1)) if m else None


def table_row(row, club_team_ids, tier_by_stage):
    tid = api.ref_id(row.get("team"))
    gf = row.get("goalsWon", 0) or 0
    ga = row.get("goalsLost", 0) or 0
    sid = _stage_id((row.get("targetStage") or {}).get("href", ""))
    return {
        "name": api.name_of(row), "team_id": tid,
        "is_alingsas": tid in club_team_ids,
        "played": row.get("played", 0) or 0,
        "won": row.get("won", 0) or 0, "tied": row.get("tied", 0) or 0,
        "lost": row.get("lost", 0) or 0,
        "goals_for": gf, "goals_against": ga, "diff": gf - ga,
        "points": row.get("points", 0) or 0,
        "tier": tier_by_stage.get(sid),
    }


def bucket_groups(groups):
    """Lista av grupp-dict (med age_slug + rule) → {age_slug: [grupper]}.

    Hoppar över regeltyper utan tabeller (Mini)."""
    out = {}
    for g in groups:
        if not rules.rule_profile(g["rule"])["has_tables"]:
            continue
        out.setdefault(g["age_slug"], []).append(g)
    return out


def _bana_num(field):
    import re as _re
    m = _re.search(r"(\d+)", field or "")
    return int(m.group(1)) if m else (field or "")


def bracket_match(m, store, club_ids):
    """Slutspelsmatch (Match-entitet + store) → vår bracket-modell."""
    home = api.store_get(store, m.get("home")) or {}
    away = api.store_get(store, m.get("away")) or {}
    arena = api.store_get(store, m.get("arena")) or {}
    rnd = api.store_get(store, m.get("round")) or {}
    result = api.store_get(store, m.get("result")) or {}
    side = winner_side(result)

    def actor(a):
        tid = api.ref_id(a.get("team")) if isinstance(a.get("team"), dict) else None
        goals = None
        if result.get("finished"):
            goals = result.get("homeGoals") if a is home else result.get("awayGoals")
        return {"label": api.name_of(a), "team_id": tid,
                "is_alingsas": tid in club_ids if tid else False, "goals": goals}

    return {"id": m.get("id"), "start": m.get("start"),
            "bana": _bana_num(arena.get("fieldName", "")),
            "round": api.name_of(rnd), "home": actor(home), "away": actor(away),
            "winner": side}


def group_rounds(matches):
    """Normaliserade matcher → ronder, ordnade efter rondens första start."""
    by_round = {}
    for m in matches:
        by_round.setdefault(m["round"], []).append(m)
    rounds = []
    for name, ms in by_round.items():
        ms.sort(key=lambda x: (x.get("start") or 0, x.get("id") or 0))
        rounds.append({"name": name, "matches": ms, "_first": ms[0].get("start") or 0})
    rounds.sort(key=lambda r: r["_first"])
    for r in rounds:
        del r["_first"]
    return rounds


def _category_id(division_entity):
    import re as _re
    cat = division_entity.get("category") if isinstance(division_entity, dict) else None
    href = cat.get("href", "") if isinstance(cat, dict) else ""
    m = _re.search(r"categoryId:(\d+)", href)
    return m.group(1) if m else None


def discover_divisions(store, reg_by_id):
    """{division_id: {age_slug, rule, name, category}} för klubbens grupper."""
    out = {}
    for e in store.values():
        if e.get("__typename") != "Match":
            continue
        home = api.store_get(store, e.get("home", {}))
        away = api.store_get(store, e.get("away", {}))
        hid, aid = api.ref_id(home.get("team")), api.ref_id(away.get("team"))
        team = reg_by_id.get(hid) or reg_by_id.get(aid)
        if not team:
            continue
        did = api.ref_id(e.get("division"))
        if did is None:
            continue
        dent = api.store_get(store, e.get("division", {}))
        out[did] = {"age_slug": team["age_slug"], "rule": team["rule"],
                    "name": api.name_of(dent), "category": _category_id(dent)}
    return out


ROOT = os.path.dirname(os.path.abspath(__file__))
STANDINGS_JSON = os.path.join(ROOT, "standings.json")


def _resolve(query):
    resp = api.call(query).get("responses", {})
    if query in resp and isinstance(resp[query], dict):
        return resp[query].get("entity")
    for v in resp.values():
        if isinstance(v, dict) and "entity" in v:
            return v["entity"]
    return None


def _store(query):
    resp = api.call(query).get("responses", {})
    return {k: v["entity"] for k, v in resp.items()
            if isinstance(v, dict) and isinstance(v.get("entity"), dict)}


def category_playoffs(cat_id, sample_division_id):
    """[(stage_id, playoff_division_id, tier_namn)] för en kategori."""
    table = _resolve(f"Division({{id:{sample_division_id}}})$table") or {}
    stage_ids = []
    for r in table.get("rows", []):
        sid = _stage_id((r.get("targetStage") or {}).get("href", ""))
        if sid and sid not in stage_ids:
            stage_ids.append(sid)
    out = []
    for sid in stage_ids:
        ent = _resolve(f"Stage({{categoryId:{cat_id},stageId:{sid},"
                       f"tournamentId:{config.TOURNAMENT_ID}}})$divisions")
        if isinstance(ent, list):
            for dref in ent:
                pid = api.ref_id(dref)
                pe = _resolve(f"Division({{id:{pid}}})")
                out.append((sid, pid, api.name_of(pe)))
    return out


def build():
    store = api.fetch_store()
    registry = fetch_data.build_team_registry(store)
    reg_by_id = {t["id"]: t for t in registry}
    club_ids = set(reg_by_id)
    divisions = discover_divisions(store, reg_by_id)

    cat_play, cat_age = {}, {}
    for did, info in divisions.items():
        if not rules.rule_profile(info["rule"])["has_tables"]:
            continue
        cat = info["category"]
        cat_age.setdefault(cat, info["age_slug"])
        if cat not in cat_play:
            cat_play[cat] = category_playoffs(cat, did)

    by_age = {}
    for did, info in divisions.items():
        if not rules.rule_profile(info["rule"])["has_tables"]:
            continue
        tier_by_stage = {sid: name for (sid, _p, name) in cat_play.get(info["category"], [])}
        table = _resolve(f"Division({{id:{did}}})$table") or {}
        rows = [table_row(r, club_ids, tier_by_stage) for r in table.get("rows", [])]
        for i, r in enumerate(rows, 1):
            r["pos"] = i
        bucket = by_age.setdefault(info["age_slug"], {"groups": [], "playoffs": []})
        bucket["groups"].append({"name": info["name"], "division_id": did, "rows": rows})

    for cat, plist in cat_play.items():
        age = cat_age.get(cat)
        tiers = []
        for (_sid, pid, name) in plist:
            q = (f"Division({{id:{pid}}}){{matches:[{{... on Match:"
                 f"{{start:{{}},home:{{}},away:{{}},arena:{{}},round:{{}},result:{{}}}}}}]}}")
            st = _store(q)
            ms = [bracket_match(e, st, club_ids)
                  for e in st.values() if e.get("__typename") == "Match"]
            tiers.append({"tier": name, "division_id": pid, "rounds": group_rounds(ms)})
        if age:
            by_age.setdefault(age, {"groups": [], "playoffs": []})["playoffs"].extend(tiers)

    for b in by_age.values():
        b["groups"].sort(key=lambda g: g["name"])
    return by_age


def _hash(by_age):
    return hashlib.sha256(json.dumps(by_age, ensure_ascii=False,
                                     sort_keys=True).encode()).hexdigest()


def main():
    try:
        by_age = build()
    except Exception as e:
        print("FEL vid hämtning:", e, "- lämnar standings.json orörd")
        return 0
    if not by_age:
        print("0 grupper - lämnar standings.json orörd")
        return 0
    h = _hash(by_age)
    if os.path.exists(STANDINGS_JSON):
        try:
            with open(STANDINGS_JSON, encoding="utf-8") as f:
                if json.load(f).get("meta", {}).get("data_hash") == h:
                    print(f"Ingen ändring ({len(by_age)} åldersgrupper). Skriver inte om.")
                    return 0
        except Exception:
            pass
    now = datetime.now(timezone.utc)
    doc = {"meta": {"source": "cupmanager API (Division$table + Playoff)",
                    "generated": now.isoformat(timespec="seconds"),
                    "seq": int(now.timestamp()), "data_hash": h},
           "by_age": by_age}
    with open(STANDINGS_JSON, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"Skrev standings.json för {len(by_age)} åldersgrupper")
    return 0


if __name__ == "__main__":
    sys.exit(main())
