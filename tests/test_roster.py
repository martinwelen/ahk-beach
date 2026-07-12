# -*- coding: utf-8 -*-
import build_apps


def _group(age_slug="u15", age=15):
    return {"age": age, "label": f"U{age}", "rule": "Classic",
            "profile": {"duration_min": 11, "has_results": True,
                        "has_tables": True, "has_playoffs": True},
            "teams": [{"id": 1, "slug": f"{age_slug}-p-bla", "team_name": "Blå",
                       "color": "#1f5fbf", "gender": "P"}],
            "matches": []}


def test_rosters_js_returns_players_for_group_teams():
    r = build_apps._rosters_js(_group())
    assert "u15-p-bla" in r
    assert {"namn": "Oskar Viklund", "pos": "UT"} in r["u15-p-bla"]


def test_rosters_js_empty_for_group_without_roster_data():
    r = build_apps._rosters_js(_group("u14", 14))
    assert r == {}


def test_render_app_embeds_rosters_not_empty_object_for_u15():
    import json
    html = build_apps.render_app(_group(), standings=None, base="b", updated="u")
    rosters = html.split("const ROSTERS = ", 1)[1].split(";\n", 1)[0]
    assert "Oskar Viklund" in rosters
    assert json.loads(rosters)["u15-p-bla"]


def test_render_app_keeps_empty_rosters_for_live_groups():
    html = build_apps.render_app(_group("u14", 14), standings=None, base="b", updated="u")
    rosters = html.split("const ROSTERS = ", 1)[1].split(";\n", 1)[0]
    assert rosters == "{}"
