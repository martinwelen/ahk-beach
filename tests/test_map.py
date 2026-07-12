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


def test_template_has_fullscreen_zoom_overlay():
    assert 'id="mapzoom"' in template.TEMPLATE
    assert 'id="mapzoom-img"' in template.TEMPLATE
    assert 'id="mapzoom-close"' in template.TEMPLATE


def test_mapzoom_overlay_is_hidden_by_default():
    # Regression: #mapzoom{display:flex} skulle överköra [hidden] → overlay syns
    # vid laddning och täcker hela appen. display:flex måste gälla :not([hidden]).
    assert '#mapzoom:not([hidden]){' in template.TEMPLATE
    assert '#mapzoom{' not in template.TEMPLATE


def test_viewport_disables_native_page_zoom():
    # Root cause (mobil): webbläsarens sid-zoom kapade nyp-gesten → kartans egen
    # zoom fungerade inte. Sid-zoom är avstängd så kartzoomen äger nypet.
    assert 'user-scalable=no' in template.TEMPLATE
    assert 'maximum-scale=1' in template.TEMPLATE


def test_tab_bar_scrolls_horizontally():
    # Med Karta-fliken blir flikraden bredare än en mobil; utan sid-zoom måste den
    # kunna svepas i sidled så alla flikar är nåbara (som .filters redan är).
    import re
    m = re.search(r'\.tabs\{[^}]*\}', template.TEMPLATE)
    assert m and 'overflow-x:auto' in m.group(0)


def test_template_has_pointer_based_zoom_handler():
    assert 'pointerdown' in template.TEMPLATE
    assert 'setPointerCapture' in template.TEMPLATE
    assert 'MIN=1, MAX=6' in template.TEMPLATE
    assert 'clamp' in template.TEMPLATE               # pan-clamp finns
    assert 'justLifted' in template.TEMPLATE          # ingen pan-hopp vid 2→1
