# -*- coding: utf-8 -*-
import build_hub


def test_hub_lists_groups_and_links_u15_to_live_repo():
    data = {"groups": {
        "u14": {"label": "U14", "teams": [1, 2], "matches": [1],
                "rule": "Classic", "profile": {}},
        "u15": {"label": "U15", "teams": [1], "matches": [1],
                "rule": "Classic", "profile": {}},
    }}
    html = build_hub.render_hub(data)
    assert "U14" in html and 'href="u14/"' in html
    assert build_hub.U15_LIVE_URL in html        # U15 → live-repots URL
    assert 'href="u15/"' not in html             # ingen lokal u15-länk


def test_hub_orders_groups_by_age():
    data = {"groups": {
        "u8": {"label": "U8", "teams": [1], "matches": [1], "rule": "Mini", "profile": {}},
        "u14": {"label": "U14", "teams": [1], "matches": [1], "rule": "Classic", "profile": {}},
    }}
    html = build_hub.render_hub(data)
    assert html.index("U8") < html.index("U14")


def test_hub_includes_analytics_beacon():
    html = build_hub.render_hub({"groups": {}})
    assert "static.cloudflareinsights.com/beacon.min.js" in html
    assert '"token": "0fbaddb77cfe4155af4e4bdb370de308"' in html
