# fetch_data.py
# -*- coding: utf-8 -*-
"""Klubbkodsdriven datahämtning → data.json (lag + matcher per åldersgrupp)."""

from collections import defaultdict

import api
import config
import derive


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
