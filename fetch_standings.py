# fetch_standings.py
# -*- coding: utf-8 -*-
"""Grupptabeller + A/B/C-slutspelsträd per åldersgrupp (klubbkodsdrivet).

Speglar API:ts tabellordning (ingen egen tie-break). Mini hoppas över
(inga tabeller). Mirror av proven logik i alingsas-ahus-beach-2026."""

import re

import api
import rules


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
