# build_hub.py
# -*- coding: utf-8 -*-
"""Hubbsida på roten: listar alla åldersgrupps-appar. U15 länkar till live-repot."""

import os
import json

import config

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(ROOT, "data.json")
U15_LIVE_URL = "https://martinwelen.github.io/alingsas-ahus-beach-2026/"

_PAGE = """<!doctype html><html lang="sv"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AHK Åhus Beach – välj lag</title>
<style>body{{font-family:system-ui,sans-serif;background:#f4ecdb;color:#13293d;margin:0;padding:24px}}
h1{{font-size:1.4rem}} ul{{list-style:none;padding:0;display:grid;gap:10px;max-width:480px}}
a.card{{display:block;padding:14px 16px;background:#fff;border-radius:12px;text-decoration:none;
color:inherit;border:1px solid #0001;font-weight:700}} small{{color:#5a6b75;font-weight:500}}</style>
</head><body><h1>Alingsås HK · Åhus Beach Handboll</h1>
<p>Välj din åldersgrupp och lägg till på hemskärmen.</p><ul>{items}</ul>
<!-- Cloudflare Web Analytics (cookielöst, ingen samtyckesruta) -->
<script defer src="https://static.cloudflareinsights.com/beacon.min.js"
  data-cf-beacon='{{"token": "0fbaddb77cfe4155af4e4bdb370de308"}}'></script>
</body></html>"""


def render_hub(data):
    groups = data.get("groups", {})
    items = []
    for age_slug in sorted(groups, key=lambda s: int(s[1:])):
        g = groups[age_slug]
        n_teams, n_matches = len(g.get("teams", [])), len(g.get("matches", []))
        meta = f"<small>{n_teams} lag · {n_matches} matcher</small>"
        if age_slug == "u15":
            items.append(f'<li><a class="card" href="{U15_LIVE_URL}">{g["label"]} '
                         f'(P15+F15) {meta}</a></li>')
        else:
            items.append(f'<li><a class="card" href="{age_slug}/">{g["label"]} {meta}</a></li>')
    return _PAGE.format(items="\n".join(items))


def main():
    with open(DATA_JSON, encoding="utf-8") as f:
        data = json.load(f)
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(render_hub(data))
    print("Hubb (index.html) genererad")


if __name__ == "__main__":
    main()
