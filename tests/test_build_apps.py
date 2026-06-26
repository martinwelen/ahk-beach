# -*- coding: utf-8 -*-
import build_apps


def _group(age_slug="u14", label="U14"):
    return {"age": 14, "label": label, "rule": "Classic",
            "profile": {"duration_min": 11, "has_results": True,
                        "has_tables": True, "has_playoffs": True},
            "teams": [{"slug": f"{age_slug}-p-bla", "team_name": "Alingsås HK Blå",
                       "color": "#1f5fbf", "gender": "P"}],
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
    g["teams"] = [{"slug": "u14-p-bla", "team_name": "A", "color": "#1f5fbf", "gender": "P"},
                  {"slug": "u14-f-vit", "team_name": "B", "color": "#c9c2b4", "gender": "F"}]
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
