# api.py
# -*- coding: utf-8 -*-
"""cupmanager-API: rena entitetshjälpare + tunn nätverkshämtning."""

import re
import json
import time
import urllib.parse
import urllib.request

import config

_API = ("https://ahusbeachhandboll.cupmanager.net/rest/results_api/call"
        "?call={call}&lang=sv&tournamentId=" + config.TOURNAMENT_ID)


def ref_id(node):
    if isinstance(node, dict):
        m = re.search(r"id:(\d+)", node.get("href", ""))
        if m:
            return int(m.group(1))
    return None


def name_of(entity):
    n = entity.get("name") if isinstance(entity, dict) else None
    if isinstance(n, dict):
        return n.get("sv") or n.get("en") or ""
    return n or ""


def store_get(store, ref):
    return store.get(ref.get("href") if isinstance(ref, dict) else ref, {})


PAGE = 300


def match_query(limit, offset):
    return (
        "MatchWindow({{limit:{l},offset:{o},tournamentId:{t}}})"
        "{{matches:[{{... on Match:{{start:{{}},arena:{{}},"
        "away:{{team:{{}}}},division:{{category:{{}},name:{{}}}},"
        "home:{{team:{{}}}},result:{{}}}}}}]}}"
    ).format(l=limit, o=offset, t=config.TOURNAMENT_ID)


def call(query, retries=4):
    url = _API.format(call=urllib.parse.quote(query))
    req = urllib.request.Request(url, headers={
        "accept": "application/json", "user-agent": "ahk-beach-bot/1.0"})
    last = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:           # nät/transient → backoff och försök igen
            last = e
            time.sleep(2 + 2 * i)
    raise last


def fetch_store():
    """Sidar igenom alla matchfönster → entitets-store {href: entity}."""
    store, offset = {}, 0
    while True:
        resp = call(match_query(PAGE, offset)).get("responses", {})
        page = 0
        for k, v in resp.items():
            if isinstance(v, dict) and isinstance(v.get("entity"), dict):
                store[k] = v["entity"]
                if v["entity"].get("__typename") == "Match":
                    page += 1
        if page < PAGE:
            break
        offset += PAGE
    return store
