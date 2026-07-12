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
