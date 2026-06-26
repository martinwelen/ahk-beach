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
