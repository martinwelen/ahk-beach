# build_apps.py
# -*- coding: utf-8 -*-
"""Bygger en installerbar PWA per åldersgrupp ur data.json/standings.json."""

import os
import json

import config
import template

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(ROOT, "data.json")
STANDINGS_JSON = os.path.join(ROOT, "standings.json")
SKIP_AGE_SLUGS = {"u15"}                  # U15 bor kvar i alingsas-ahus-beach-2026


def app_manifest(group):
    m = dict(template.MANIFEST_BASE)
    m["name"] = f"AHK {group['label']}"
    m["short_name"] = f"AHK {group['label']}"
    m["description"] = f"Matchschema för Alingsås HK {group['label']} på Åhus Beach Handboll"
    m["start_url"] = "."
    m["scope"] = "./"
    return m


def service_worker_js(age_slug):
    return template.SERVICE_WORKER_TPL.replace("__CACHE__", f"ahk-{age_slug}-v1")
