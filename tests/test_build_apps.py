# -*- coding: utf-8 -*-
import build_apps


def _group(age_slug="u14", label="U14"):
    return {"age": 14, "label": label, "rule": "Classic",
            "profile": {"duration_min": 11, "has_results": True,
                        "has_tables": True, "has_playoffs": True},
            "teams": [{"id": 74328265, "slug": f"{age_slug}-p-bla",
                       "team_name": "Alingsås HK Blå", "color": "#1f5fbf", "gender": "P"}],
            "matches": []}


def test_app_manifest_has_unique_identity():
    m = build_apps.app_manifest(_group())
    assert m["name"] == "AHK U14"
    assert m["short_name"] == "AHK U14"
    assert m["start_url"] == "." and m["scope"] == "./"
    assert any(i["src"] == "icon-192.png" for i in m["icons"])


def test_service_worker_has_unique_cache_name():
    sw = build_apps.service_worker_js("u14")
    assert 'const C = "ahk-u14-v1";' in sw
    assert "__CACHE__" not in sw


import json


def test_render_app_replaces_placeholders_and_labels():
    html = build_apps.render_app(_group(), standings=None,
                                 base="https://x/ahk-beach/u14", updated="nyss")
    for ph in ("__DATA__", "__STANDINGS__", "__APPLABEL__", "__CLASSES__"):
        assert ph not in html
    assert "U14" in html


def test_render_app_builds_gender_classes_from_teams():
    g = _group()
    g["teams"] = [{"id": 1, "slug": "u14-p-bla", "team_name": "A", "color": "#1f5fbf", "gender": "P"},
                  {"id": 2, "slug": "u14-f-vit", "team_name": "B", "color": "#c9c2b4", "gender": "F"}]
    html = build_apps.render_app(g, standings=None, base="b", updated="u")
    classes = json.loads(html.split("const CLASSES = ", 1)[1].split(";\n", 1)[0])
    assert {"cls": "P14", "label": "Pojkar 14"} in classes
    assert {"cls": "F14", "label": "Flickor 14"} in classes


def test_render_app_strips_hash_from_colors():
    g = _group()
    g["matches"] = [{"start_ms": 1, "tid": "10:00", "bana": 1, "slug": "u14-p-bla",
                     "grupp": "G1", "hemma": "A", "borta": "B", "hb": "Hemma",
                     "day_label": "x", "color": "#1f5fbf", "gender": "P", "result": None}]
    html = build_apps.render_app(g, standings=None, base="b", updated="u")
    matches = html.split("const MATCHES = ", 1)[1].split(";\n", 1)[0]
    assert '"color": "1f5fbf"' in matches or '"color":"1f5fbf"' in matches
    assert "##" not in html


def test_render_app_strips_results_when_has_results_false():
    g = _group()
    g["rule"] = "Mini"
    g["profile"]["has_results"] = False
    g["matches"] = [{"start_ms": 1, "tid": "10:00", "bana": 1, "slug": "u14-p-bla",
                     "grupp": "G1", "hemma": "A", "borta": "B", "hb": "Hemma",
                     "day_label": "x", "color": "#1f5fbf", "gender": "P",
                     "result": {"hg": 5, "ag": 3}}]
    html = build_apps.render_app(g, standings=None, base="b", updated="u")
    matches = html.split("const MATCHES = ", 1)[1].split(";\n", 1)[0]
    assert '"res": null' in matches or '"res":null' in matches


def test_build_apps_writes_each_group_dir(tmp_path, monkeypatch):
    data = {"meta": {"generated": "2026-06-26T00:00:00Z"},
            "groups": {"u14": _group("u14", "U14"), "u15": _group("u15", "U15")}}
    (tmp_path / "data.json").write_text(json.dumps(data), encoding="utf-8")
    # skapa ikon-filer som main() försöker kopiera
    for ic in ("icon-192.png", "icon-512.png", "icon-512-maskable.png",
               "icon-180.png", "favicon-32.png"):
        (tmp_path / ic).write_bytes(b"x")
    monkeypatch.setattr(build_apps, "ROOT", str(tmp_path))
    monkeypatch.setattr(build_apps, "DATA_JSON", str(tmp_path / "data.json"))
    monkeypatch.setattr(build_apps, "STANDINGS_JSON", str(tmp_path / "nope.json"))
    n = build_apps.main()
    assert (tmp_path / "u14" / "index.html").exists()
    assert (tmp_path / "u14" / "manifest.json").exists()
    assert (tmp_path / "u14" / "sw.js").exists()
    assert (tmp_path / "u14" / "icon-192.png").exists()
    assert not (tmp_path / "u15").exists()       # U15 skippas
    assert n == 1


def test_teams_js_uses_numeric_id_for_standings_join():
    # C1-regression: TEAMS.id måste vara cupmanagers numeriska lag-id (standings
    # joinar r.team_id===team.id), INTE slug.
    g = _group()
    g["teams"] = [{"id": 999001, "slug": "u14-p-bla", "team_name": "Alingsås HK Blå",
                   "color": "#1f5fbf", "gender": "P"}]
    teams = build_apps._teams_js(g)
    assert teams[0]["id"] == 999001
    assert teams[0]["slug"] == "u14-p-bla"


def test_js_matches_uses_team_name_not_slug_for_lag():
    # I1-regression: schemat ska visa lagnamn, inte slug.
    g = _group()
    g["matches"] = [{"start_ms": 1, "tid": "10:00", "bana": 1, "slug": "u14-p-bla",
                     "grupp": "G1", "hemma": "A", "borta": "B", "hb": "Hemma",
                     "day_label": "Måndag 13 juli", "color": "#1f5fbf",
                     "gender": "P", "result": None}]
    m = build_apps._js_matches(g)[0]
    assert m["lag"] == "Alingsås HK Blå"


def test_render_app_fills_dates_and_teamcount():
    # I2-regression: header får inte hårdkoda "6 lag" / U15-datum.
    g = _group()
    g["matches"] = [{"start_ms": 1, "tid": "10:00", "bana": 1, "slug": "u14-p-bla",
                     "grupp": "G1", "hemma": "A", "borta": "B", "hb": "Hemma",
                     "day_label": "Måndag 13 juli", "color": "#1f5fbf",
                     "gender": "P", "result": None}]
    html = build_apps.render_app(g, standings=None, base="b", updated="u")
    assert "__DATES__" not in html and "__TEAMCOUNT__" not in html
    assert "Måndag 13 juli" in html
    assert "6 lag" not in html and "17 juli" not in html


def test_render_app_starts_with_doctype_no_leading_backslash():
    # Regression: mallen fick en literal '\' först → syntes uppe till vänster.
    html = build_apps.render_app(_group(), standings=None, base="b", updated="u")
    assert html.startswith("<!doctype html>")
